#!/usr/bin/env python3
"""
记忆训练器 — 交互式面试知识点记忆测验
===========================================
从已生成的面试解答文档中提取"联想记忆法"，通过交互式问答帮你巩固记忆。

模式：
  1. 闪卡模式 (flashcard)：看到题目 → 回忆记忆法 → 按回车看答案
  2. 填空模式 (cloze)：看到记忆口诀（部分挖空）→ 补全缺失部分
  3. 随机挑战 (random)：随机抽题，答对加分

Usage:
  python memory_trainer.py outputs/面经解答-20260704.md    # 从文档加载
  python memory_trainer.py --mode cloze outputs/*.md        # 填空模式
  python memory_trainer.py --mode random --rounds 10 outputs/*.md
"""

import sys
import re
import random
import argparse
import textwrap
from pathlib import Path
from typing import NamedTuple


class Card(NamedTuple):
    question: str
    memory_aid: str      # 联想记忆法全文
    mnemonic: str         # 记忆口诀（提取的第一句）
    principle: str        # 记忆原理


def extract_cards_from_md(filepath: Path) -> list[Card]:
    """从生成的 Markdown 文档中提取记忆卡片"""
    text = filepath.read_text(encoding='utf-8')
    cards = []

    # 匹配每道题
    sections = re.split(r'\n## 第\d+题[：:]', text)
    for section in sections[1:]:  # 跳过目录部分
        # 提取题目文本（第一行）
        lines = section.strip().split('\n')
        question = lines[0].strip() if lines else "未知题目"

        # 提取联想记忆法部分
        memory_match = re.search(
            r'###?\s*🧠\s*联想记忆法(.*?)(?=###?\s*[📖🗺️])',
            section, re.DOTALL
        )
        if not memory_match:
            continue

        memory_section = memory_match.group(1).strip()

        # 提取记忆口诀
        mnemonic_match = re.search(
            r'(?:记忆口诀|联想|口诀)[：:]\s*(.+?)(?:\n|$)',
            memory_section
        )
        mnemonic = mnemonic_match.group(1).strip() if mnemonic_match else ""

        # 提取记忆原理
        principle_match = re.search(
            r'(?:记忆原理|原理)[：:]\s*(.+?)(?:\n|$)',
            memory_section
        )
        principle = principle_match.group(1).strip() if principle_match else ""

        cards.append(Card(
            question=question,
            memory_aid=memory_section,
            mnemonic=mnemonic if mnemonic else memory_section[:120],
            principle=principle,
        ))

    return cards


def color(text: str, code: str) -> str:
    """终端颜色"""
    colors = {
        "green": "\033[92m", "yellow": "\033[93m",
        "cyan": "\033[96m", "red": "\033[91m",
        "bold": "\033[1m", "reset": "\033[0m",
    }
    return f"{colors.get(code, '')}{text}{colors['reset']}"


def flashcard_mode(cards: list[Card]):
    """闪卡模式"""
    print(color("\n📇 闪卡模式", "bold"))
    print("看到题目 → 尝试回忆记忆法 → 按回车查看答案 → 自我评分\n")

    random.shuffle(cards)
    scores = []

    for i, card in enumerate(cards, 1):
        print(f"\n{'─'*50}")
        print(color(f"卡片 {i}/{len(cards)}", "cyan"))
        print(color(f"📝 题目: {card.question}", "bold"))
        input(color("\n💭 先在脑海中回忆记忆法，然后按回车...", "yellow"))

        print(color("\n✨ 记忆口诀:", "green"))
        print(f"  {card.mnemonic}")
        if card.principle:
            print(color(f"\n💡 记忆原理: {card.principle}", "yellow"))
        print(color(f"\n📖 完整记忆法:", "cyan"))
        print(textwrap.indent(card.memory_aid[:300], "  "))

        rating = input(color("\n🌟 评分 (3=完全记住 2=大概记得 1=只记得一点 0=完全忘了): ", "bold"))
        try:
            scores.append(int(rating))
        except ValueError:
            scores.append(0)

    if scores:
        avg = sum(scores) / len(scores)
        print(f"\n{'='*50}")
        print(color(f"📊 本轮平均分: {avg:.1f}/3", "bold"))
        print(f"   ⭐⭐⭐ {scores.count(3)} 张 | ⭐⭐ {scores.count(2)} 张 | ⭐ {scores.count(1)} 张 | 需复习 {scores.count(0)} 张")


