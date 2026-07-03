#!/usr/bin/env python3
"""
题库 API 服务器 (简易版)
==========================
提供题库数据的 RESTful JSON API，供第三方工具或前端调用。

端点:
  GET  /api/questions            — 所有题目
  GET  /api/questions?cat=java   — 按分类筛选
  GET  /api/questions?search=B+  — 搜索
  GET  /api/questions/q0001      — 单道题
  GET  /api/stats                — 统计
  GET  /api/categories           — 分类列表
  GET  /api/tags                 — 标签列表
  GET  /api/search?q=CAP         — 全文搜索
  GET  /api/graph                — 知识图谱数据
  GET  /api/review/today         — 今日复习状态
  POST /api/review/toggle        — 切换复习状态

启动:
  python scripts/api_server.py
  python scripts/api_server.py --port 8080 --host 0.0.0.0

依赖: 标准库 (http.server)，无需额外安装
"""

import sys, json, argparse, re
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
DATABASE_DIR = PROJECT_ROOT / "questions" / "database"

# 全局缓存（首次加载后缓存）
_cache = {"index": None, "questions_by_id": {}, "loaded_at": None}


def load_index():
    """加载题库索引（带缓存）"""
    now = datetime.now()
    if _cache["loaded_at"] and (now - _cache["loaded_at"]).seconds < 30:
        return _cache["index"]

    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            _cache["index"] = json.load(f)
    else:
        _cache["index"] = {"questions": [], "categories": {}, "meta": {}}

    _cache["questions_by_id"] = {q["id"]: q for q in _cache["index"].get("questions", [])}
    _cache["loaded_at"] = now
    return _cache["index"]


def load_answer(qid: str) -> str:
    """加载题目答案"""
    q = _cache["questions_by_id"].get(qid)
    if not q:
        return ""
    filepath = PROJECT_ROOT / q.get("file", "")
    if filepath.exists():
        content = filepath.read_text(encoding='utf-8')
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                content = content[end + 3:].strip()
        return content
    return ""


