#!/usr/bin/env python3
"""
复习调度器
===========
基于间隔重复（Spaced Repetition）算法的智能复习计划生成器。

算法: SM-2 (SuperMemo 2) 简化版
  - 难度等级 0-5
  - 间隔: 1天, 3天, 7天, 14天, 30天, 60天, 120天
  - 每次复习后根据评分调整间隔

功能:
  plan      — 生成今日复习计划
  schedule  — 生成未来 N 天复习计划
  next      — 显示下一道待复习题目
  stats     — 复习统计

Usage:
  python scripts/review_scheduler.py plan
  python scripts/review_scheduler.py schedule --days 7
  python scripts/review_scheduler.py next
"""

import sys, json, argparse, random
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
SCHEDULE_FILE = PROJECT_ROOT / "questions" / "review_schedule.json"

# SM-2 间隔表 (based on ease factor)
INTERVALS = [1, 3, 7, 14, 30, 60, 120, 240]
EASE_FACTORS = {0: 1.3, 1: 1.5, 2: 1.8, 3: 2.0, 4: 2.2, 5: 2.5}


def load_index():
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"cards": {}, "history": []}


def save_schedule(schedule):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)


def init_cards(index: dict) -> dict:
    """初始化所有卡片"""
    schedule = load_schedule()
    questions = index.get("questions", [])

    for q in questions:
        qid = q["id"]
        if qid not in schedule["cards"]:
            schedule["cards"][qid] = {
                "id": qid,
                "question": q["question"][:80],
                "repetitions": 0,
                "ease_factor": 2.5,
                "interval": 1,
                "next_review": datetime.now().strftime("%Y-%m-%d"),
                "last_review": None,
                "category": q.get("category", ""),
                "difficulty": q.get("difficulty", "medium"),
            }

    save_schedule(schedule)
    return schedule


def get_due_cards(schedule: dict, date_str: str) -> list[dict]:
    """获取到期卡片"""
    due = []
    for qid, card in schedule.get("cards", {}).items():
        if card.get("next_review", "") <= date_str:
            due.append(card)
    # 按紧急程度排序（最过期的优先）
    due.sort(key=lambda c: c.get("next_review", "9999"))
    return due


def plan_today(index: dict):
    """生成今日计划"""
    schedule = init_cards(index)
    today = datetime.now().strftime("%Y-%m-%d")
    due = get_due_cards(schedule, today)

    print(f"\n📅 今日复习计划 ({today})")
    print(f"{'='*55}")
    print(f"📋 到期题目: {len(due)} 题")

    if due:
        print(f"\n⏰ 待复习:\n")
        for i, card in enumerate(due[:20], 1):
            days_ago = (datetime.now() - datetime.strptime(card.get("next_review", today), "%Y-%m-%d")).days
            overdue = f" (超期 {days_ago} 天)" if days_ago > 0 else " (今天)"
            print(f"  {i:2d}. [{card['id']}] {card['question'][:60]}")
            print(f"      复习 {card['repetitions']} 次 | 间隔 {card['interval']} 天 | {overdue}")

        if len(due) > 20:
            print(f"  ... 还有 {len(due) - 20} 题")

    else:
        print("  🎉 今天没有到期题目！")
        new_cards = [c for c in schedule["cards"].values() if c["repetitions"] == 0]
        if new_cards:
            print(f"  💡 还有 {len(new_cards)} 道新题等待首次复习")


def schedule_days(index: dict, days: int):
    """未来 N 天计划"""
    schedule = init_cards(index)
    today = datetime.now()

    print(f"\n📅 未来 {days} 天复习计划\n{'='*55}")

    for i in range(days):
        d = today + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        due = get_due_cards(schedule, ds)
        new_count = len([c for c in schedule["cards"].values() if c["repetitions"] == 0])
        print(f"  {ds} ({'周' + '一二三四五六日'[d.weekday()]}) : {len(due)} 题到期"
              + (f" | {new_count} 新题可选" if new_count > 0 else ""))


def next_card(index: dict):
    """显示下一道待复习"""
    schedule = init_cards(index)
    today = datetime.now().strftime("%Y-%m-%d")
    due = get_due_cards(schedule, today)

    if due:
        card = random.choice(due[:min(5, len(due))])
        print(f"\n💡 下一道复习:")
        print(f"  [{card['id']}] {card['question']}")
        print(f"  已复习 {card['repetitions']} 次 | 间隔 {card['interval']} 天")
        print(f"  分类: {card.get('category','')} | 难度: {card.get('difficulty','')}")
    else:
        print("🎉 没有到期题目！")


def main():
    parser = argparse.ArgumentParser(description="复习调度器 (SM-2)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("plan", help="今日计划")
    p_sched = sub.add_parser("schedule", help="未来计划")
    p_sched.add_argument("--days", "-d", type=int, default=7)
    sub.add_parser("next", help="下一道题")
    p_rate = sub.add_parser("rate", help="评价复习")
    p_rate.add_argument("qid", help="题号")
    p_rate.add_argument("score", type=int, choices=range(0, 6), help="评分 0-5")
    sub.add_parser("stats", help="复习统计")
    sub.add_parser("reset", help="重置所有进度")

    args = parser.parse_args()
    index = load_index()

    if not args.cmd:
        plan_today(index)
    elif args.cmd == "plan":
        plan_today(index)
    elif args.cmd == "schedule":
        schedule_days(index, args.days)
    elif args.cmd == "next":
        next_card(index)
    elif args.cmd == "rate":
        schedule = init_cards(index)
        card = schedule["cards"].get(args.qid)
        if not card:
            print(f"❌ 未找到题目: {args.qid}")
            return
        card["repetitions"] += 1
        ef = EASE_FACTORS.get(args.score, 2.5)
        card["ease_factor"] = max(1.3, card["ease_factor"] + (0.1 - (5 - args.score) * (0.08 + (5 - args.score) * 0.02)))
        if card["repetitions"] == 1:
            card["interval"] = 1
        elif card["repetitions"] == 2:
            card["interval"] = 6
        else:
            card["interval"] = round(card["interval"] * card["ease_factor"])
        card["next_review"] = (datetime.now() + timedelta(days=card["interval"])).strftime("%Y-%m-%d")
        card["last_review"] = datetime.now().strftime("%Y-%m-%d")
        schedule["history"].append({"qid": args.qid, "score": args.score, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_schedule(schedule)
        print(f"✅ [{args.qid}] 已评价: {args.score}/5 | 下次复习: {card['next_review']} ({card['interval']} 天后)")
    elif args.cmd == "stats":
        schedule = init_cards(index)
        cards = schedule["cards"].values()
        total = len(cards)
        reviewed = sum(1 for c in cards if c["repetitions"] > 0)
        due_today = len(get_due_cards(schedule, datetime.now().strftime("%Y-%m-%d")))
        print(f"\n📊 复习统计\n{'='*40}")
        print(f"  总题数: {total}")
        print(f"  已复习: {reviewed} ({round(reviewed/max(total,1)*100)}%)")
        print(f"  今日到期: {due_today}")
        print(f"  历史记录: {len(schedule.get('history',[]))} 条")
    elif args.cmd == "reset":
        if input("确认重置所有复习进度? [y/N]: ").strip().lower() == 'y':
            SCHEDULE_FILE.unlink(missing_ok=True)
            print("✅ 已重置")


if __name__ == "__main__":
    main()
