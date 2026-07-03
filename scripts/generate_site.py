#!/usr/bin/env python3
"""
站点数据生成器 — 为 GitHub Pages 生成所有静态资源
====================================================
核心功能：
  1. 将 questions/database/ 中每道题的 .md 转为精美 HTML → docs/q/
  2. 生成 docs/data.json（供前端动态加载）
  3. 同步 index.json 到 docs/

这解决了 GitHub Pages 上查看题目文件 404 的问题：
题目源文件在 questions/database/ (Pages 不可访问)
→ 生成 HTML 到 docs/q/ (Pages 可访问)

Usage:
  python scripts/generate_site.py
  python scripts/generate_site.py --force  # 强制重新生成所有页面
"""

import sys
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import markdown
    from markdown.extensions import tables, fenced_code, codehilite, toc, nl2br
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("⚠️  markdown 库未安装，将使用纯文本渲染")
    print("   pip install markdown pygments")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = PROJECT_ROOT / "questions"
DATABASE_DIR = QUESTIONS_DIR / "database"
INDEX_FILE = QUESTIONS_DIR / "index.json"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_HTML_DIR = DOCS_DIR / "q"
OUTPUT_DATA_FILE = DOCS_DIR / "data.json"

# ============================================================
# CSS — 统一设计语言
# ============================================================

PAGE_CSS = """
:root {
    --bg: #0d1117; --bg-secondary: #161b22; --border: #30363d;
    --text: #c9d1d9; --text-secondary: #8b949e; --accent: #58a6ff;
    --accent-green: #3fb950; --accent-orange: #d2991d;
    --accent-purple: #a371f7; --accent-red: #f85149;
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
             'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', Menlo, monospace;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: var(--font); background: var(--bg); color: var(--text);
    line-height: 1.8; font-size: 15px;
}

/* ===== Layout ===== */
.q-header {
    background: var(--bg-secondary); border-bottom: 1px solid var(--border);
    padding: 20px 0; position: sticky; top: 0; z-index: 10;
    backdrop-filter: blur(12px);
}
.q-header-inner {
    max-width: 820px; margin: 0 auto; padding: 0 24px;
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.q-header a { color: var(--accent); text-decoration: none; font-size: 0.85rem; }
.q-header .sep { color: var(--text-secondary); }
.q-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-left: auto; }
.q-meta-item {
    padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
}
.q-meta-cat { background: rgba(88,166,255,0.12); color: var(--accent); }
.q-meta-diff-easy { color: var(--accent-green); }
.q-meta-diff-medium { color: var(--accent-orange); }
.q-meta-diff-hard { color: var(--accent-red); }

.q-container { max-width: 820px; margin: 0 auto; padding: 32px 24px; }

/* ===== Typography ===== */
.q-container h1 {
    font-size: 1.7rem; color: #f0f6fc; margin: 8px 0 24px;
    padding-bottom: 16px; border-bottom: 2px solid var(--border); line-height: 1.4;
}
.q-container h2 {
    font-size: 1.3rem; margin: 36px 0 16px; color: #f0f6fc;
    padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
.q-container h3 {
    font-size: 1.1rem; margin: 28px 0 12px; color: var(--accent);
}
.q-container h4 { font-size: 1rem; margin: 20px 0 8px; color: #e6edf3; }
.q-container p { margin: 12px 0; }
.q-container strong { color: #f0f6fc; font-weight: 600; }
.q-container em { color: var(--text-secondary); }
.q-container a { color: var(--accent); text-decoration: none; }
.q-container a:hover { text-decoration: underline; }

/* ===== Blockquote ===== */
.q-container blockquote {
    border-left: 3px solid var(--accent); margin: 16px 0;
    padding: 12px 20px; background: var(--bg-secondary);
    border-radius: 0 8px 8px 0; color: var(--text-secondary);
}
.q-container blockquote p { margin: 4px 0; }

/* ===== Code ===== */
.q-container code {
    background: var(--bg-secondary); padding: 3px 8px; border-radius: 4px;
    font-family: var(--font-mono); font-size: 0.88em; color: var(--accent-orange);
}
.q-container pre {
    background: var(--bg-secondary); border: 1px solid var(--border);
    border-radius: 8px; padding: 18px 20px; overflow-x: auto;
    margin: 16px 0; line-height: 1.6;
}
.q-container pre code {
    background: none; padding: 0; color: var(--text); font-size: 0.85rem;
}

/* ===== Tables ===== */
.q-container table {
    width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9rem;
}
.q-container th {
    background: var(--bg-secondary); padding: 10px 14px; text-align: left;
    border: 1px solid var(--border); font-weight: 600; color: #f0f6fc;
}
.q-container td {
    padding: 8px 14px; border: 1px solid var(--border);
}

/* ===== Lists ===== */
.q-container ul, .q-container ol { padding-left: 24px; margin: 10px 0; }
.q-container li { margin: 6px 0; }
.q-container li::marker { color: var(--accent); }
.q-container hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }

/* ===== Tags ===== */
.tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 20px 0; }
.tag-item {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    background: rgba(163,113,247,0.1); color: var(--accent-purple);
    font-size: 0.78rem; font-weight: 500;
}

/* ===== Review Button ===== */
.review-actions { margin: 32px 0; text-align: center; }
.btn-review {
    display: inline-block; padding: 12px 32px; border-radius: 8px;
    background: var(--accent-green); color: #fff; border: none;
    font-size: 0.95rem; font-weight: 600; cursor: pointer;
    transition: all 0.2s;
}
.btn-review:hover { filter: brightness(1.15); transform: translateY(-1px); }
.btn-review.reviewed { background: var(--bg-secondary); border: 1px solid var(--accent-green); color: var(--accent-green); }

/* ===== Footer ===== */
.q-footer {
    text-align: center; padding: 28px; color: var(--text-secondary);
    font-size: 0.82rem; border-top: 1px solid var(--border); margin-top: 40px;
}
.q-footer a { color: var(--accent); text-decoration: none; }

/* ===== Mobile ===== */
@media (max-width: 640px) {
    .q-container { padding: 20px 16px; }
    .q-container h1 { font-size: 1.3rem; }
    .q-header-inner { flex-direction: column; align-items: flex-start; }
    .q-meta { margin-left: 0; }
}
"""

