#!/usr/bin/env python3
"""
Anki 导出器
============
将题库导出为 Anki 兼容的 CSV/APKG 格式，可直接导入 Anki 使用。

功能:
  csv    — 导出为 CSV（Anki 可直接导入）
  apkg   — 导出为 .apkg 文件（需要 genanki 库）
  cards  — 预览将要导出的卡片内容

卡片模板:
  正面: 面试题
  背面: 联想记忆法 + 核心答案摘要 + 标签

Usage:
  python scripts/export_anki.py csv --output interview_deck.csv
  python scripts/export_anki.py csv --category java --difficulty medium
  python scripts/export_anki.py apkg --output interview_deck.apkg
  python scripts/export_anki.py cards --limit 5
"""

import sys
import json
import csv
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
DATABASE_DIR = PROJECT_ROOT / "questions" / "database"


def load_index() -> dict:
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_answer_summary(md_text: str, max_len: int = 500) -> str:
    """从完整答案中提取摘要部分"""
    lines = md_text.strip().split('\n')
    summary_lines = []
    in_summary = False

    for line in lines:
        if re.match(r'^##\s*', line):
            break
        if re.match(r'^#\s*', line):
            continue
        if line.strip().startswith('---'):
            continue
        cleaned = line.strip()
        if cleaned and not cleaned.startswith('>'):
            summary_lines.append(cleaned)
            if sum(len(l) for l in summary_lines) > max_len:
                break

    return '\n'.join(summary_lines) if summary_lines else md_text[:max_len]


def extract_memory_aid(md_text: str) -> str:
    """提取联想记忆法部分"""
    match = re.search(
        r'(?:###?\s*)?🧠.*?联想记忆法(.*?)(?=###?\s*[📖🗺️]|##\s)',
        md_text, re.DOTALL
    )
    if match:
        return match.group(1).strip()[:400]
    # 回退：取前 300 字符
    return md_text[:300]


def generate_cards(index: dict, category: Optional[str] = None,
                   difficulty: Optional[str] = None,
                   tags_filter: Optional[list[str]] = None) -> list[dict]:
    """生成 Anki 卡片列表"""
    cards = []
    cats = index.get("categories", {})

    for q in index.get("questions", []):
        if category and q.get("category") != category:
            continue
        if difficulty and q.get("difficulty") != difficulty:
            continue
        if tags_filter and not any(t in q.get("tags", []) for t in tags_filter):
            continue

        # 读取完整答案
        md_path = PROJECT_ROOT / q.get("file", "")
        full_answer = ""
        if md_path.exists():
            full_answer = md_path.read_text(encoding='utf-8')
            # 去掉 frontmatter
            if full_answer.startswith('---'):
                end = full_answer.find('---', 3)
                if end > 0:
                    full_answer = full_answer[end + 3:].strip()

        memory_aid = extract_memory_aid(full_answer)
        summary = extract_answer_summary(full_answer)
        cat_name = cats.get(q.get("category", ""), {}).get("name", q.get("category", ""))

        cards.append({
            "id": q["id"],
            "question": q["question"],
            "memory_aid": memory_aid,
            "summary": summary,
            "category": cat_name,
            "difficulty": q.get("difficulty", "medium"),
            "tags": " ".join(q.get("tags", [])),
        })

    return cards


def export_csv(cards: list[dict], output_path: Path):
    """导出为 Anki CSV 格式"""
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        # Anki CSV header
        writer.writerow(["Front", "Back", "Tags"])

        for c in cards:
            front = c["question"]
            back = (
                f"<h3>🧠 联想记忆法</h3>{c['memory_aid']}<hr>"
                f"<h3>📖 核心答案</h3>{c['summary']}"
                f"<br><br><small>📂 {c['category']} | 📊 {c['difficulty']}</small>"
            )
            writer.writerow([front, back, c["tags"]])

    print(f"✅ CSV 已导出: {output_path}")
    print(f"   {len(cards)} 张卡片")
    print(f"   在 Anki 中: 文件 → 导入 → 选择此 CSV → 分隔符选逗号 → 导入")


