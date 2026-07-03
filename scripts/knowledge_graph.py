#!/usr/bin/env python3
"""
知识图谱生成器
===============
从题库中提取知识点、构建关联关系、生成可视化数据。

功能:
  analyze   — 分析题库，提取知识点及其关联
  graph     — 生成知识图谱 JSON（可直接用于 D3.js/ECharts）
  map       — 生成知识点→题目映射表
  suggest   — 根据当前进度推荐下一步学习的知识点

Usage:
  python scripts/knowledge_graph.py analyze
  python scripts/knowledge_graph.py graph --output docs/graph.json
  python scripts/knowledge_graph.py map
  python scripts/knowledge_graph.py suggest --reviewed 5 --goal java
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"


def load_index() -> dict:
    if not INDEX_FILE.exists():
        print("❌ 题库为空，先运行 /面经助手 添加题目")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_knowledge_nodes(index: dict) -> list[dict]:
    """从题库提取知识点节点"""
    nodes = {}
    tags = defaultdict(list)

    for q in index.get("questions", []):
        for tag in q.get("tags", []):
            tags[tag].append(q["id"])

    for tag, qids in tags.items():
        nodes[tag] = {
            "id": tag,
            "name": tag,
            "count": len(qids),
            "questions": qids,
            "categories": list(set(
                q["category"] for q in index["questions"] if q["id"] in qids
            )),
        }

    return list(nodes.values())


def extract_edges(nodes: list[dict], index: dict) -> list[dict]:
    """提取知识点之间的关联边"""
    edges = []
    node_ids = {n["id"] for n in nodes}
    questions = index.get("questions", [])

    # 同一道题中的标签互相连接
    for q in questions:
        qt = q.get("tags", [])
        for i in range(len(qt)):
            for j in range(i + 1, len(qt)):
                if qt[i] in node_ids and qt[j] in node_ids:
                    edges.append({
                        "source": qt[i],
                        "target": qt[j],
                        "weight": 1,
                        "question": q["id"],
                    })

    # 合并重复边（加权重）
    merged = {}
    for e in edges:
        key = tuple(sorted([e["source"], e["target"]]))
        if key not in merged:
            merged[key] = {"source": key[0], "target": key[1], "weight": 0, "questions": []}
        merged[key]["weight"] += 1
        if e["question"] not in merged[key]["questions"]:
            merged[key]["questions"].append(e["question"])

    return list(merged.values())


def build_graph_data(index: dict) -> dict:
    """构建完整知识图谱数据"""
    nodes = extract_knowledge_nodes(index)
    edges = extract_edges(nodes, index)

    # 节点大小映射
    max_count = max((n["count"] for n in nodes), default=1)
    for n in nodes:
        n["size"] = 8 + (n["count"] / max_count) * 32

    # 分类颜色映射
    cat_colors = {
        "java": "#f89820", "mysql": "#4479A1", "redis": "#DC382D",
        "spring": "#6DB33F", "distributed": "#00ADD8", "os": "#0078D7",
        "network": "#E44D26", "python": "#3776AB", "go": "#00ADD8",
        "behavioral": "#A371F7", "system-design": "#F85149",
        "frontend": "#F7DF1E", "devops": "#FC6D26",
    }
    for n in nodes:
        primary_cat = n.get("categories", ["unknown"])[0] if n.get("categories") else "unknown"
        n["color"] = cat_colors.get(primary_cat, "#8b949e")

    return {
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }


def build_topic_map(index: dict) -> dict:
    """生成知识点→题目映射"""
    mapping = defaultdict(list)
    for q in index.get("questions", []):
        for tag in q.get("tags", []):
            mapping[tag].append({
                "id": q["id"],
                "question": q["question"],
                "category": q.get("category", ""),
                "difficulty": q.get("difficulty", "medium"),
            })
    return dict(mapping)


def suggest_next(index: dict, reviewed_ids: list[str], goal_category: str) -> list[dict]:
    """推荐下一步学习的知识点"""
    questions = index.get("questions", [])

    # 已复习标签
    reviewed_tags = set()
    for q in questions:
        if q["id"] in reviewed_ids:
            reviewed_tags.update(q.get("tags", []))

    # 目标分类下的未复习题目
    candidates = [
        q for q in questions
        if q.get("category") == goal_category
        and q["id"] not in reviewed_ids
    ]

    # 按是否有新标签排序
    for c in candidates:
        new_tags = [t for t in c.get("tags", []) if t not in reviewed_tags]
        c["new_tag_count"] = len(new_tags)
        c["new_tags"] = new_tags

    candidates.sort(key=lambda c: (-c["new_tag_count"], c.get("difficulty", "medium")))
    return candidates[:10]


def main():
    parser = argparse.ArgumentParser(description="知识图谱生成器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("analyze", help="分析题库知识点")

    p_graph = sub.add_parser("graph", help="生成知识图谱 JSON")
    p_graph.add_argument("--output", "-o", help="输出文件路径")
    p_graph.add_argument("--min-weight", type=int, default=1, help="最小边权重")

    sub.add_parser("map", help="生成知识点→题目映射表")

    p_suggest = sub.add_parser("suggest", help="推荐下一步学习")
    p_suggest.add_argument("--reviewed", "-r", type=int, default=0, help="已复习题数")
    p_suggest.add_argument("--goal", "-g", default="java", help="目标分类")
    p_suggest.add_argument("--reviewed-ids", nargs="*", help="已复习题号列表")

    args = parser.parse_args()
    index = load_index()

    if args.cmd == "analyze":
        nodes = extract_knowledge_nodes(index)
        edges = extract_edges(nodes, index)
        print(f"\n📊 知识点分析:")
        print(f"   知识点节点: {len(nodes)}")
        print(f"   关联关系: {len(edges)}")
        print(f"\n🏷️  知识点列表 (按题目数排序):")
        nodes.sort(key=lambda n: -n["count"])
        for n in nodes[:30]:
            bar = "█" * min(n["count"], 20)
            cats = ", ".join(n.get("categories", [])[:2])
            print(f"  {n['name']:16s} {n['count']:3d}题 {bar} [{cats}]")

        # 核心知识点（度最高的）
        if edges:
            degree = defaultdict(int)
            for e in edges:
                degree[e["source"]] += e["weight"]
                degree[e["target"]] += e["weight"]
            print(f"\n🔗 核心知识点 (关联最多):")
            for tag, d in sorted(degree.items(), key=lambda x: -x[1])[:10]:
                print(f"  {tag}: 与 {d} 个知识点关联")

    elif args.cmd == "graph":
        data = build_graph_data(index)
        data["edges"] = [e for e in data["edges"] if e["weight"] >= args.min_weight]

        if args.output:
            Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"✅ 知识图谱数据已保存: {args.output}")
            print(f"   节点: {data['meta']['total_nodes']}, 边: {len(data['edges'])}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))

    elif args.cmd == "map":
        mapping = build_topic_map(index)
        print(f"\n📋 知识点→题目映射 ({len(mapping)} 个知识点):\n")
        for tag, qs in sorted(mapping.items(), key=lambda x: -len(x[1])):
            print(f"## {tag} ({len(qs)} 题)")
            for q in qs[:5]:
                print(f"  [{q['id']}] {q['question'][:60]}")
            if len(qs) > 5:
                print(f"  ... 还有 {len(qs)-5} 题")
            print()

    elif args.cmd == "suggest":
        reviewed_ids = args.reviewed_ids or []
        suggestions = suggest_next(index, reviewed_ids, args.goal)

        print(f"\n💡 推荐学习 ({args.goal}):\n")
        for i, s in enumerate(suggestions, 1):
            diff = {"easy": "🟢基础", "medium": "🟡中级", "hard": "🔴进阶"}.get(s.get("difficulty", ""), "")
            print(f"  {i}. [{s['id']}] {s['question'][:70]}")
            print(f"     {diff} | 新知识点: {', '.join(s['new_tags'][:5])}")
            print()


if __name__ == "__main__":
    main()
