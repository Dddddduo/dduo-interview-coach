#!/usr/bin/env python3
"""
模板引擎
=========
为面试答案生成不同格式的文档模板。

支持格式:
  - default  — 完整面试解答（记忆法+深度解答+回答思路）
  - concise  — 精简版（核心答案+记忆口诀）
  - flashcard — Anki 闪卡格式
  - blog      — 博客文章格式
  - notion    — Notion 导入格式
  - slides    — PPT 大纲格式

Usage:
  python scripts/template_engine.py generate q0001 --format default
  python scripts/template_engine.py generate q0001 --format flashcard
  python scripts/template_engine.py list-formats
"""

import sys, json, argparse, re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
DATABASE_DIR = PROJECT_ROOT / "questions" / "database"


def load_question(qid: str) -> dict:
    """加载指定题目"""
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        index = json.load(f)
    for q in index.get("questions", []):
        if q["id"] == qid:
            return q
    print(f"❌ 未找到题目: {qid}")
    sys.exit(1)


def load_answer(q: dict) -> str:
    """加载完整答案"""
    filepath = PROJECT_ROOT / q.get("file", "")
    if filepath.exists():
        text = filepath.read_text(encoding='utf-8')
        if text.startswith('---'):
            end = text.find('---', 3)
            if end > 0:
                text = text[end + 3:].strip()
        return text
    return q.get("answer", "")


# ============================================================
# 模板格式
# ============================================================

def template_default(q: dict, answer: str) -> str:
    """完整面试解答模板"""
    cats = _load_cats()
    cat = cats.get(q.get("category", ""), {})
    tags = " ".join(f"`{t}`" for t in q.get("tags", []))

    return f"""---
id: {q['id']}
date: {q.get('created', '')}
category: {cat.get('name', q.get('category', ''))}
tags: [{', '.join(q.get('tags', []))}]
difficulty: {q.get('difficulty', 'medium')}
---

# {q['question']}

## 🧠 联想记忆法

> **记忆口诀**: [从答案中提取]
> **记忆原理**: [从答案中提取]
> **关联知识**: [从答案中提取]

---

## 📖 深度解答

### 1. 核心概念（是什么）

### 2. 底层原理（为什么）

### 3. 实践应用（怎么用）

### 4. 深入思考（注意事项）

---

## 🗺️ 回答思路

- **答题框架**:
- **得分点**:
- **常见误区**:
- **时间分配**:

---

{answer}

---

> 📂 分类: {cat.get('name', '')} | 🏷️ 标签: {tags}
> 📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def template_concise(q: dict, answer: str) -> str:
    """精简版模板"""
    # 提取记忆口诀
    memory = ""
    memory_match = re.search(r'(?:记忆口诀|联想)[：:]\s*(.+?)(?:\n|$)', answer)
    if memory_match:
        memory = memory_match.group(1).strip()

    # 提取核心定义（前200字符）
    core = answer[:300].strip()

    return f"""# {q['question']}

## 🧠 记住这个
{memory or '(从完整答案中查看)'}

## 📝 核心要点
{core}

---
🔗 [查看完整答案](q/{q['id']}.html)
"""


def template_flashcard(q: dict, answer: str) -> str:
    """Anki 闪卡格式"""
    # 提取记忆法
    memory_section = ""
    memory_match = re.search(r'(?:###?\s*)?🧠.*?联想记忆法(.*?)(?=###?\s*[📖🗺️]|##\s)', answer, re.DOTALL)
    if memory_match:
        memory_section = memory_match.group(1).strip()[:500]

    # 提取核心答案
    core = re.sub(r'#{1,4}\s+', '', answer[:400]).strip()

    return f"""FRONT: {q['question']}

BACK:
🧠 {memory_section or core[:200]}

📖 {core}

🏷️ {' '.join(q.get('tags', []))}
📂 {q.get('category', '')} | {q.get('difficulty', '')}
"""


def template_blog(q: dict, answer: str) -> str:
    """博客文章格式"""
    cats = _load_cats()
    cat = cats.get(q.get("category", ""), {})
    tags = q.get("tags", [])
    now = datetime.now().strftime("%Y-%m-%d")

    return f"""---
title: "{q['question']}"
date: {now}
category: {cat.get('name', q.get('category', ''))}
tags: {json.dumps(tags, ensure_ascii=False)}
description: "深度解析 {q['question'][:50]}..."
---

# {q['question']}

> 本文深度解析面试高频题「{q['question'][:50]}」，从核心概念到底层原理，从实践应用到面试答题技巧，帮你彻底掌握。

{answer}

---

*本文由 [Interview Coach](https://github.com/Dddddduo/dduo-interview-coach) 生成 · Harness Engineering 架构*

**标签**: {' '.join(f'#{t}' for t in tags[:8])}
"""


def template_notion(q: dict, answer: str) -> str:
    """Notion 导入格式 (CSV-like Markdown)"""
    cats = _load_cats()
    cat = cats.get(q.get("category", ""), {})

    # 提取各部分
    sections = re.split(r'(?:###?\s*)?[🧠📖🗺️]', answer)

    return f"""---
Name: {q['question']}
Category: {cat.get('name', q.get('category', ''))}
Difficulty: {q.get('difficulty', 'medium')}
Tags: {', '.join(q.get('tags', []))}
ID: {q['id']}
---

# {q['question']}

{answer}

---
Created: {q.get('created', '')}
"""


def template_slides(q: dict, answer: str) -> str:
    """PPT 大纲格式"""
    lines = [
        f"# {q['question'][:60]}",
        "",
        "## Slide 1: 题目",
        f"- {q['question']}",
        f"- 分类: {q.get('category', '')}",
        f"- 难度: {q.get('difficulty', '')}",
        "",
        "## Slide 2: 核心概念",
        "- 一句话定义",
        "- 解决什么问题",
        "",
        "## Slide 3: 底层原理",
        "- 核心机制",
        "- 关键设计决策",
        "",
        "## Slide 4: 实践应用",
        "- 代码示例",
        "- 最佳实践",
        "",
        "## Slide 5: 面试要点",
        "- 联想记忆法",
        "- 得分点",
        "- 常见误区",
        "",
        "## Slide 6: 总结",
        "- 3 个关键 Takeaways",
    ]
    return "\n".join(lines)


TEMPLATES = {
    "default": template_default,
    "concise": template_concise,
    "flashcard": template_flashcard,
    "blog": template_blog,
    "notion": template_notion,
    "slides": template_slides,
}


def _load_cats():
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("categories", {})
    return {}


def main():
    parser = argparse.ArgumentParser(description="模板引擎")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="生成模板")
    p_gen.add_argument("qid", help="题号 (如 q0001)")
    p_gen.add_argument("--format", "-f", choices=list(TEMPLATES.keys()), default="default")
    p_gen.add_argument("--output", "-o", help="输出文件")

    sub.add_parser("list-formats", help="列出所有格式")

    args = parser.parse_args()

    if args.cmd == "list-formats":
        print("\n📋 可用模板格式:\n")
        for name, func in TEMPLATES.items():
            doc = (func.__doc__ or "").strip().split('\n')[0]
            print(f"  {name:15s} — {doc}")
        return

    if args.cmd == "generate":
        q = load_question(args.qid)
        answer = load_answer(q)
        template_func = TEMPLATES[args.format]
        output = template_func(q, answer)

        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"✅ 已保存: {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()