def cloze_mode(cards: list[Card]):
    """填空模式"""
    print(color("\n📝 填空模式", "bold"))
    print("记忆口诀会被挖掉关键词，你需要补全\n")

    random.shuffle(cards)
    score = 0
    total = 0

    for i, card in enumerate(cards, 1):
        if not card.mnemonic or len(card.mnemonic) < 10:
            continue

        total += 1
        # 随机挖掉一个词（选最长的词或加引号的词）
        words = re.findall(r'[一-鿿\w]+', card.mnemonic)
        if len(words) < 4:
            continue

        target = random.choice([w for w in words if len(w) >= 2])
        cloze = card.mnemonic.replace(target, "____", 1)

        print(f"\n{'─'*50}")
        print(color(f"填空 {i}/{len(cards)}", "cyan"))
        print(color(f"题目: {card.question}", "bold"))
        print(f"\n  {cloze}")

        answer = input(color("\n✏️  填入缺失的词: ", "yellow")).strip()

        if answer.lower() == target.lower() or answer in target or target in answer:
            print(color("  ✅ 正确！", "green"))
            score += 1
        else:
            print(color(f"  ❌ 正确答案是: {target}", "red"))

    print(f"\n{'='*50}")
    print(color(f"📊 得分: {score}/{total}", "bold"))


def random_mode(cards: list[Card], rounds: int = 10):
    """随机挑战模式"""
    print(color(f"\n🎲 随机挑战模式 ({rounds} 轮)", "bold"))
    print("答对加分，答错不扣分。每题有 2 次机会\n")

    score = 0
    used = set()

    for r in range(1, rounds + 1):
        available = [c for i, c in enumerate(cards) if i not in used]
        if not available:
            used.clear()
            available = cards

        card = random.choice(available)
        used.add(cards.index(card))

        print(f"\n{'─'*50}")
        print(color(f"第 {r}/{rounds} 轮 | 当前得分: {score}", "cyan"))
        print(color(f"📝 {card.question}", "bold"))

        # 第一试
        guess = input(color("\n💭 你能回忆起这道题的联想记忆法吗？（简述即可）\n> ", "yellow")).strip()

        if len(guess) >= 3 and any(
            word in card.memory_aid for word in guess.split() if len(word) >= 2
        ):
            print(color("  ✅ 太棒了！+3分", "green"))
            score += 3
            print(color(f"  完整记忆法: {card.mnemonic}", "cyan"))
        else:
            # 给提示，第二试
            hint = card.mnemonic[:20] + "..." if len(card.mnemonic) > 20 else card.mnemonic[:10]
            print(color(f"  💡 提示: {hint}", "yellow"))
            guess2 = input(color("  再试一次 > ", "yellow")).strip()

            if len(guess2) >= 3 and any(
                word in card.memory_aid for word in guess2.split() if len(word) >= 2
            ):
                print(color("  ✅ 正确！+1分", "green"))
                score += 1
            else:
                print(color(f"  ❌ 正确答案: {card.mnemonic}", "red"))

        if card.principle:
            print(color(f"  💡 记忆原理: {card.principle}", "yellow"))

    print(f"\n{'='*50}")
    print(color(f"🏆 最终得分: {score}/{rounds * 3}", "bold"))
    if score >= rounds * 2:
        print(color("  🎉 非常出色！记忆掌握得很好！", "green"))
    elif score >= rounds:
        print(color("  👍 不错！再多练习几次就很扎实了", "yellow"))
    else:
        print(color("  📚 需要加强复习，建议每天练一轮", "red"))


def main():
    parser = argparse.ArgumentParser(
        description="记忆训练器 — 交互式面试知识点测验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files", nargs="+", help="面试解答 Markdown 文件路径"
    )
    parser.add_argument(
        "--mode", choices=["flashcard", "cloze", "random"],
        default="flashcard", help="训练模式 (默认: flashcard)"
    )
    parser.add_argument(
        "--rounds", type=int, default=10,
        help="随机模式的轮数 (默认: 10)"
    )

    args = parser.parse_args()

    # 加载所有卡片
    all_cards = []
    for fp in args.files:
        path = Path(fp)
        if not path.exists():
            print(f"⚠️  跳过不存在的文件: {fp}")
            continue
        cards = extract_cards_from_md(path)
        all_cards.extend(cards)
        print(f"📄 从 {path.name} 加载 {len(cards)} 张卡片")

    if not all_cards:
        print("❌ 没有找到任何记忆卡片。请先运行 interview_agent.py 生成答题文档。")
        sys.exit(1)

    print(f"\n📚 共加载 {len(all_cards)} 张记忆卡片")

    if args.mode == "flashcard":
        flashcard_mode(all_cards)
    elif args.mode == "cloze":
        cloze_mode(all_cards)
    elif args.mode == "random":
        random_mode(all_cards, args.rounds)


if __name__ == "__main__":
    main()
