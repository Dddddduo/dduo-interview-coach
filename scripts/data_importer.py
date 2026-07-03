#!/usr/bin/env python3
"""
数据导入器
===========
支持从多种来源导入面试题到题库。

支持格式:
  - Markdown 文件（含题目和答案）
  - JSON 题库文件
  - CSV 文件
  - 纯文本文件（每行一题）
  - LeetCode 导出的 JSON
  - 牛客网面经文本

功能:
  import    — 导入题目
  detect    — 自动检测文件格式
  merge     — 合并多个题库
  validate  — 验证导入数据格式
  batch     — 批量导入目录下所有文件

Usage:
  python scripts/data_importer.py import questions.md
  python scripts/data_importer.py detect my_questions.json
  python scripts/data_importer.py merge file1.json file2.json --output merged.json
  python scripts/data_importer.py batch ./my_questions/
"""

import sys, json, csv, re, argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def detect_format(filepath: str) -> str:
    """自动检测文件格式"""
    path = Path(filepath)
    if not path.exists():
        return "not_found"

    suffix = path.suffix.lower()

    if suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return "json_array"
        if isinstance(data, dict):
            if "questions" in data:
                return "interview_coach_json"
            if "stat_status_pairs" in data:
                return "leetcode_json"
            return "json_object"

    if suffix == '.csv':
        return "csv"

    if suffix in ['.md', '.markdown']:
        content = path.read_text(encoding='utf-8')
        if re.search(r'^#+\s*第?\d+[题\.、]', content, re.MULTILINE):
            return "markdown_questions"
        if '---' in content[:10]:
            return "markdown_frontmatter"
        return "markdown_generic"

    if suffix == '.txt':
        return "text_lines"

    return "unknown"


def import_markdown_questions(filepath: str) -> list[dict]:
    """从 Markdown 导入题目"""
    path = Path(filepath)
    content = path.read_text(encoding='utf-8')

    questions = []
    # 匹配 "第N题" 或 "QN" 或 "N." 开头的块
    blocks = re.split(r'\n(?=#{1,3}\s*(?:第?\d+[题\.、]|Q\d+[\.:]))', content)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 提取标题（题目）
        title_match = re.match(r'^#{1,3}\s*(.+?)$', block, re.MULTILINE)
        if not title_match:
            continue
        question = title_match.group(1).strip()

        # 去掉标题后的内容即为答案
        answer = block[title_match.end():].strip()

        # 尝试提取标签
        tags = []
        tag_match = re.findall(r'🏷️.*?标签[：:]\s*(.+?)$', answer, re.MULTILINE)
        if tag_match:
            tags = [t.strip() for t in tag_match[0].split(',')]

        # 尝试提取分类
        category = "unknown"
        cat_match = re.search(r'📂.*?分类[：:]\s*(.+?)$', answer, re.MULTILINE)
        if cat_match:
            category = cat_match.group(1).strip()

        questions.append({
            "question": question,
            "answer": answer,
            "tags": tags,
            "category": category,
            "source": path.name,
        })

    return questions


def import_json_array(filepath: str) -> list[dict]:
    """从 JSON 数组导入"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    questions = []
    for item in data:
        if isinstance(item, str):
            questions.append({"question": item, "answer": "", "tags": [], "category": "unknown"})
        elif isinstance(item, dict):
            questions.append({
                "question": item.get("question", item.get("title", item.get("name", ""))),
                "answer": item.get("answer", item.get("solution", item.get("content", ""))),
                "tags": item.get("tags", item.get("topics", [])),
                "category": item.get("category", item.get("type", "unknown")),
                "source": Path(filepath).name,
            })
    return questions


def import_csv(filepath: str) -> list[dict]:
    """从 CSV 导入"""
    questions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append({
                "question": row.get("question", row.get("题目", row.get("title", ""))),
                "answer": row.get("answer", row.get("答案", row.get("solution", ""))),
                "tags": [t.strip() for t in row.get("tags", row.get("标签", "")).split(",") if t.strip()],
                "category": row.get("category", row.get("分类", "unknown")),
                "source": Path(filepath).name,
            })
    return questions


def import_text_lines(filepath: str) -> list[dict]:
    """从纯文本导入（每行一题）"""
    path = Path(filepath)
    lines = [l.strip() for l in path.read_text(encoding='utf-8').split('\n') if l.strip()]
    return [{"question": line, "answer": "", "tags": [], "category": "unknown", "source": path.name} for line in lines]


def import_file(filepath: str) -> list[dict]:
    """通用导入入口"""
    fmt = detect_format(filepath)
    print(f"📂 检测格式: {fmt}")

    importers = {
        "markdown_questions": import_markdown_questions,
        "markdown_frontmatter": import_markdown_questions,
        "markdown_generic": import_markdown_questions,
        "json_array": import_json_array,
        "interview_coach_json": lambda f: import_json_array(f) if False else json.load(open(f)).get("questions", []),
        "leetcode_json": import_leetcode_json,
        "csv": import_csv,
        "text_lines": import_text_lines,
    }

    importer = importers.get(fmt)
    if importer:
        return importer(filepath)
    return []


def import_leetcode_json(filepath: str) -> list[dict]:
    """从 LeetCode 导出格式导入"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    questions = []
    for item in data.get("stat_status_pairs", []):
        stat = item.get("stat", {})
        difficulty_map = {1: "easy", 2: "medium", 3: "hard"}
        questions.append({
            "question": stat.get("question__title", ""),
            "answer": "",
            "tags": [],
            "category": "java",
            "difficulty": difficulty_map.get(item.get("difficulty", {}).get("level", 2), "medium"),
            "source": "LeetCode",
        })
    return questions