# ============================================================
# HTML 模板
# ============================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Interview Coach</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>{css}</style>
</head>
<body>

<header class="q-header">
    <div class="q-header-inner">
        <a href="index.html">🏠 首页</a>
        <span class="sep">/</span>
        <a href="questions.html">📚 题库</a>
        <span class="sep">/</span>
        <span style="font-size:0.85rem;">{qid}</span>
        <div class="q-meta">
            <span class="q-meta-item q-meta-cat">{cat_icon} {cat_name}</span>
            <span class="q-meta-item q-meta-diff-{difficulty}">● {diff_name}</span>
            <span class="q-meta-item" style="color:var(--text-secondary);">{date}</span>
        </div>
    </div>
</header>

<div class="q-container">
    <h1>{question}</h1>
    <div class="tag-row">{tags_html}</div>
    {body}
    <div class="review-actions">
        <button class="btn-review" id="review-btn" onclick="toggleReview('{qid}')">
            ✅ Mark as Reviewed Today
        </button>
        <p id="review-status" style="margin-top:8px;font-size:0.82rem;color:var(--text-secondary);"></p>
    </div>
</div>

<footer class="q-footer">
    <p>
        <a href="questions.html">📚 题库浏览器</a> ·
        <a href="daily.html">📅 每日复习</a> ·
        <a href="https://github.com/Dddddduo/dduo-interview-coach">GitHub</a>
    </p>
    <p style="margin-top:6px;">Interview Coach — Harness Engineering Architecture</p>
</footer>

<script>
hljs.highlightAll();

// 复习打卡
function toggleReview(qid) {{
    const key = 'reviewed_' + new Date().toISOString().slice(0,10);
    let reviewed = JSON.parse(localStorage.getItem(key) || '[]');
    const btn = document.getElementById('review-btn');
    const status = document.getElementById('review-status');

    if (reviewed.includes(qid)) {{
        reviewed = reviewed.filter(id => id !== qid);
        btn.textContent = '✅ Mark as Reviewed Today';
        btn.classList.remove('reviewed');
        status.textContent = '';
    }} else {{
        reviewed.push(qid);
        btn.textContent = '✓ Reviewed Today!';
        btn.classList.add('reviewed');
        status.textContent = '🎉 Great job! Keep up the momentum!';
    }}
    localStorage.setItem(key, JSON.stringify(reviewed));
}}

