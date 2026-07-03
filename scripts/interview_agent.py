#!/usr/bin/env python3
"""
Interview Coach — 独立运行的 AI 面试解答 Agent
===============================================
基于 Anthropic SDK 的多 Agent 协作系统，无需 Claude Code 即可运行。

Harness Engineering 体现：
  - 3 个虚拟 Agent（Answerer / Reviewer / Assembler）各司其职
  - 质量门控：审查不合格自动返工，最多 2 次
  - 确定性流水线：解析 → 答题 → 审查 → 组装 → 输出

Usage:
  python interview_agent.py "你的面试题"
  python interview_agent.py --file questions.json
  python interview_agent.py --interactive

环境变量：
  ANTHROPIC_API_KEY — Anthropic API 密钥（必需）
"""

import os
import sys
import json
import argparse
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ 请先安装 anthropic SDK: pip install anthropic")
    sys.exit(1)

# 题库管理器（同项目内 import）
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from question_manager import QuestionManager, classify_question, auto_tag, estimate_difficulty
    HAS_QM = True
except ImportError:
    HAS_QM = False

# ============================================================
# Agent System Prompts — 每个 Agent 的角色定义
# ============================================================

ANSWERER_SYSTEM = """\
你是资深面试教练和技术答题专家。你的任务是对面试题给出深度解答。

## 输出结构（严格按此顺序）

### 🧠 联想记忆法（最先给出！）
- 记忆口诀/联想: 一句好记的口诀或场景联想
- 记忆原理: 为什么这个记忆法有效（认知钩子）
- 关联知识: 连接到读者已有的知识

### 📖 深度解答
#### 1. 核心概念（是什么）
一句话定义 + 解决什么问题 + 面试中为什么重要

#### 2. 底层原理（为什么）
详细拆解底层机制、运行流程、设计哲学、为什么选择这个方案而不是其他方案

#### 3. 实践应用（怎么用）
具体用法、代码示例、最佳实践、常见模式

#### 4. 深入思考（注意事项）
常见误区、边界情况、面试官可能的追问及其答案

### 🗺️ 回答思路
- 答题逻辑框架: 面试时怎么组织语言
- 重点得分点: 面试官在听什么
- 常见误区: 不要说哪些话
- 时间分配建议: 每部分说多久
- 过渡话术: 段落间的衔接语句

## 硬性要求
- 联想记忆法永远在最前面，每道题无一例外
- 讲透原理，不是表面结论。回答如果能在 Google 第一页搜到，就是不够深
- 中英术语对照（首次出现的术语加英文原文）
- 语言专业正式，贴合面试场景。不说废话、不写散文
- 技术题必须有代码示例。行为题按 STAR 框架展开
"""

REVIEWER_SYSTEM = """\
你是严格的质量审查员。你的唯一工作是——检查面试题答案是否达标。

## 检查清单（逐项验证）

### 结构完整性
1. 联想记忆法是否在最前面？是否包含口诀、原理、关联知识？
2. 深度解答是否包含 4 个子章节？（核心概念/底层原理/实践应用/深入思考）
3. 回答思路是否有答题框架、得分点、误区、时间分配、过渡话术？

### 内容深度
4. 是否深入讲解原理而不只是表面结论？
5. 技术题是否有代码示例？行为题是否有具体场景？
6. 是否包含最佳实践和常见误区？

### 面试可用性
7. 语言是否专业正式？
8. 结构是否清晰可扫描？
9. 术语是否中英对照？

## 输出格式
以 JSON 格式输出审查结果：
```json
{
  "result": "PASS" | "FAIL",
  "failed_items": ["项目1", "项目2"],
  "specific_issues": "具体的问题描述和改进建议"
}
```
"""

ASSEMBLER_SYSTEM = """\
你是文档排版专家。将多道题的答案组装为一份完整的 Markdown 文档。

## 文档格式
```markdown
# 📚 面经深度解答

> **生成时间**: {timestamp}
> **题目数量**: N 道
> **生成工具**: Interview Coach Agent

---

## 📑 目录
[自动生成]

---

## 第N题: [题目文本]
[完整答案内容]

---
```

## 规则
- 生成可点击的目录
- 代码块加语言标签
- 表格对齐
- 保留全部原始内容，不删减
"""

# ============================================================
# Agent 类 — 封装 API 调用
# ============================================================

class InterviewAgent:
    """单个 Agent 的 API 封装"""

    def __init__(self, client: Anthropic, model: str = "claude-sonnet-5"):
        self.client = client
        self.model = model

    def call(self, system_prompt: str, user_message: str,
             max_tokens: int = 8000) -> str:
        """调用 Claude API"""
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return resp.content[0].text
        except Exception as e:
            return f"[ERROR] API 调用失败: {e}"


