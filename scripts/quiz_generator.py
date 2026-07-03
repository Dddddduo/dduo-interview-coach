#!/usr/bin/env python3
"""
测验生成器
===========
从题库自动生成自测验卷，支持多种题型和难度。

功能:
  generate   — 生成一份测验卷
  score      — 给自己打分（交互式）
  history    — 查看测验历史

题型:
  multiple_choice — 选择题（从题库自动生成干扰项）
  recall          — 简答题（看题目→回忆→对答案）
  fill_blank      — 填空题（记忆口诀挖空）

Usage:
  python scripts/quiz_generator.py generate --count 10 --type recall
  python scripts/quiz_generator.py generate --count 5 --type multiple_choice --category java
  python scripts/quiz_generator.py score
  python scripts/quiz_generator.py history
"""

import sys
import json
import random
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
QUIZ_HISTORY = PROJECT_ROOT / "questions" / "quiz_history.json"


def load_index() -> dict:
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_history() -> list[dict]:
    if QUIZ_HISTORY.exists():
        with open(QUIZ_HISTORY, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(entry: dict):
    history = load_history()
    history.append(entry)
    with open(QUIZ_HISTORY, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def generate_mc_options(correct_answer: str, all_answers: list[str], count: int = 3) -> list[str]:
    """生成选择题干扰项（从其他题目答案中选取）"""
    candidates = [a for a in all_answers if a != correct_answer]
    if len(candidates) < count:
        return random.sample(candidates, len(candidates))
    return random.sample(candidates, count)


def generate_quiz(index: dict, count: int = 10,
                  quiz_type: str = "recall",
                  category: Optional[str] = None,
                  difficulty: Optional[str] = None) -> dict:
    """生成一份测验"""
    questions = index.get("questions", [])
    pool = [q for q in questions
            if (not category or q.get("category") == category)
            and (not difficulty or q.get("difficulty") == difficulty)]

    if len(pool) < count:
        count = len(pool)

    selected = random.sample(pool, count)
    quiz_items = []

    for q in selected:
        md_path = PROJECT_ROOT / q.get("file", "")
        full_answer = ""
        if md_path.exists():
            full_answer = md_path.read_text(encoding='utf-8')
            if full_answer.startswith('---'):
                end = full_answer.find('---', 3)
                if end > 0:
                    full_answer = full_answer[end + 3:].strip()

        item = {
            "id": q["id"],
            "question": q["question"],
            "type": quiz_type,
            "category": q.get("category", ""),
            "difficulty": q.get("difficulty", "medium"),
            "answer": full_answer[:600],
            "tags": q.get("tags", []),
        }

        if quiz_type == "multiple_choice":
            # 随机选一题答案作正确选项
            all_answers = []
            for other_q in pool:
                op = PROJECT_ROOT / other_q.get("file", "")
                if op.exists():
                    all_answers.append(op.read_text(encoding='utf-8')[:200])

            correct_summary = full_answer[:200] if full_answer else q["question"]
            distractors = generate_mc_options(correct_summary, all_answers, 3)
            options = [correct_summary] + distractors
            random.shuffle(options)
            item["options"] = [o[:100] for o in options]
            item["correct_index"] = options.index(correct_summary)

        elif quiz_type == "fill_blank":
            # 从联想记忆法中挖空关键词
            import re
            memory_match = re.search(r'(?:记忆口诀|联想)[：:]\s*(.+?)(?:\n|$)', full_answer)
            if memory_match:
                mnemonic = memory_match.group(1).strip()
                words = re.findall(r'[一-鿿\w]+', mnemonic)
                if len(words) >= 3:
                    target = random.choice([w for w in words if len(w) >= 2])
                    item["cloze_text"] = mnemonic.replace(target, "____", 1)
                    item["blank_answer"] = target
                else:
                    item["cloze_text"] = mnemonic[:60] + "..."
                    item["blank_answer"] = words[0] if words else ""
            else:
                item["cloze_text"] = full_answer[:100] + "..."
                item["blank_answer"] = ""

        quiz_items.append(item)

    quiz = {
        "id": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8],
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": quiz_type,
        "total": len(quiz_items),
        "items": quiz_items,
    }

    return quiz


def interactive_score(quiz: dict):
    """交互式打分"""
    print(f"\n📝 开始测验! ({quiz['total']} 题, 类型: {quiz['type']})")
    print(f"{'='*55}\n")

    score = 0
    results = []

    for i, item in enumerate(quiz["items"], 1):
        print(f"第 {i}/{quiz['total']} 题 [{item['id']}] {item['difficulty']}")
        print(f"📝 {item['question'][:100]}")

        if item["type"] == "multiple_choice":
            for j, opt in enumerate(item["options"]):
                print(f"  {chr(65+j)}. {opt[:80]}")
            answer = input("你的答案 (A/B/C/D): ").strip().upper()
            correct = chr(65 + item["correct_index"])
            is_correct = (answer == correct)

        elif item["type"] == "fill_blank":
            print(f"  填空: {item.get('cloze_text', '')[:150]}")
            answer = input("填入缺失的词: ").strip()
            is_correct = (answer.lower() == item.get("blank_answer", "").lower())

        else:  # recall
            input("💭 先在脑海中回忆答案，然后按回车查看...")
            print(f"\n📖 参考答案:\n{item['answer'][:400]}")
            answer = input("\n自评 (y=答对了/n=答错了/s=部分正确): ").strip().lower()
            is_correct = answer == 'y'

        if is_correct:
            print("  ✅ 正确!\n")
            score += 1
        else:
            print(f"  ❌ 正确答案: {item.get('blank_answer', '') if item['type']=='fill_blank' else ''}\n")

        results.append({"id": item["id"], "correct": is_correct})

    pct = round(score / quiz["total"] * 100)
    grade = "🏆" if pct >= 90 else "👍" if pct >= 70 else "📚" if pct >= 50 else "💪"
    print(f"{'='*55}")
    print(f"📊 得分: {score}/{quiz['total']} ({pct}%) {grade}")

    # 保存历史
    save_history({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quiz_id": quiz["id"],
        "score": score,
        "total": quiz["total"],
        "percentage": pct,
        "type": quiz["type"],
        "results": results,
    })


def main():
    parser = argparse.ArgumentParser(description="测验生成器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="生成测验")
    p_gen.add_argument("--count", "-n", type=int, default=10, help="题数")
    p_gen.add_argument("--type", "-t", choices=["recall", "multiple_choice", "fill_blank"],
                       default="recall", help="题型")
    p_gen.add_argument("--category", "-c", help="分类筛选")
    p_gen.add_argument("--difficulty", "-d", choices=["easy", "medium", "hard"])
    p_gen.add_argument("--output", "-o", help="保存测验 JSON")

    p_score = sub.add_parser("score", help="打分")
    p_score.add_argument("quiz_file", help="测验 JSON 文件")

    sub.add_parser("history", help="查看历史")

    args = parser.parse_args()
    index = load_index()

    if args.cmd == "generate":
        quiz = generate_quiz(
            index,
            count=args.count,
            quiz_type=args.type,
            category=getattr(args, 'category', None),
            difficulty=getattr(args, 'difficulty', None),
        )
        if getattr(args, 'output', None):
            Path(args.output).write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"✅ 测验已保存: {args.output}")

        interactive_score(quiz)

    elif args.cmd == "score":
        with open(args.quiz_file, 'r', encoding='utf-8') as f:
            quiz = json.load(f)
        interactive_score(quiz)

    elif args.cmd == "history":
        history = load_history()
        if not history:
            print("📭 暂无测验记录")
            return
        print(f"\n📊 测验历史 ({len(history)} 次):\n")
        total_score = 0
        for h in history:
            print(f"  {h['date']} | {h['type']:16s} | {h['score']}/{h['total']} ({h['percentage']}%)")
            total_score += h['percentage']
        print(f"\n📈 平均得分: {round(total_score/len(history))}%")


if __name__ == "__main__":
    main()