// 初始化打卡状态
(function() {{
    const key = 'reviewed_' + new Date().toISOString().slice(0,10);
    const reviewed = JSON.parse(localStorage.getItem(key) || '[]');
    if (reviewed.includes('{qid}')) {{
        const btn = document.getElementById('review-btn');
        btn.textContent = '✓ Reviewed Today!';
        btn.classList.add('reviewed');
    }}
}})();
</script>
</body>
</html>"""


def md_to_html(md_text: str) -> str:
    """将 Markdown 转为 HTML"""
    if not HAS_MARKDOWN:
        # 纯文本回退
        escaped = md_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f"<pre>{escaped}</pre>"

    html = markdown.markdown(
        md_text,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br',
        ],
        extension_configs={
            'markdown.extensions.codehilite': {
                'css_class': 'highlight',
                'guess_lang': True,
            },
        }
    )
    return html


def render_question_page(question_data: dict, md_content: str) -> str:
    """渲染单道题的完整 HTML 页面"""
    cat = question_data.get("category", "unknown")
    cat_info = _load_categories().get(cat, {"name": cat, "icon": "📌"})
    diff = question_data.get("difficulty", "medium")
    diff_info = {"easy": "基础", "medium": "中级", "hard": "进阶"}.get(diff, diff)

    tags = question_data.get("tags", [])
    tags_html = "\n".join(f'<span class="tag-item">{t}</span>' for t in tags)

    # 把 markdown 转 HTML
    body = md_to_html(md_content)

    return HTML_TEMPLATE.format(
        title=question_data.get("question", "")[:60],
        css=PAGE_CSS,
        qid=question_data.get("id", ""),
        question=question_data.get("question", ""),
        cat_icon=cat_info.get("icon", "📌"),
        cat_name=cat_info.get("name", cat),
        difficulty=diff,
        diff_name=diff_info,
        date=question_data.get("created", "")[:10],
        tags_html=tags_html,
        body=body,
    )


def _load_categories() -> dict:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("categories", {})
    return {}


def _load_index() -> dict:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"meta": {}, "categories": {}, "questions": []}


def generate_all(force: bool = False):
    """主生成函数"""
    index = _load_index()
    questions = index.get("questions", [])
    categories = index.get("categories", {})

    if not questions:
        print("⚠️  题库为空，跳过生成")
        return

    # 创建输出目录
    OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped = 0
    errors = 0

    # 逐题生成 HTML
    for q in questions:
        qid = q.get("id", "")
        filepath_rel = q.get("file", "")
        md_path = PROJECT_ROOT / filepath_rel

        if not md_path.exists():
            print(f"  ⚠️  [{qid}] 源文件不存在: {filepath_rel}")
            errors += 1
            continue

        output_path = OUTPUT_HTML_DIR / f"{qid}.html"

        # 增量生成：如果 HTML 比 MD 新，跳过
        if not force and output_path.exists():
            if output_path.stat().st_mtime >= md_path.stat().st_mtime:
                skipped += 1
                continue

        try:
            md_content = md_path.read_text(encoding='utf-8')

            # 去掉 YAML frontmatter（如果存在）
            if md_content.startswith('---'):
                end = md_content.find('---', 3)
                if end > 0:
                    md_content = md_content[end + 3:].strip()

            html = render_question_page(q, md_content)
            output_path.write_text(html, encoding='utf-8')
            generated += 1
            print(f"  ✅ [{qid}] → docs/q/{qid}.html")
        except Exception as e:
            print(f"  ❌ [{qid}] 生成失败: {e}")
            errors += 1

    # 生成 data.json（供前端用）
    data = _build_data_json(questions, categories, index.get("meta", {}))
    OUTPUT_DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"  📊 data.json 已生成 ({len(questions)} 题)")

    # 同步 index.json 到 docs/
    shutil.copy2(INDEX_FILE, DOCS_DIR / "index.json")
    print(f"  📋 index.json 已同步到 docs/")

    # 汇总
    print(f"\n{'='*50}")
    print(f"📊 站点生成完成:")
    print(f"   ✅ 生成: {generated} 个页面")
    print(f"   ⏭️  跳过: {skipped} 个 (未变化)")
    print(f"   ❌ 错误: {errors} 个")
    print(f"   📂 输出: docs/q/")
    print(f"🌐 访问: https://ddddduo.github.io/dduo-interview-coach/questions.html")


def _build_data_json(questions: list, categories: dict, meta: dict) -> dict:
    """构建前端数据文件"""
    # 按日期分组
    by_date = {}
    for q in questions:
        date = q.get("created", "")[:10]
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(q)

    # 标签统计
    tag_counts = {}
    for q in questions:
        for t in q.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:20]

    # 分类统计
    cat_stats = {}
    for q in questions:
        cat = q.get("category", "unknown")
        if cat not in cat_stats:
            cat_stats[cat] = {"count": 0}
        cat_stats[cat]["count"] += 1

    # 日期列表（倒序）
    dates = sorted(by_date.keys(), reverse=True)

    return {
        "meta": meta,
        "total": len(questions),
        "categories": categories,
        "cat_stats": cat_stats,
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        "dates": dates,
        "by_date": by_date,
        "questions": questions,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="站点数据生成器")
    parser.add_argument("--force", action="store_true", help="强制重新生成所有页面")
    args = parser.parse_args()

    print("🔨 Interview Coach — 站点数据生成器")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not HAS_MARKDOWN:
        print("⚠️  markdown 库未安装，HTML 渲染将不完整")
        print("   运行: pip install markdown pygments")
        print()

    generate_all(force=args.force)


if __name__ == "__main__":
    main()