class APIHandler(BaseHTTPRequestHandler):
    """API 请求处理器"""

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

    def _send_error(self, msg, status=404):
        self._send_json({"error": msg, "status": status}, status)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        params = parse_qs(parsed.query)

        # ---- /api/questions ----
        if path == "/api/questions" or path == "/api/questions/":
            index = load_index()
            questions = index.get("questions", [])

            # 筛选
            cat = params.get("cat", [None])[0]
            diff = params.get("difficulty", [None])[0]
            tag = params.get("tag", [None])[0]
            search = params.get("search", [None])[0]
            sort = params.get("sort", ["newest"])[0]
            limit = int(params.get("limit", [0])[0] or 0)

            if cat:
                questions = [q for q in questions if q.get("category") == cat]
            if diff:
                questions = [q for q in questions if q.get("difficulty") == diff]
            if tag:
                questions = [q for q in questions if tag in q.get("tags", [])]
            if search:
                kw = search.lower()
                questions = [q for q in questions if
                             kw in q.get("question", "").lower() or
                             any(kw in t.lower() for t in q.get("tags", []))]

            if sort == "oldest":
                questions.sort(key=lambda q: q.get("created", ""))
            elif sort == "difficulty":
                order = {"easy": 0, "medium": 1, "hard": 2}
                questions.sort(key=lambda q: order.get(q.get("difficulty"), 1))
            else:
                questions.sort(key=lambda q: q.get("created", ""), reverse=True)

            if limit > 0:
                questions = questions[:limit]

            self._send_json({
                "total": len(questions),
                "questions": questions,
                "params": {"cat": cat, "difficulty": diff, "tag": tag, "search": search, "sort": sort},
            })

        # ---- /api/questions/{qid} ----
        elif path.startswith("/api/questions/"):
            qid = path.split("/")[-1]
            q = _cache["questions_by_id"].get(qid)
            if not q:
                self._send_error(f"Question not found: {qid}")
                return
            answer = load_answer(qid)
            self._send_json({**q, "answer": answer})

        # ---- /api/stats ----
        elif path == "/api/stats":
            index = load_index()
            questions = index.get("questions", [])
            categories = index.get("categories", {})

            cat_stats = {}
            diff_stats = {"easy": 0, "medium": 0, "hard": 0}
            tag_stats = {}

            for q in questions:
                cat = q.get("category", "unknown")
                cat_stats[cat] = cat_stats.get(cat, 0) + 1
                diff_stats[q.get("difficulty", "medium")] += 1
                for t in q.get("tags", []):
                    tag_stats[t] = tag_stats.get(t, 0) + 1

            self._send_json({
                "total": len(questions),
                "categories_count": len([c for c in cat_stats.values() if c > 0]),
                "total_categories": len(categories),
                "by_category": cat_stats,
                "by_difficulty": diff_stats,
                "top_tags": sorted(tag_stats.items(), key=lambda x: -x[1])[:20],
                "last_updated": index.get("meta", {}).get("last_updated", ""),
            })

        # ---- /api/categories ----
        elif path == "/api/categories":
            index = load_index()
            categories = index.get("categories", {})
            questions = index.get("questions", [])
            result = {}
            for key, cat in categories.items():
                count = sum(1 for q in questions if q.get("category") == key)
                result[key] = {**cat, "count": count}
            self._send_json(result)

        # ---- /api/tags ----
        elif path == "/api/tags":
            index = load_index()
            questions = index.get("questions", [])
            tag_stats = {}
            for q in questions:
                for t in q.get("tags", []):
                    tag_stats[t] = tag_stats.get(t, 0) + 1
            self._send_json({
                "total": len(tag_stats),
                "tags": [{"tag": k, "count": v} for k, v in sorted(tag_stats.items(), key=lambda x: -x[1])],
            })

        # ---- /api/search ----
        elif path == "/api/search":
            q_param = params.get("q", [""])[0]
            if not q_param:
                self._send_json({"results": [], "query": ""})
                return

            index = load_index()
            questions = index.get("questions", [])
            kw = q_param.lower()
            results = []

            for q in questions:
                score = 0
                if kw in q.get("question", "").lower():
                    score += 3
                if any(kw in t.lower() for t in q.get("tags", [])):
                    score += 2
                if kw in q.get("category", "").lower():
                    score += 1
                if score > 0:
                    results.append({**q, "_score": score})

            results.sort(key=lambda r: -r["_score"])
            self._send_json({"results": results[:20], "query": q_param, "total": len(results)})

        # ---- /api/graph ----
        elif path == "/api/graph":
            index = load_index()
            questions = index.get("questions", [])

            nodes = {}
            edges = {}

            for q in questions:
                tags = q.get("tags", [])
                for tag in tags:
                    if tag not in nodes:
                        nodes[tag] = {"id": tag, "name": tag, "count": 0, "category": q.get("category")}
                    nodes[tag]["count"] += 1

                for i in range(len(tags)):
                    for j in range(i + 1, len(tags)):
                        key = tuple(sorted([tags[i], tags[j]]))
                        if key not in edges:
                            edges[key] = {"source": key[0], "target": key[1], "weight": 0}
                        edges[key]["weight"] += 1

            self._send_json({
                "nodes": list(nodes.values()),
                "edges": list(edges.values()),
                "meta": {"node_count": len(nodes), "edge_count": len(edges)},
            })

        # ---- /api/review/today ----
        elif path == "/api/review/today":
            today = datetime.now().strftime("%Y-%m-%d")
            self._send_json({
                "date": today,
                "reviewed": [],  # 客户端管理，服务端不存储
                "note": "Review data is managed client-side via localStorage",
            })

        # ---- /api/health ----
        elif path == "/api/health" or path == "/api":
            index = load_index()
            self._send_json({
                "status": "ok",
                "service": "Interview Coach API",
                "version": "2.0",
                "questions": len(index.get("questions", [])),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        else:
            self._send_error("Not Found", 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # ---- POST /api/review/toggle ----
        if path == "/api/review/toggle":
            qid = data.get("qid", "")
            date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            if not qid:
                self._send_error("Missing qid", 400)
                return
            # 客户端管理，服务端返回确认
            self._send_json({
                "status": "ok",
                "qid": qid,
                "date": date,
                "action": "toggle",
                "note": "Client should update localStorage",
            })

        else:
            self._send_error("Not Found", 404)

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="题库 API 服务器")
    parser.add_argument("--port", "-p", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    # 预加载
    print("📚 加载题库...")
    load_index()
    print(f"   {len(_cache['index'].get('questions', []))} 题已加载")

    server = HTTPServer((args.host, args.port), APIHandler)
    print(f"\n🚀 API 服务器已启动: http://{args.host}:{args.port}")
    print(f"   📋 http://{args.host}:{args.port}/api/questions")
    print(f"   📊 http://{args.host}:{args.port}/api/stats")
    print(f"   🔍 http://{args.host}:{args.port}/api/search?q=CAP")
    print(f"   🧠 http://{args.host}:{args.port}/api/graph")
    print(f"\n按 Ctrl+C 停止\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
