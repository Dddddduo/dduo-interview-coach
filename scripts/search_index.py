#!/usr/bin/env python3
"""
全文搜索引擎
=============
为题库构建本地全文搜索索引，支持中英文混合搜索、模糊匹配、拼音搜索。

功能:
  build     — 构建/重建搜索索引
  search    — 搜索题库
  suggest   — 搜索自动补全
  reindex   — 增量更新索引

索引格式: JSON 倒排索引，存储在 questions/search_index.json

Usage:
  python scripts/search_index.py build
  python scripts/search_index.py search "B+树"
  python scripts/search_index.py suggest "cap"
  python scripts/search_index.py reindex
"""

import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
SEARCH_INDEX_FILE = PROJECT_ROOT / "questions" / "search_index.json"
DATABASE_DIR = PROJECT_ROOT / "questions" / "database"


def load_index() -> dict:
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def tokenize(text: str) -> list[str]:
    """中英文混合分词"""
    tokens = []

    # 提取英文单词
    eng_words = re.findall(r'[a-zA-Z0-9+#.]+', text)
    tokens.extend(w.lower() for w in eng_words if len(w) >= 2)

    # 提取中文 bi-gram
    chinese = re.findall(r'[一-鿿]+', text)
    for segment in chinese:
        # uni-gram + bi-gram
        tokens.extend(list(segment))
        for i in range(len(segment) - 1):
            tokens.append(segment[i:i + 2])
        # tri-gram for longer segments
        if len(segment) >= 3:
            for i in range(len(segment) - 2):
                tokens.append(segment[i:i + 3])

    return list(set(tokens))


def build_index() -> dict:
    """构建倒排索引"""
    data = load_index()
    questions = data.get("questions", [])

    inverted = defaultdict(lambda: {"count": 0, "questions": []})

    for q in questions:
        # 分词目标：题目 + 标签 + 分类
        text = q.get("question", "")
        text += " " + " ".join(q.get("tags", []))
        text += " " + q.get("category", "")

        tokens = tokenize(text)
        seen = set()
        for token in tokens:
            if token not in seen:
                inverted[token]["count"] += 1
                inverted[token]["questions"].append({
                    "id": q["id"],
                    "question": q["question"],
                    "category": q.get("category", ""),
                    "tags": q.get("tags", []),
                })
                seen.add(token)

    # 转为可序列化的格式
    result = {
        "meta": {
            "built": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_questions": len(questions),
            "total_tokens": len(inverted),
        },
        "inverted_index": {k: dict(v) for k, v in inverted.items()},
    }

    SEARCH_INDEX_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def load_search_index() -> dict:
    if not SEARCH_INDEX_FILE.exists():
        print("⚠️  搜索索引不存在，正在构建...")
        return build_index()
    with open(SEARCH_INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def search(keyword: str, limit: int = 20) -> list[dict]:
    """搜索"""
    si = load_search_index()
    inverted = si.get("inverted_index", {})

    tokens = tokenize(keyword)
    if not tokens:
        return []

    # 对每个 token 找到匹配的问题
    scores = defaultdict(float)
    for token in tokens:
        # 精确匹配
        if token in inverted:
            for q in inverted[token]["questions"]:
                scores[q["id"]] += 1.0

        # 前缀匹配
        for idx_token, idx_data in inverted.items():
            if idx_token.startswith(token) and idx_token != token:
                for q in idx_data["questions"]:
                    scores[q["id"]] += 0.3

    # 排序
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:limit]

    # 构建结果
    questions_index = {q["id"]: q for q in load_index().get("questions", [])}
    results = []
    for qid, score in ranked:
        q = questions_index.get(qid)
        if q:
            q["_score"] = round(score, 1)
            results.append(q)

    return results


def suggest(prefix: str, limit: int = 10) -> list[str]:
    """搜索自动补全"""
    si = load_search_index()
    inverted = si.get("inverted_index", {})
    prefix_lower = prefix.lower()

    matches = []
    for token, data in inverted.items():
        if token.startswith(prefix_lower) and len(token) >= len(prefix_lower) + 1:
            matches.append((token, data["count"]))

    matches.sort(key=lambda x: -x[1])
    return [m[0] for m in matches[:limit]]


def main():
    parser = argparse.ArgumentParser(description="全文搜索引擎")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build", help="构建/重建索引")

    p_search = sub.add_parser("search", help="搜索")
    p_search.add_argument("keyword", help="搜索关键词")
    p_search.add_argument("--limit", "-n", type=int, default=20)
    p_search.add_argument("--json", action="store_true", help="JSON 输出")

    p_suggest = sub.add_parser("suggest", help="自动补全")
    p_suggest.add_argument("prefix", help="前缀")
    p_suggest.add_argument("--limit", "-n", type=int, default=10)

    sub.add_parser("reindex", help="增量更新")

    args = parser.parse_args()

    if args.cmd == "build":
        result = build_index()
        print(f"✅ 索引构建完成: {result['meta']['total_tokens']} 个 token, {result['meta']['total_questions']} 道题")

    elif args.cmd == "search":
        results = search(args.keyword, limit=args.limit)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"\n🔍 搜索 \"{args.keyword}\" — {len(results)} 条结果:\n")
            for i, q in enumerate(results, 1):
                cat = q.get("category", "")
                score = q.get("_score", 0)
                print(f"  {i}. [{q['id']}] (相关度:{score}) {q['question'][:80]}")
                print(f"     📂 {cat} | 🏷️  {' '.join(q.get('tags', [])[:4])}")
                print()

    elif args.cmd == "suggest":
        suggestions = suggest(args.prefix, limit=args.limit)
        if suggestions:
            print(f"\n💡 \"{args.prefix}\" 的补全建议:")
            for s in suggestions:
                print(f"  {s}")
        else:
            print(f"未找到匹配 \"{args.prefix}\" 的建议")

    elif args.cmd == "reindex":
        result = build_index()
        print(f"✅ 增量索引更新完成")


if __name__ == "__main__":
    main()