class InterviewCoach:
    """
    主编排器 — Harness Engineering 核心
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Answerer │ →  │ Reviewer │ →  │Assembler │ → 输出
    └──────────┘    └──────────┘    └──────────┘
                     ↑ 不合格返工
    """

    MAX_RETRIES = 2

    def __init__(self, model: str = "claude-sonnet-5"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "请设置环境变量 ANTHROPIC_API_KEY\n"
                "  export ANTHROPIC_API_KEY='your-key-here'"
            )
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.answerer = InterviewAgent(self.client, model)
        self.reviewer = InterviewAgent(self.client, model)
        self.assembler = InterviewAgent(self.client, model)

    def process_single(self, question: str, index: int = 1) -> dict:
        """处理单道题：答题 → 审查 → 必要时重答"""
        print(f"\n{'='*60}")
        print(f"📝 第 {index} 题: {question[:60]}{'...' if len(question) > 60 else ''}")

        # 阶段 1：答题
        print("  🤖 答题中...")
        answer = None
        review_result = None

        for attempt in range(1 + self.MAX_RETRIES):
            if attempt > 0:
                print(f"  🔄 第 {attempt} 次重答...")
                # 重答时附上审查反馈
                prompt = f"面试题：{question}\n\n[上次审查不通过，请修正以下问题]\n{review_result}"
            else:
                prompt = f"请解答以下面试题：\n\n{question}"

            answer = self.answerer.call(ANSWERER_SYSTEM, prompt)

            if answer.startswith("[ERROR]"):
                print(f"  ❌ {answer}")
                continue

            # 阶段 2：审查
            print("  ✅ 审查中...")
            review_raw = self.reviewer.call(
                REVIEWER_SYSTEM,
                f"审查以下面试题答案：\n\n## 题目\n{question}\n\n## 答案\n{answer}"
            )

            parsed = self._parse_review(review_raw)
            review_result = parsed.get("specific_issues", "")

            if parsed.get("result") == "PASS":
                print("  ✅ 审查通过")
                return {
                    "index": index,
                    "question": question,
                    "answer": answer,
                    "review": "PASS",
                    "retries": attempt,
                }
            else:
                failed = parsed.get("failed_items", [])
                print(f"  ❌ 审查不通过 ({len(failed)} 项): {', '.join(failed[:3])}")

        # 超过最大重试次数
        print("  ⚠️ 超过最大重试次数，使用最后一次答案")
        return {
            "index": index,
            "question": question,
            "answer": answer or "[ERROR] 答题失败",
            "review": "FAILED_AFTER_RETRIES",
            "retries": self.MAX_RETRIES,
        }

    def assemble(self, results: list[dict]) -> str:
        """阶段 3：组装文档"""
        print("\n📄 组装文档...")
        parts = []
        for r in results:
            parts.append(f"## 第{r['index']}题：{r['question']}")
            parts.append(r['answer'])
            parts.append("\n---\n")

        all_answers = "\n\n".join(parts)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        doc = self.assembler.call(
            ASSEMBLER_SYSTEM.replace("{timestamp}", timestamp),
            f"请组装以下 {len(results)} 道题的答案：\n\n{all_answers}"
        )
        return doc

    def archive_results(self, results: list[dict], source: str = "") -> list[dict]:
        """阶段 4：将答题结果归档到题库"""
        if not HAS_QM:
            print("\n⚠️  question_manager 不可用，跳过题库归档")
            return []

        print("\n📚 归档到题库...")
        mgr = QuestionManager()
        entries = []

        for r in results:
            question = r["question"]
            answer = r["answer"]
            cat = classify_question(question)
            tags = auto_tag(question)
            diff = estimate_difficulty(question)

            try:
                entry = mgr.add(
                    question=question,
                    answer=answer,
                    category=cat,
                    tags=tags,
                    difficulty=diff,
                    source=source or "interview_agent",
                )
                entries.append(entry)
            except Exception as e:
                print(f"  ❌ 归档失败 [{r['index']}]: {e}")

        return entries

    def _parse_review(self, text: str) -> dict:
        """尝试从审查输出中提取 JSON"""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        # 回退：从文本中推断
        text_upper = text.upper()
        if "PASS" in text_upper and "FAIL" not in text_upper.replace("PASS", ""):
            return {"result": "PASS", "failed_items": [], "specific_issues": ""}
        return {"result": "FAIL", "failed_items": ["parse_error"],
                "specific_issues": "审查结果解析失败，请人工检查"}


# ============================================================
# CLI
# ============================================================

