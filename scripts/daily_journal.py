#!/usr/bin/env python3
"""
每日学习日志
=============
记录每日复习内容、心得笔记、学习计划。

功能:
  write   — 写一篇今日日志（复习内容+心得+明日计划）
  read    — 读取指定日期的日志
  list    — 列出所有日志
  summary — 生成学习总结报告
  streak  — 查看连续学习天数

Usage:
  python scripts/daily_journal.py write
  python scripts/daily_journal.py read 2026-07-04
  python scripts/daily_journal.py list
  python scripts/daily_journal.py summary
  python scripts/daily_journal.py streak
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNAL_DIR = PROJECT_ROOT / "questions" / "journals"
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE = """---
date: {date}
mood: {mood}
study_time: {study_time}
questions_reviewed: {questions_reviewed}
---

# 📅 学习日志 — {date}

## 📝 今日复习内容
{review_content}

## 💡 心得与收获
{insights}

## ⚠️ 遇到的困难
{difficulties}

## 📋 明日计划
{tomorrow_plan}

## 🏷️ 涉及知识点
{topics}
"""


def journal_path(date_str: str) -> Path:
    return JOURNAL_DIR / f"{date_str}.md"


def parse_journal(filepath: Path) -> dict:
    """解析日志文件的 frontmatter"""
    text = filepath.read_text(encoding='utf-8')
    meta = {}
    if text.startswith('---'):
        end = text.find('---', 3)
        if end > 0:
            for line in text[3:end].strip().split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
    meta['content'] = text
    meta['file'] = str(filepath)
    return meta


def write_journal(date_str: str, mood: str, study_time: str,
                  review_content: str, insights: str,
                  difficulties: str, tomorrow_plan: str,
                  topics: str, questions_reviewed: str):
    """写入日志"""
    fp = journal_path(date_str)
    content = TEMPLATE.format(
        date=date_str,
        mood=mood,
        study_time=study_time,
        questions_reviewed=questions_reviewed,
        review_content=review_content or "（待补充）",
        insights=insights or "（待补充）",
        difficulties=difficulties or "（无）",
        tomorrow_plan=tomorrow_plan or "（待规划）",
        topics=topics or "（待标注）",
    )
    fp.write_text(content, encoding='utf-8')
    return fp


def list_journals() -> list[dict]:
    """列出所有日志"""
    journals = []
    for fp in sorted(JOURNAL_DIR.glob("*.md"), reverse=True):
        journals.append(parse_journal(fp))
    return journals


def generate_summary() -> dict:
    """生成学习总结"""
    journals = list_journals()
    if not journals:
        return {"error": "暂无日志"}

    total_days = len(journals)
    total_reviewed = sum(int(j.get("questions_reviewed", 0) or 0) for j in journals)
    moods = defaultdict(int)
    for j in journals:
        m = j.get("mood", "neutral")
        moods[m] += 1

    return {
        "total_days": total_days,
        "total_questions_reviewed": total_reviewed,
        "avg_per_day": round(total_reviewed / total_days, 1) if total_days else 0,
        "mood_distribution": dict(moods),
        "first_entry": journals[-1].get("date", "") if journals else "",
        "last_entry": journals[0].get("date", "") if journals else "",
        "recent": journals[:7],
    }


def calc_streak() -> dict:
    """计算连续学习天数"""
    journals = list_journals()
    dates = set(j.get("date", "") for j in journals)

    today = datetime.now().strftime("%Y-%m-%d")
    streak = 0
    d = datetime.now()
    while True:
        ds = d.strftime("%Y-%m-%d")
        if ds in dates:
            streak += 1
            d -= timedelta(days=1)
        else:
            # 如果连续断了且不是今天，检查是否是今天没写但昨天写了
            if ds == today and streak == 0:
                d -= timedelta(days=1)
                continue
            break

    # 本月统计
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    this_month = sum(1 for ds in dates if ds >= month_start)

    return {
        "streak": streak,
        "total_entries": len(journals),
        "this_month": this_month,
        "dates": sorted(dates, reverse=True),
    }


def main():
    parser = argparse.ArgumentParser(description="每日学习日志")
    sub = parser.add_subparsers(dest="cmd")

    # write
    p_write = sub.add_parser("write", help="写一篇今日日志")
    p_write.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    p_write.add_argument("--mood", default="neutral",
                         choices=["great", "good", "neutral", "tired", "bad"])
    p_write.add_argument("--study-time", default="1h", help="学习时长")
    p_write.add_argument("--reviewed", default="0", help="复习题数")
    p_write.add_argument("--content", default="", help="复习内容")
    p_write.add_argument("--insights", default="", help="心得收获")
    p_write.add_argument("--difficulties", default="", help="困难")
    p_write.add_argument("--plan", default="", help="明日计划")
    p_write.add_argument("--topics", default="", help="知识点")
    p_write.add_argument("--interactive", "-i", action="store_true", help="交互式输入")

    # read
    p_read = sub.add_parser("read", help="读取指定日期日志")
    p_read.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"))

    # list
    p_list = sub.add_parser("list", help="列出所有日志")
    p_list.add_argument("--limit", "-n", type=int, default=10, help="显示条数")

    # summary
    sub.add_parser("summary", help="生成学习总结")

    # streak
    sub.add_parser("streak", help="连续学习天数")

    args = parser.parse_args()

    if args.cmd == "write":
        if args.interactive:
            print("📝 写学习日志 (输入 . 结束):\n")
            mood = input("😊 心情 (great/good/neutral/tired/bad) [neutral]: ").strip() or "neutral"
            study_time = input("⏱️  学习时长 [1h]: ").strip() or "1h"
            reviewed = input("📚 复习题数 [0]: ").strip() or "0"
            print("📝 复习内容 (多行，输入 . 结束):")
            content_lines = []
            while True:
                line = input()
                if line == ".": break
                content_lines.append(line)
            print("💡 心得收获:")
            insight_lines = []
            while True:
                line = input()
                if line == ".": break
                insight_lines.append(line)
            print("⚠️ 困难:")
            diff_lines = []
            while True:
                line = input()
                if line == ".": break
                diff_lines.append(line)
            print("📋 明日计划:")
            plan_lines = []
            while True:
                line = input()
                if line == ".": break
                plan_lines.append(line)
            topics = input("🏷️  涉及知识点 (逗号分隔): ").strip()
        else:
            mood = args.mood
            study_time = args.study_time
            reviewed = args.reviewed
            content_lines = [args.content] if args.content else []
            insight_lines = [args.insights] if args.insights else []
            diff_lines = [args.difficulties] if args.difficulties else []
            plan_lines = [args.plan] if args.plan else []
            topics = args.topics

        fp = write_journal(
            date_str=args.date,
            mood=mood,
            study_time=study_time,
            review_content="\n".join(content_lines),
            insights="\n".join(insight_lines),
            difficulties="\n".join(diff_lines),
            tomorrow_plan="\n".join(plan_lines),
            topics=topics,
            questions_reviewed=reviewed,
        )
        print(f"✅ 日志已保存: {fp}")

    elif args.cmd == "read":
        fp = journal_path(args.date)
        if not fp.exists():
            print(f"❌ {args.date} 没有日志")
            sys.exit(1)
        print(fp.read_text(encoding='utf-8'))

    elif args.cmd == "list":
        journals = list_journals()[:args.limit]
        if not journals:
            print("📭 暂无日志")
            return
        print(f"\n📋 最近 {len(journals)} 篇日志:\n")
        for j in journals:
            mood_emoji = {"great": "😄", "good": "🙂", "neutral": "😐", "tired": "😴", "bad": "😞"}
            print(f"  {mood_emoji.get(j.get('mood',''),'')} {j.get('date','')}  "
                  f"复习 {j.get('questions_reviewed','0')} 题  "
                  f"学习 {j.get('study_time','?')}")

    elif args.cmd == "summary":
        s = generate_summary()
        if "error" in s:
            print(f"❌ {s['error']}")
            return
        print(f"\n📊 学习总结:")
        print(f"{'='*45}")
        print(f"  📅 总学习天数: {s['total_days']} 天")
        print(f"  📝 总复习题数: {s['total_questions_reviewed']} 题")
        print(f"  📈 日均复习: {s['avg_per_day']} 题")
        print(f"  📅 首次记录: {s['first_entry']}")
        print(f"  📅 最近记录: {s['last_entry']}")
        print(f"  😊 心情分布: {s['mood_distribution']}")

    elif args.cmd == "streak":
        s = calc_streak()
        print(f"\n🔥 连续学习: {s['streak']} 天")
        print(f"📝 总日志数: {s['total_entries']} 篇")
        print(f"📅 本月记录: {s['this_month']} 天")
        if s['dates']:
            print(f"\n📅 记录日期:")
            for d in s['dates'][:14]:
                print(f"  {d}")


if __name__ == "__main__":
    main()
