#!/usr/bin/env python3
"""
数据同步管理器
===============
管理 questions/ ↔ docs/ 之间的数据同步，确保 GitHub Pages 数据始终最新。

功能:
  sync-all   — 完整同步（index + HTML + data.json + 清理过期文件）
  watch      — 监听文件变化自动同步
  clean      — 清理 docs/q/ 中无对应题库的孤立 HTML
  validate   — 验证数据一致性
  backup     — 备份题库到 zip

Usage:
  python scripts/sync_manager.py sync-all
  python scripts/sync_manager.py watch
  python scripts/sync_manager.py clean
  python scripts/sync_manager.py validate
  python scripts/sync_manager.py backup --output backup.zip
"""

import sys
import json
import shutil
import argparse
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
DATABASE_DIR = PROJECT_ROOT / "questions" / "database"
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_Q_DIR = DOCS_DIR / "q"
DOCS_DATA = DOCS_DIR / "data.json"
DOCS_INDEX = DOCS_DIR / "index.json"
JOURNALS_DIR = PROJECT_ROOT / "questions" / "journals"


def load_index() -> dict:
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"questions": []}


def sync_all(force: bool = False):
    """完整同步流程"""
    print("🔄 完整同步...")
    steps = []

    # Step 1: 同步 index.json
    if INDEX_FILE.exists():
        shutil.copy2(INDEX_FILE, DOCS_INDEX)
        steps.append(("index.json → docs/", True))

    # Step 2: 调用 generate_site.py
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_site.py"),
             *(["--force"] if force else [])],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=120
        )
        steps.append(("generate_site.py", result.returncode == 0))
        if result.returncode != 0:
            print(f"  ⚠️  {result.stderr[:200]}")
    except Exception as e:
        steps.append(("generate_site.py", False))
        print(f"  ❌ {e}")

    # Step 3: 清理孤立 HTML
    cleaned = clean_orphans(dry_run=False)
    steps.append((f"清理 {cleaned} 个孤立文件", True))

    # Step 4: 验证
    valid, issues = validate_consistency()
    steps.append((f"数据验证: {'✅' if valid else '⚠️ '+str(len(issues))+' 个问题'}", valid))

    print(f"\n📊 同步完成:")
    for name, ok in steps:
        print(f"  {'✅' if ok else '⚠️'} {name}")


def clean_orphans(dry_run: bool = True) -> int:
    """清理无对应题库的孤立 HTML"""
    index = load_index()
    valid_ids = {q["id"] for q in index.get("questions", [])}

    if not DOCS_Q_DIR.exists():
        return 0

    removed = 0
    for html_file in DOCS_Q_DIR.glob("*.html"):
        qid = html_file.stem  # e.g., q0001.html → q0001
        if qid not in valid_ids:
            if dry_run:
                print(f"  [DRY RUN] 将删除孤立文件: {html_file.name}")
            else:
                html_file.unlink()
                print(f"  🗑️  已删除: {html_file.name}")
            removed += 1

    return removed


def validate_consistency() -> tuple[bool, list[str]]:
    """验证数据一致性"""
    issues = []
    index = load_index()
    index_qs = index.get("questions", [])

    # 检查 index 中的 file 字段是否存在
    for q in index_qs:
        filepath = PROJECT_ROOT / q.get("file", "")
        if not filepath.exists():
            issues.append(f"[{q['id']}] 源文件不存在: {q.get('file')}")

    # 检查 docs/data.json 是否存在
    if not DOCS_DATA.exists():
        issues.append("docs/data.json 不存在")
    else:
        try:
            with open(DOCS_DATA, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data_qs_count = len(data.get("questions", []))
            if data_qs_count != len(index_qs):
                issues.append(f"data.json 题目数({data_qs_count}) ≠ index.json({len(index_qs)})")
        except Exception as e:
            issues.append(f"docs/data.json 解析失败: {e}")

    # 检查 docs/q/ 下的 HTML 是否与 index 一致
    if DOCS_Q_DIR.exists():
        html_ids = {f.stem for f in DOCS_Q_DIR.glob("*.html")}
        index_ids = {q["id"] for q in index_qs}

        missing_html = index_ids - html_ids
        orphan_html = html_ids - index_ids

        if missing_html:
            issues.append(f"缺少 HTML: {len(missing_html)} 个 ({', '.join(sorted(missing_html)[:5])}...)")
        if orphan_html:
            issues.append(f"孤立 HTML: {len(orphan_html)} 个")

    return len(issues) == 0, issues


def backup(output_path: str):
    """备份题库到 zip"""
    output = Path(output_path)
    if not output.suffix:
        output = output.with_suffix('.zip')

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 备份 index
        if INDEX_FILE.exists():
            zf.write(INDEX_FILE, INDEX_FILE.relative_to(PROJECT_ROOT))

        # 备份所有数据库文件
        for md_file in DATABASE_DIR.rglob("*.md"):
            zf.write(md_file, md_file.relative_to(PROJECT_ROOT))

        # 备份日志
        if JOURNALS_DIR.exists():
            for jf in JOURNALS_DIR.glob("*.md"):
                zf.write(jf, jf.relative_to(PROJECT_ROOT))

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"✅ 备份完成: {output} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="数据同步管理器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync-all", help="完整同步")
    p_sync.add_argument("--force", action="store_true", help="强制重新生成")

    sub.add_parser("clean", help="清理孤立文件")
    sub.add_parser("validate", help="验证数据一致性")

    p_backup = sub.add_parser("backup", help="备份题库")
    p_backup.add_argument("--output", "-o", default="backup.zip")

    args = parser.parse_args()

    if args.cmd == "sync-all":
        sync_all(force=args.force)
    elif args.cmd == "clean":
        removed = clean_orphans(dry_run=True)
        if removed > 0:
            ans = input(f"\n确认删除 {removed} 个孤立文件? [y/N]: ").strip().lower()
            if ans == 'y':
                clean_orphans(dry_run=False)
            else:
                print("已取消")
        else:
            print("✅ 没有孤立文件需要清理")
    elif args.cmd == "validate":
        valid, issues = validate_consistency()
        if valid:
            print("✅ 数据一致性检查通过")
        else:
            print(f"⚠️  发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"  - {issue}")
    elif args.cmd == "backup":
        backup(args.output)


if __name__ == "__main__":
    main()
