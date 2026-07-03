#!/usr/bin/env python3
"""
标签分析器
===========
深入分析题库中的标签分布、关联模式和学习路径。

功能:
  analyze    — 标签全景分析
  path       — 推荐学习路径（基于依赖关系）
  compare    — 标签对比分析
  trends     — 标签趋势（按时间）
  coverage   — 标签覆盖率分析

Usage:
  python scripts/tag_analyzer.py analyze
  python scripts/tag_analyzer.py path --goal "微服务架构"
  python scripts/tag_analyzer.py trends
"""

import sys, json, argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"


def load_index():
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_tags(index: dict) -> dict:
    """全景标签分析"""
    questions = index.get("questions", [])
    categories = index.get("categories", {})

    tag_info = {}
    for q in questions:
        for tag in q.get("tags", []):
            if tag not in tag_info:
                tag_info[tag] = {
                    "count": 0, "categories": defaultdict(int),
                    "difficulties": defaultdict(int), "co_tags": defaultdict(int),
                    "questions": [], "first_seen": None, "last_seen": None,
                }
            info = tag_info[tag]
            info["count"] += 1
            info["categories"][q.get("category", "unknown")] += 1
            info["difficulties"][q.get("difficulty", "medium")] += 1
            info["questions"].append(q["id"])

            created = q.get("created", "")
            if not info["first_seen"] or created < info["first_seen"]:
                info["first_seen"] = created
            if not info["last_seen"] or created > info["last_seen"]:
                info["last_seen"] = created

            # 共现标签
            for other in q.get("tags", []):
                if other != tag:
                    info["co_tags"][other] += 1

    return tag_info


def recommend_path(index: dict, goal: str, max_steps: int = 10) -> list[dict]:
    """推荐学习路径"""
    tag_info = analyze_tags(index)
    if goal not in tag_info:
        print(f"❌ 未找到目标标签: {goal}")
        return []

    path = []
    current = goal
    visited = set()

    for _ in range(max_steps):
        if current in visited:
            break
        visited.add(current)
        info = tag_info.get(current, {})
        path.append({
            "tag": current,
            "count": info.get("count", 0),
            "prerequisite": sorted(
                [(t, c) for t, c in info.get("co_tags", {}).items() if t not in visited],
                key=lambda x: -x[1]
            )[:5],
        })

        # 找下一个：最相关的未访问标签
        co_tags = info.get("co_tags", {})
        candidates = [(t, c) for t, c in co_tags.items() if t not in visited]
        if not candidates:
            break
        candidates.sort(key=lambda x: -x[1])
        # 选择关联最强但不是已访问的
        current = candidates[0][0]

    return path


def trends(index: dict) -> list[dict]:
    """标签趋势（按月）"""
    questions = index.get("questions", [])
    monthly = defaultdict(lambda: defaultdict(int))

    for q in questions:
        created = q.get("created", "")
        if not created:
            continue
        month = created[:7]  # YYYY-MM
        for tag in q.get("tags", []):
            monthly[month][tag] += 1

    return [{"month": m, "tags": dict(tags)} for m, tags in sorted(monthly.items())]


def main():
    parser = argparse.ArgumentParser(description="标签分析器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("analyze", help="标签全景分析")

    p_path = sub.add_parser("path", help="推荐学习路径")
    p_path.add_argument("--goal", "-g", required=True, help="目标标签")
    p_path.add_argument("--steps", "-n", type=int, default=10)

    p_compare = sub.add_parser("compare", help="标签对比")
    p_compare.add_argument("tags", nargs="+", help="要对比的标签")

    sub.add_parser("trends", help="标签趋势")
    sub.add_parser("coverage", help="标签覆盖率")

    args = parser.parse_args()
    index = load_index()

    if args.cmd == "analyze":
        tag_info = analyze_tags(index)
        print(f"\n🏷️  标签分析 ({len(tag_info)} 个标签)\n{'='*55}")

        # Top 20
        sorted_tags = sorted(tag_info.items(), key=lambda x: -x[1]["count"])
        for tag, info in sorted_tags[:20]:
            main_cat = max(info["categories"], key=info["categories"].get)
            top_co = sorted(info["co_tags"].items(), key=lambda x: -x[1])[:3]
            print(f"  {tag:18s} {info['count']:3d}题 | 主分类:{main_cat:15s} | 关联:{', '.join(f'{t}({c})' for t,c in top_co)}")

        # 孤立标签（无共现）
        isolated = [t for t, info in tag_info.items() if not info["co_tags"]]
        if isolated:
            print(f"\n⚠️  孤立标签 ({len(isolated)}): {', '.join(isolated)}")

    elif args.cmd == "path":
        path = recommend_path(index, args.goal, args.steps)
        if path:
            print(f"\n🧭 学习路径 → {args.goal}\n{'='*50}")
            for i, step in enumerate(path):
                print(f"  {i+1}. {step['tag']} ({step['count']} 题)")
                if step["prerequisite"]:
                    print(f"     └ 前置: {', '.join(f'{t}({c})' for t,c in step['prerequisite'][:3])}")

    elif args.cmd == "compare":
        tag_info = analyze_tags(index)
        print(f"\n📊 标签对比\n{'='*55}")
        print(f"{'标签':18s} {'题数':>5s} {'基础':>5s} {'中级':>5s} {'进阶':>5s}")
        print(f"{'-'*45}")
        for tag in args.tags:
            info = tag_info.get(tag, {})
            diffs = info.get("difficulties", {})
            print(f"  {tag:16s} {info.get('count',0):5d} {diffs.get('easy',0):5d} {diffs.get('medium',0):5d} {diffs.get('hard',0):5d}")

    elif args.cmd == "trends":
        trend_data = trends(index)
        print(f"\n📈 标签趋势 (按月):\n")
        for entry in trend_data:
            tags = entry["tags"]
            if not tags:
                continue
            print(f"  {entry['month']}: {sum(tags.values())} 个标签实例")
            for tag, count in sorted(tags.items(), key=lambda x: -x[1])[:5]:
                print(f"    {tag}: {count}")

    elif args.cmd == "coverage":
        tag_info = analyze_tags(index)
        questions = index.get("questions", [])
        categories = index.get("categories", {})

        print(f"\n📊 标签覆盖率\n{'='*55}")
        for cat_key, cat_data in categories.items():
            cat_qs = [q for q in questions if q.get("category") == cat_key]
            cat_tags = set()
            for q in cat_qs:
                cat_tags.update(q.get("tags", []))
            print(f"  {cat_data.get('icon','')} {cat_data.get('name',cat_key):20s}: {len(cat_qs):3d}题 | {len(cat_tags):3d}个标签")


if __name__ == "__main__":
    main()