def parse_questions_from_file(filepath: str) -> list[str]:
    """从 JSON 文件读取题目列表"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "questions" in data:
        return data["questions"]
    raise ValueError("JSON 格式错误：需要题目数组或包含 'questions' 字段的对象")


def save_output(content: str, output_dir: str = "outputs") -> Path:
    """保存文档到 outputs/ 目录"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    fpath = out / f"面经解答-{ts}.md"
    fpath.write_text(content, encoding='utf-8')
    return fpath


def parse_questions_from_text(text: str) -> list[str]:
    """从文本中解析题目（按编号或空行分隔）"""
    import re
    # 尝试按 "第N题"、"QN"、"N." 分隔
    parts = re.split(r'\n(?=第\d+题[：:])|(?<=^)第\d+题[：:]', text, flags=re.MULTILINE)
    if len(parts) <= 1:
        # 按双换行分隔
        parts = re.split(r'\n\s*\n', text)

    questions = [p.strip() for p in parts if p.strip()]
    # 去重（有些分隔会产生空项）
    return questions


def main():
    parser = argparse.ArgumentParser(
        description="Interview Coach — AI 面试解答 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        示例:
          %(prog)s "什么是CAP理论？"
          %(prog)s -f questions.json
          %(prog)s -f questions.json --model claude-opus-4-8
          %(prog)s -i
          echo "进程和线程的区别？" | %(prog)s
        """),
    )
    parser.add_argument(
        "question", nargs="?", default=None,
        help="单个面试题文本"
    )
    parser.add_argument(
        "-f", "--file", dest="filepath",
        help="包含面试题列表的 JSON 文件"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true",
        help="交互模式：逐题输入"
    )
    parser.add_argument(
        "-o", "--output-dir", default="outputs",
        help="输出目录 (默认: outputs)"
    )
    parser.add_argument(
        "-m", "--model", default="claude-sonnet-5",
        help="模型名称 (默认: claude-sonnet-5)"
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="只打印不保存"
    )
    parser.add_argument(
        "--skip-review", action="store_true",
        help="跳过质量审查（更快但质量无保证）"
    )
    parser.add_argument(
        "--no-archive", action="store_true",
        help="不归档到题库（仅生成文档）"
    )
    parser.add_argument(
        "--source", default="interview_agent",
        help="题目来源标记 (默认: interview_agent)"
    )

    args = parser.parse_args()

    # 读取题目
    questions = []

    if args.filepath:
        questions = parse_questions_from_file(args.filepath)
    elif args.interactive:
        print("📝 交互模式 — 逐行输入面试题，输入空行结束：")
        q = []
        while True:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                break
            if line.strip() == "" and q:
                questions.append("\n".join(q))
                q = []
                break
            elif line.strip() == "":
                break
            else:
                q.append(line)
        if q:
            questions.append("\n".join(q))
    elif args.question:
        questions = [args.question]
    else:
        # 从 stdin 读取
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
            if text:
                questions = parse_questions_from_text(text)
        if not questions:
            parser.print_help()
            sys.exit(1)

    if not questions:
        print("❌ 没有检测到面试题")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"🎯 Interview Coach — AI 面试解答 Agent")
    print(f"{'='*60}")
    print(f"📋 检测到 {len(questions)} 道题")
    print(f"🧠 模型: {args.model}")
    print(f"📁 输出目录: {args.output_dir}")
    print(f"✅ 质量审查: {'关闭' if args.skip_review else '开启'}")
    print(f"{'='*60}")

    try:
        coach = InterviewCoach(model=args.model)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    results = []
    for i, q in enumerate(questions, 1):
        result = coach.process_single(q, index=i)
        results.append(result)

    # 统计
    passed = sum(1 for r in results if r["review"] == "PASS")
    failed = len(results) - passed
    print(f"\n{'='*60}")
    print(f"📊 处理完成: {len(results)} 道题")
    print(f"   ✅ {passed} 道审查通过")
    if failed:
        print(f"   ⚠️ {failed} 道需人工审核")

    # 组装 & 输出
    doc = coach.assemble(results)

    # 归档到题库
    if not args.no_archive:
        archive_entries = coach.archive_results(results, source=args.source)
        if archive_entries:
            print(f"  📚 已归档 {len(archive_entries)} 道题到题库 (questions/database/)")

    if args.no_save:
        print("\n" + doc)
    else:
        fpath = save_output(doc, args.output_dir)
        print(f"\n📄 文档已保存: {fpath.absolute()}")
        # 打印前 500 字符预览
        print(f"\n--- 预览 ---\n{doc[:500]}...\n")


if __name__ == "__main__":
    main()