def export_apkg(cards: list[dict], output_path: Path):
    """导出为 .apkg 文件"""
    try:
        import genanki
    except ImportError:
        print("❌ 需要 genanki 库: pip install genanki")
        sys.exit(1)

    model = genanki.Model(
        model_id=hash("interview-coach") % (1 << 31),
        name="Interview Coach Card",
        fields=[
            {"name": "Question"},
            {"name": "MemoryAid"},
            {"name": "Summary"},
            {"name": "Category"},
            {"name": "Tags"},
        ],
        templates=[{
            "name": "Interview Card",
            "qfmt": "<h3>{{Question}}</h3><br><small>{{Tags}}</small>",
            "afmt": (
                "{{FrontSide}}<hr id='answer'>"
                "<h3>🧠 联想记忆法</h3>{{MemoryAid}}<hr>"
                "<h3>📖 核心答案</h3>{{Summary}}"
                "<br><br><small>📂 {{Category}}</small>"
            ),
        }],
        css=".card { font-family: 'PingFang SC', sans-serif; font-size: 16px; } "
            "h3 { color: #333; } hr { margin: 12px 0; }",
    )

    deck = genanki.Deck(
        deck_id=hash("interview-deck") % (1 << 31),
        name=f"Interview Coach ({len(cards)} cards)",
        description=f"Generated by Interview Coach on {datetime.now().strftime('%Y-%m-%d')}",
    )

    for c in cards:
        note = genanki.Note(
            model=model,
            fields=[c["question"], c["memory_aid"], c["summary"], c["category"], c["tags"]],
            tags=c["tags"].split(),
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.write_to_file(str(output_path))
    print(f"✅ APKG 已导出: {output_path}")
    print(f"   {len(cards)} 张卡片")


def main():
    parser = argparse.ArgumentParser(description="Anki 导出器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_csv = sub.add_parser("csv", help="导出 CSV")
    p_csv.add_argument("--output", "-o", default="interview_cards.csv")
    p_csv.add_argument("--category", "-c")
    p_csv.add_argument("--difficulty", "-d", choices=["easy", "medium", "hard"])
    p_csv.add_argument("--tags", "-t", nargs="*")

    p_apkg = sub.add_parser("apkg", help="导出 APKG")
    p_apkg.add_argument("--output", "-o", default="interview_cards.apkg")
    p_apkg.add_argument("--category", "-c")
    p_apkg.add_argument("--difficulty", "-d", choices=["easy", "medium", "hard"])

    p_cards = sub.add_parser("cards", help="预览卡片")
    p_cards.add_argument("--limit", "-n", type=int, default=5)
    p_cards.add_argument("--category", "-c")

    args = parser.parse_args()
    index = load_index()

    if args.cmd in ("csv", "apkg", "cards"):
        cards = generate_cards(
            index,
            category=getattr(args, 'category', None),
            difficulty=getattr(args, 'difficulty', None),
            tags_filter=getattr(args, 'tags', None),
        )

    if args.cmd == "csv":
        export_csv(cards, Path(args.output))
    elif args.cmd == "apkg":
        export_apkg(cards, Path(args.output))
    elif args.cmd == "cards":
        limit = getattr(args, 'limit', 5)
        print(f"\n📋 预览前 {min(limit, len(cards))} 张卡片:\n")
        for i, c in enumerate(cards[:limit], 1):
            print(f"{'='*50}")
            print(f"卡片 {i}  [{c['id']}]")
            print(f"📝 正面: {c['question'][:100]}")
            print(f"🧠 记忆法: {c['memory_aid'][:150]}...")
            print(f"🏷️  标签: {c['tags']}")
            print()


if __name__ == "__main__":
    main()