def validate_questions(questions: list[dict]) -> tuple[bool, list[str]]:
    """验证导入数据"""
    issues = []
    if not questions:
        issues.append("没有题目可导入")
    for i, q in enumerate(questions):
        if not q.get("question", "").strip():
            issues.append(f"第 {i+1} 题: 题目为空")
        if len(q.get("question", "")) < 3:
            issues.append(f"第 {i+1} 题: 题目过短 (< 3 字符)")
    return len(issues) == 0, issues


def merge_files(filepaths: list[str]) -> list[dict]:
    """合并多个题库文件"""
    all_questions = []
    for fp in filepaths:
        qs = import_file(fp)
        print(f"  {Path(fp).name}: {len(qs)} 题")
        all_questions.extend(qs)
    # 去重
    seen = set()
    unique = []
    for q in all_questions:
        key = q["question"].strip().lower()[:100]
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


def main():
    parser = argparse.ArgumentParser(description="数据导入器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_import = sub.add_parser("import", help="导入题目")
    p_import.add_argument("filepath")
    p_import.add_argument("--dry-run", action="store_true", help="仅预览不导入")
    p_import.add_argument("--auto-add", action="store_true", help="自动添加到题库")

    p_detect = sub.add_parser("detect", help="检测文件格式")
    p_detect.add_argument("filepath")

    p_merge = sub.add_parser("merge", help="合并多个题库")
    p_merge.add_argument("files", nargs="+")
    p_merge.add_argument("--output", "-o", default="merged_questions.json")

    sub.add_parser("validate", help="验证导入数据")

    p_batch = sub.add_parser("batch", help="批量导入目录")
    p_batch.add_argument("directory")
    p_batch.add_argument("--recursive", "-r", action="store_true")

    args = parser.parse_args()

    if args.cmd == "detect":
        fmt = detect_format(args.filepath)
        print(f"📂 {args.filepath}")
        print(f"   格式: {fmt}")

    elif args.cmd == "import":
        questions = import_file(args.filepath)
        valid, issues = validate_questions(questions)

        print(f"\n📥 导入 {len(questions)} 题")
        if not valid:
            print(f"⚠️  问题:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ 数据格式验证通过")

        if not args.dry_run:
            print("\n预览前 3 题:\n")
            for q in questions[:3]:
                print(f"  📝 {q['question'][:80]}")
                print(f"     🏷️  {', '.join(q.get('tags', [])[:5]) or '无标签'}")
                print(f"     📂 {q.get('category', 'unknown')}")
                print()

            if args.auto_add and valid:
                # 自动添加到题库
                import subprocess
                for q in questions:
                    subprocess.run([
                        sys.executable, str(PROJECT_ROOT / "scripts" / "question_manager.py"),
                        "add", "--question", q["question"],
                        "--answer", q.get("answer", ""),
                        "--category", q.get("category", "unknown"),
                        "--source", q.get("source", "import"),
                    ], cwd=str(PROJECT_ROOT))
                print(f"✅ 已添加 {len(questions)} 题到题库")

    elif args.cmd == "merge":
        merged = merge_files(args.files)
        output = Path(args.output)
        output.write_text(json.dumps({"questions": merged}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n✅ 合并完成: {output} ({len(merged)} 题, 去重后)")

    elif args.cmd == "batch":
        directory = Path(args.directory)
        if not directory.is_dir():
            print(f"❌ 不是目录: {directory}")
            return

        pattern = "**/*" if args.recursive else "*"
        files = [f for f in directory.glob(pattern) if f.is_file() and f.suffix in ['.md', '.json', '.csv', '.txt']]

        print(f"📂 批量导入 {len(files)} 个文件:\n")
        total = 0
        for f in files:
            try:
                qs = import_file(str(f))
                if qs:
                    print(f"  ✅ {f.name}: {len(qs)} 题")
                    total += len(qs)
                else:
                    print(f"  ⚠️  {f.name}: 无法解析")
            except Exception as e:
                print(f"  ❌ {f.name}: {e}")
        print(f"\n📊 共 {total} 题可导入")


if __name__ == "__main__":
    main()
