#!/usr/bin/env python3
"""
站点数据生成器
===============
生成 GitHub Pages 所需的静态数据文件：
  docs/index.json — 题库数据（从 questions/index.json 复制或精简）
  docs/questions.js — 已手动维护，此脚本可验证 JSON 合法性

Usage:
  python scripts/generate_site.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_SRC = PROJECT_ROOT / "questions" / "index.json"
INDEX_DST = PROJECT_ROOT / "docs" / "index.json"


def main():
    # 读取源
    if not INDEX_SRC.exists():
        print(f"❌ 源文件不存在: {INDEX_SRC}")
        print("   先运行 interview_agent.py 或 question_manager.py add 生成题库")
        sys.exit(1)

    with open(INDEX_SRC, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 验证
    questions = data.get("questions", [])
    print(f"📊 题库状态:")
    print(f"   总题数: {len(questions)}")

    categories = data.get("categories", {})
    for cat_key, cat_info in categories.items():
        count = sum(1 for q in questions if q.get("category") == cat_key)
        if count > 0:
            print(f"   {cat_info.get('icon','')} {cat_info.get('name', cat_key)}: {count} 题")

    # 写入 docs/
    INDEX_DST.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_DST, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 站点数据已生成: {INDEX_DST}")
    print(f"🌐 GitHub Pages 题库浏览器可正常使用")


if __name__ == "__main__":
    main()
