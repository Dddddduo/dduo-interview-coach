#!/usr/bin/env python3
"""
学习进度追踪器
===============
全面的学习进度追踪、可视化和报告系统。

功能:
  overview  — 学习总览（题数、分类覆盖、进度百分比）
  timeline  — 学习时间线（按日期展示学习活动）
  coverage  — 分类覆盖率分析
  report    — 生成学习报告（Markdown）
  compare   — 对比两个时间点的进度

Usage:
  python scripts/progress_tracker.py overview
  python scripts/progress_tracker.py timeline
  python scripts/progress_tracker.py coverage
  python scripts/progress_tracker.py report --output progress_report.md
  python scripts/progress_tracker.py compare 2026-06-01 2026-07-01
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
JOURNAL_DIR = PROJECT_ROOT / "questions" / "journals"


def load_index() -> dict:
    if not INDEX_FILE.exists():
        return {"meta": {}, "categories": {}, "questions": []}
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_journals() -> list[dict]:
    journals = []
    if JOURNAL_DIR.exists():
        for fp in sorted(JOURNAL_DIR.glob("*.md")):
            text = fp.read_text(encoding='utf-8')
            meta = {}
            if text.startswith('---'):
                end = text.find('---', 3)
                if end > 0:
                    for line in text[3:end].strip().split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            meta[k.strip()] = v.strip()
            meta['date'] = fp.stem
            journals.append(meta)
    return journals


def overview(index: dict, journals: list[dict]) -> dict:
    """学习总览"""
    questions = index.get("questions", [])
    categories = index.get("categories", {})
    diffs = index.get("difficulty_levels", {})

    # 分类统计
    cat_counts = defaultdict(int)
    for q in questions:
        cat_counts[q.get("category", "unknown")] += 1

    # 难度统计
    diff_counts = defaultdict(int)
    for q in questions:
        diff_counts[q.get("difficulty", "medium")] += 1

    # 时间统计
    dates = sorted(set(q.get("created", "")[:10] for q in questions if q.get("created")))
    first_date = dates[0] if dates else "N/A"
    last_date = dates[-1] if dates else "N/A"

    # 日志统计
    total_reviewed = sum(int(j.get("questions_reviewed", 0) or 0) for j in journals)
    total_study_time = 0
    for j in journals:
        st = j.get("study_time", "0h")
        try:
            if st.endswith('h'):
                total_study_time += float(st[:-1])
            elif st.endswith('m'):
                total_study_time += float(st[:-1]) / 60
        except ValueError:
            pass

    return {
        "total_questions": len(questions),
        "total_categories": len([c for c in cat_counts if cat_counts[c] > 0]),
        "category_coverage": dict(cat_counts),
        "difficulty_distribution": dict(diff_counts),
        "first_question": first_date,
        "last_question": last_date,
        "total_journals": len(journals),
        "total_reviewed": total_reviewed,
        "total_study_hours": round(total_study_time, 1),
        "questions_per_day": round(len(questions) / max((journals and len(journals) or 1), 1), 1),
    }


def timeline(index: dict, journals: list[dict]) -> dict:
    """学习时间线"""
    events = []

    # 题库添加事件
    for q in index.get("questions", []):
        if q.get("created"):
            events.append({
                "date": q["created"][:10],
                "type": "new_question",
                "detail": f"添加题目 [{q['id']}] {q['question'][:60]}",
                "category": q.get("category", ""),
            })

    # 日志事件
    for j in journals:
        events.append({
            "date": j.get("date", ""),
            "type": "journal",
            "detail": f"学习日志 — 复习 {j.get('questions_reviewed', '?')} 题",
            "mood": j.get("mood", ""),
        })

    # 按日期分组
    events.sort(key=lambda e: e["date"])
    by_date = defaultdict(list)
    for e in events:
        by_date[e["date"]].append(e)

    return dict(by_date)


def coverage(index: dict) -> dict:
    """分类覆盖率分析"""
    categories = index.get("categories", {})
    questions = index.get("questions", [])

    cat_coverage = {}
    for cat_key, cat_info in categories.items():
        qs_in_cat = [q for q in questions if q.get("category") == cat_key]
        by_diff = defaultdict(int)
        for q in qs_in_cat:
            by_diff[q.get("difficulty", "medium")] += 1

        cat_coverage[cat_key] = {
            "name": cat_info.get("name", cat_key),
            "total": len(qs_in_cat),
            "by_difficulty": dict(by_diff),
            "percentage": round(len(qs_in_cat) / max(len(questions), 1) * 100, 1),
        }

    # 薄弱分类（题目最少的）
    weak = sorted(
        [(k, v) for k, v in cat_coverage.items()],
        key=lambda x: x[1]["total"]
    )[:5]

    # 优势分类（题目最多的）
    strong = sorted(
        [(k, v) for k, v in cat_coverage.items() if v["total"] > 0],
        key=lambda x: -x[1]["total"]
    )[:5]

    return {
        "categories": cat_coverage,
        "weak_areas": [{"category": k, **v} for k, v in weak if v["total"] == 0],
        "strong_areas": [{"category": k, **v} for k, v in strong],
        "recommendation": "建议优先补充题目数为 0 的分类",
    }


def generate_report(ov: dict, tl: dict, cov: dict) -> str:
    """生成 Markdown 学习报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 📊 学习进度报告",
        f"> 生成时间: {now}",
        "",
        "## 📈 总体概览",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 题库总数 | {ov['total_questions']} 题 |",
        f"| 覆盖分类 | {ov['total_categories']} 个 |",
        f"| 学习日志 | {ov['total_journals']} 篇 |",
        f"| 累计复习 | {ov['total_reviewed']} 题 |",
        f"| 学习时长 | {ov['total_study_hours']} 小时 |",
        f"| 日均新增 | {ov['questions_per_day']} 题 |",
        f"| 首次学习 | {ov['first_question']} |",
        f"| 最近学习 | {ov['last_question']} |",
        "",
        "## 📂 分类覆盖",
        "| 分类 | 题目数 | 占比 |",
        "|------|--------|------|",
    ]

    for cat, count in sorted(ov["category_coverage"].items(), key=lambda x: -x[1]):
        pct = round(count / max(ov["total_questions"], 1) * 100)
        bar = "█" * (pct // 5)
        lines.append(f"| {cat} | {count} | {bar} {pct}% |")

    lines += [
        "",
        "## 📊 难度分布",
        "| 难度 | 题数 |",
        "|------|------|",
    ]
    for diff, count in ov["difficulty_distribution"].items():
        lines.append(f"| {diff} | {count} |")

    lines += [
        "",
        "## ⚠️ 待加强领域",
    ]
    for w in cov.get("weak_areas", [])[:5]:
        lines.append(f"- {w['name']}: 0 题 — 建议优先补充")

    lines += [
        "",
        "## 🎯 建议",
        f"1. 当前题库 {ov['total_questions']} 题，建议继续扩充至 50+ 题以覆盖更多知识点",
        f"2. 薄弱分类需补充题目以提升覆盖率",
        f"3. 建议每天至少复习 5 题，保持学习连续性",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="学习进度追踪器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("overview", help="学习总览")
    sub.add_parser("timeline", help="学习时间线")
    sub.add_parser("coverage", help="分类覆盖率")

    p_report = sub.add_parser("report", help="生成学习报告")
    p_report.add_argument("--output", "-o", help="输出文件路径")

    p_compare = sub.add_parser("compare", help="对比进度")
    p_compare.add_argument("date1")
    p_compare.add_argument("date2")

    args = parser.parse_args()
    index = load_index()
    journals = load_journals()

    if args.cmd == "overview":
        ov = overview(index, journals)
        print(f"\n📊 学习总览")
        print(f"{'='*50}")
        print(f"  📝 题库总数: {ov['total_questions']} 题")
        print(f"  📂 覆盖分类: {ov['total_categories']} 个")
        print(f"  📔 学习日志: {ov['total_journals']} 篇")
        print(f"  ✅ 累计复习: {ov['total_reviewed']} 题")
        print(f"  ⏱️  学习时长: {ov['total_study_hours']} 小时")
        print(f"  📈 日均新增: {ov['questions_per_day']} 题")
        print(f"  📅 学习周期: {ov['first_question']} ~ {ov['last_question']}")
        print(f"\n📂 分类分布:")
        for cat, count in sorted(ov["category_coverage"].items(), key=lambda x: -x[1]):
            if count > 0:
                bar = "█" * min(count, 30)
                print(f"  {cat:20s} {count:3d} {bar}")

    elif args.cmd == "timeline":
        tl = timeline(index, journals)
        print(f"\n📅 学习时间线 ({len(tl)} 天)\n")
        for date in sorted(tl.keys(), reverse=True)[:30]:
            events = tl[date]
            q_count = sum(1 for e in events if e["type"] == "new_question")
            j_count = sum(1 for e in events if e["type"] == "journal")
            print(f"  📅 {date} | 新增 {q_count} 题 | 日志 {j_count} 篇")
            for e in events[:3]:
                icon = "📝" if e["type"] == "new_question" else "📔"
                print(f"    {icon} {e['detail'][:80]}")
            if len(events) > 3:
                print(f"    ... 还有 {len(events)-3} 条")

    elif args.cmd == "coverage":
        cov = coverage(index)
        print(f"\n📊 分类覆盖率分析\n")
        print(f"{'分类':20s} {'题数':>5s} {'占比':>6s} {'基础':>5s} {'中级':>5s} {'进阶':>5s}")
        print(f"{'-'*55}")
        for cat_key, info in cov["categories"].items():
            if info["total"] > 0:
                diffs = info.get("by_difficulty", {})
                print(f"{info['name']:20s} {info['total']:5d} {info['percentage']:5.1f}% "
                      f"{diffs.get('easy',0):5d} {diffs.get('medium',0):5d} {diffs.get('hard',0):5d}")

        if cov["weak_areas"]:
            print(f"\n⚠️  待补充分类: {', '.join(w['name'] for w in cov['weak_areas'])}")

    elif args.cmd == "report":
        ov = overview(index, journals)
        tl = timeline(index, journals)
        cov = coverage(index)
        report = generate_report(ov, tl, cov)

        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            print(f"✅ 报告已保存: {args.output}")
        else:
            print(report)

    elif args.cmd == "compare":
        # 简化版对比：只看两个日期的题库变化
        questions = index.get("questions", [])
        before = [q for q in questions if q.get("created", "")[:10] <= args.date1]
        after = [q for q in questions if q.get("created", "")[:10] <= args.date2]
        new_qs = [q for q in after if q["id"] not in {x["id"] for x in before}]

        print(f"\n📊 进度对比: {args.date1} → {args.date2}")
        print(f"{'='*50}")
        print(f"  {args.date1}: {len(before)} 题")
        print(f"  {args.date2}: {len(after)} 题")
        print(f"  新增: {len(new_qs)} 题 ({round(len(new_qs)/max(len(before),1)*100)}% 增长)")
        if new_qs:
            print(f"\n  新增题目:")
            cats = defaultdict(int)
            for q in new_qs:
                cats[q.get("category", "?")] += 1
            for cat, count in cats.items():
                print(f"    {cat}: +{count} 题")


if __name__ == "__main__":
    main()
