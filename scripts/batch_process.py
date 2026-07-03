#!/usr/bin/env python3
"""
批量面试题处理器
=================
从 JSON 文件读取题目列表，批量调用 Interview Coach 深度解答。

Usage:
  python batch_process.py questions.json
  python batch_process.py questions.json --output-dir my_answers/ --model claude-opus-4-8

questions.json 格式:
  {
    "title": "Java 后端面试题集",
    "questions": [
      "什么是 JVM？它的内存模型是怎样的？",
      "HashMap 的底层实现原理？为什么线程不安全？",
      ...
    ]
  }

  或简单的数组格式:
  [
    "第一道题",
    "第二道题"
  ]
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def validate_file(filepath: str) -> Path:
    p = Path(filepath)
    if not p.exists():
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)
    if p.suffix.lower() != '.json':
        print(f"⚠️  文件不是 .json 格式: {filepath}")
    return p


def load_questions(filepath: Path) -> tuple[str, list[str]]:
    """加载 JSON，返回 (标题, 题目列表)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        return "批量面试题", data
    if isinstance(data, dict):
        title = data.get("title", "批量面试题")
        questions = data.get("questions", [])
        if not questions:
            # 尝试其他可能的字段名
            for key in ["topics", "items", "problems"]:
                if key in data:
                    questions = data[key]
                    break
        return title, questions

    raise ValueError("JSON 格式错误：需要数组或包含 questions 字段的对象")


def run_agent(questions: list[str], output_dir: str, model: str,
              skip_review: bool = False) -> Path:
    """调用 interview_agent.py 处理所有题目"""
    # 写入临时 JSON
    tmp = Path("/tmp") / f"batch_questions_{datetime.now().strftime('%H%M%S')}.json"
    tmp.write_text(json.dumps({"questions": questions}, ensure_ascii=False, indent=2),
                   encoding='utf-8')

    agent_script = Path(__file__).parent / "interview_agent.py"
    cmd = [
        sys.executable, str(agent_script),
        "-f", str(tmp),
        "-o", output_dir,
        "-m", model,
    ]
    if skip_review:
        cmd.append("--skip-review")

    print(f"🚀 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    tmp.unlink(missing_ok=True)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="批量面试题处理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="面试题 JSON 文件路径")
    parser.add_argument("-o", "--output-dir", default="outputs",
                        help="输出目录 (默认: outputs)")
    parser.add_argument("-m", "--model", default="claude-sonnet-5",
                        help="模型名称")
    parser.add_argument("--skip-review", action="store_true",
                        help="跳过审查（更快）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示题目不执行")

    args = parser.parse_args()

    # 加载
    filepath = validate_file(args.file)
    title, questions = load_questions(filepath)

    print(f"\n{'='*60}")
    print(f"📚 {title}")
    print(f"{'='*60}")
    print(f"📋 共 {len(questions)} 道题")
    print(f"🧠 模型: {args.model}")
    print(f"📁 输出目录: {args.output_dir}")

    for i, q in enumerate(questions, 1):
        preview = q[:80].replace('\n', ' ')
        print(f"  {i}. {preview}{'...' if len(q) > 80 else ''}")

    if args.dry_run:
        print("\n📋 --dry-run 模式，不执行答题")
        return

    print(f"\n⏳ 开始批量处理...")
    run_agent(questions, args.output_dir, args.model, args.skip_review)


if __name__ == "__main__":
    main()
