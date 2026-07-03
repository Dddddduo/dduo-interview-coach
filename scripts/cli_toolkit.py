#!/usr/bin/env python3
"""
CLI 工具箱
===========
Interview Coach 的命令行统一入口。集成了题库管理、答题、复习、统计等所有功能。

Usage:
  python scripts/cli_toolkit.py ask "什么是CAP理论？"
  python scripts/cli_toolkit.py stats
  python scripts/cli_toolkit.py review
  python scripts/cli_toolkit.py search "B+树"
  python scripts/cli_toolkit.py quiz --count 5
  python scripts/cli_toolkit.py journal write
  python scripts/cli_toolkit.py export csv
  python scripts/cli_toolkit.py sync
"""

import sys, json, os, argparse, subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_script(name, *args):
    """运行同目录下的脚本"""
    script = SCRIPTS_DIR / f"{name}.py"
    if not script.exists():
        print(f"❌ 脚本不存在: {script}")
        return 1
    cmd = [sys.executable, str(script)] + list(args)
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT)).returncode


def cmd_stats():
    """显示整体统计仪表盘"""
    print(f"\n{'='*55}")
    print(f"  🎯 Interview Coach — 状态仪表盘")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    # 题库统计
    run_script("question_manager", "stats")

    # Git 状态
    try:
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        changes = [l for l in result.stdout.strip().split('\n') if l]
        print(f"\n📂 Git 状态: {len(changes)} 个变更" if changes else "\n📂 Git: clean")
    except:
        pass

    # 学习统计
    run_script("progress_tracker", "overview")


def cmd_review():
    """交互式复习模式"""
    index_file = PROJECT_ROOT / "questions" / "index.json"
    if not index_file.exists():
        print("❌ 题库为空")
        return

    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)

    questions = index.get("questions", [])
    if not questions:
        print("❌ 题库为空")
        return

    print(f"\n📝 交互式复习 ({len(questions)} 题)")
    print(f"  输入 s=跳过, q=退出, y=记住了, n=没记住")
    print(f"{'='*55}")

    score = 0
    reviewed = 0
    reviewed_today = set()

    import random
    qs = list(questions)
    random.shuffle(qs)

    for i, q in enumerate(qs, 1):
        print(f"\n[{i}/{len(qs)}] [{q['id']}] {q['question'][:100]}")
        ans = input("  [y/n/s/q]: ").strip().lower()

        if ans == 'q':
            break
        elif ans == 's':
            continue
        elif ans == 'y':
            score += 1
            reviewed_today.add(q['id'])
        elif ans == 'n':
            reviewed_today.add(q['id'])
        reviewed += 1

    print(f"\n📊 本次: {score}/{reviewed} 记住了 | {'='*30}")
    if reviewed_today:
        today = datetime.now().strftime("%Y-%m-%d")
        existing = set(json.loads(local_storage_get(f"reviewed_{today}", "[]")))
        existing.update(reviewed_today)
        local_storage_set(f"reviewed_{today}", json.dumps(list(existing)))
        print(f"  ✅ 已记录 {len(reviewed_today)} 题复习状态")


def local_storage_get(key, default=""):
    """模拟 localStorage"""
    import tempfile
    storage_dir = Path(tempfile.gettempdir()) / "interview_coach_cli"
    storage_dir.mkdir(exist_ok=True)
    f = storage_dir / f"{key}.json"
    if f.exists():
        return f.read_text()
    return default


def local_storage_set(key, value):
    import tempfile
    storage_dir = Path(tempfile.gettempdir()) / "interview_coach_cli"
    storage_dir.mkdir(exist_ok=True)
    (storage_dir / f"{key}.json").write_text(value)


def cmd_daily():
    """每日摘要"""
    print(f"\n📅 每日摘要 — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*55}")

    run_script("review_scheduler", "plan")
    print()
    run_script("progress_tracker", "overview")


def cmd_quick_add():
    """快速添加单题（交互式）"""
    print("📝 快速添加题目")
    question = input("题目: ").strip()
    if not question:
        print("已取消")
        return

    print("答案 (输入 END 结束):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    answer = "\n".join(lines)

    if not answer.strip():
        print("❌ 答案不能为空")
        return

    run_script("question_manager", "add", "--question", question, "--answer", answer)


def main():
    parser = argparse.ArgumentParser(
        description="CLI 工具箱 — Interview Coach 命令行统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  cli_toolkit.py stats        查看总览
  cli_toolkit.py ask "什么是CAP?"  答题
  cli_toolkit.py review       交互式复习
  cli_toolkit.py daily        每日摘要
  cli_toolkit.py quick-add    快速添加题目
  cli_toolkit.py search "B+树"  搜索
  cli_toolkit.py export csv   导出 CSV
  cli_toolkit.py sync         完整同步
  cli_toolkit.py backup       备份题库
""",
    )

    sub = parser.add_subparsers(dest="cmd")

    p_ask = sub.add_parser("ask", help="答题")
    p_ask.add_argument("question", help="题目文本")

    sub.add_parser("stats", help="总览仪表盘")
    sub.add_parser("review", help="交互式复习")
    sub.add_parser("daily", help="每日摘要")
    sub.add_parser("quick-add", help="快速添加")

    p_search = sub.add_parser("search", help="搜索题库")
    p_search.add_argument("keyword")

    p_quiz = sub.add_parser("quiz", help="生成测验")
    p_quiz.add_argument("--count", "-n", type=int, default=5)
    p_quiz.add_argument("--type", "-t", default="recall", choices=["recall", "multiple_choice", "fill_blank"])

    p_export = sub.add_parser("export", help="导出")
    p_export.add_argument("format", choices=["csv", "anki", "markdown", "json"])
    p_export.add_argument("--output", "-o")

    sub.add_parser("sync", help="完整同步到 docs/")
    sub.add_parser("backup", help="备份题库")

    p_journal = sub.add_parser("journal", help="学习日志")
    p_journal.add_argument("action", choices=["write", "read", "list", "streak"], default="list")

    args = parser.parse_args()

    if not args.cmd:
        # 默认显示 stats
        cmd_stats()
    elif args.cmd == "ask":
        run_script("interview_agent", args.question)
    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "review":
        cmd_review()
    elif args.cmd == "daily":
        cmd_daily()
    elif args.cmd == "quick-add":
        cmd_quick_add()
    elif args.cmd == "search":
        run_script("question_manager", "search", args.keyword)
    elif args.cmd == "quiz":
        run_script("quiz_generator", "generate", "--count", str(args.count), "--type", args.type)
    elif args.cmd == "export":
        if args.format == "csv" or args.format == "anki":
            run_script("export_anki", "csv", *(["-o", args.output] if args.output else []))
        elif args.format == "markdown":
            run_script("question_manager", "export", "--format", "markdown", *(["-o", args.output] if args.output else []))
        elif args.format == "json":
            run_script("question_manager", "export", "--format", "json", *(["-o", args.output] if args.output else []))
    elif args.cmd == "sync":
        run_script("sync_manager", "sync-all")
    elif args.cmd == "backup":
        run_script("sync_manager", "backup")
    elif args.cmd == "journal":
        run_script("daily_journal", args.action)


if __name__ == "__main__":
    main()
