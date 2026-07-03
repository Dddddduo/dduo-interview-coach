#!/usr/bin/env python3
"""
题库管理器 — 面试题的持久化、分类、索引、检索系统
===================================================
Question Manager — 整个项目的"沉淀引擎"。

功能：
  add       — 添加新题（自动分类、打标签、写入文件、更新索引）
  search    — 全文搜索题库
  stats     — 题库统计（按分类、难度、时间）
  export    — 导出题库为 JSON/Markdown
  tag       — 手动添加/修改标签
  dedup     — 去重检查

Usage:
  python scripts/question_manager.py add --question "..." --answer "..." --category java
  python scripts/question_manager.py search "CAP"
  python scripts/question_manager.py stats
  python scripts/question_manager.py export --format markdown --output all_questions.md
"""

import sys
import json
import argparse
import textwrap
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional


# ============================================================
# 配置
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = PROJECT_ROOT / "questions"
INDEX_FILE = QUESTIONS_DIR / "index.json"
DATABASE_DIR = QUESTIONS_DIR / "database"

# 关键词 → 分类的映射规则（用于自动分类）
CATEGORY_KEYWORDS = {
    "java": [
        "java", "jvm", "jdk", "spring", "maven", "gradle", "mybatis",
        "hibernate", "tomcat", "jetty", "类加载", "垃圾回收", "gc",
        "多线程", "线程池", "synchronized", "lock", "volatile",
        "hashmap", "concurrenthashmap", "arraylist", "string",
        "面向对象", "多态", "继承", "封装", "接口", "抽象类",
    ],
    "python": [
        "python", "django", "flask", "fastapi", "pandas", "numpy",
        "pytorch", "tensorflow", "gil", "装饰器", "生成器", "协程",
        "asyncio", "pip", "列表推导",
    ],
    "go": [
        "go", "golang", "goroutine", "channel", "gin", "beego",
        "gorm", "defer", "interface{}",
    ],
    "mysql": [
        "mysql", "sql", "索引", "b+树", "事务", "acid", "隔离级别",
        "mvcc", "慢查询", "explain", "分库分表", "主从", "数据库",
        "innodb", "myisam", "postgresql", "mongodb", "nosql",
        "连接池", "死锁", "redolog", "undolog", "binlog",
    ],
    "redis": [
        "redis", "缓存", "memcached", "缓存穿透", "缓存击穿",
        "缓存雪崩", "过期策略", "lru", "lfu", "持久化", "rdb",
        "aof", "哨兵", "集群", "分布式锁",
    ],
    "spring": [
        "spring", "ioc", "aop", "di", "springboot", "springcloud",
        "微服务", "bean", "autowired", "事务管理",
    ],
    "distributed": [
        "分布式", "cap", "base", "一致性", "raft", "paxos",
        "zookeeper", "消息队列", "kafka", "rabbitmq", "rocketmq",
        "rpc", "dubbo", "服务发现", "限流", "熔断", "降级",
        "分布式事务", "seata", "雪花算法", "分布式id",
    ],
    "os": [
        "操作系统", "进程", "线程", "死锁", "内存管理", "虚拟内存",
        "页表", "mmu", "文件系统", "inode", "调度", "用户态",
        "内核态", "linux", "信号量", "互斥锁",
    ],
    "network": [
        "网络", "tcp", "udp", "http", "https", "dns", "socket",
        "三次握手", "四次挥手", "osi", "ip", "路由", "cdn",
        "websocket", "rest", "grpc", "ssl", "tls", "拥塞控制",
    ],
    "behavioral": [
        "项目经历", "团队", "冲突", "挑战", "失败", "领导",
        "职业规划", "优缺点", "为什么", "离职", "自我介绍",
        "最大的", "如何解决", "描述一个",
    ],
    "system-design": [
        "系统设计", "架构", "高并发", "高可用", "秒杀", "设计一个",
        "设计模式", "领域驱动", "ddd", "c端", "b端", "千万级",
        "亿级", "扩容", "拆分", "中台",
    ],
    "frontend": [
        "javascript", "typescript", "html", "css", "react",
        "vue", "angular", "webpack", "babel", "浏览器", "dom",
        "事件循环", "promise", "async", "跨域", "cors",
        "前端", "spa", "ssr", "node",
    ],
    "devops": [
        "docker", "kubernetes", "k8s", "ci/cd", "jenkins",
        "gitlab", "ansible", "terraform", "监控", "告警",
        "prometheus", "grafana", "日志", "elk", "发布",
        "灰度", "蓝绿", "devops", "运维",
    ],
}

# 自动标签规则
AUTO_TAG_RULES = [
    (r'(?i)\b(jvm|垃圾回收|gc|类加载|字节码)\b', 'JVM'),
    (r'(?i)\b(线程|并发|同步|锁|synchronized|lock|volatile|cas|aqs)\b', '并发编程'),
    (r'(?i)\b(索引|b\+树|查询优化|慢查询|执行计划)\b', '索引优化'),
    (r'(?i)\b(事务|acid|mvcc|隔离级别)\b', '事务'),
    (r'(?i)\b(分布式|微服务|rpc|消息队列)\b', '分布式'),
    (r'(?i)\b(缓存|redis|穿透|击穿|雪崩)\b', '缓存'),
    (r'(?i)\b(设计模式|单例|工厂|策略|代理)\b', '设计模式'),
    (r'(?i)\b(tcp|http|https|网络|socket)\b', '网络协议'),
    (r'(?i)\b(内存|堆|栈|oom|内存泄漏)\b', '内存管理'),
    (r'(?i)\b(spring|ioc|aop|bean)\b', 'Spring'),
    (r'(?i)\b(docker|k8s|容器|镜像)\b', '容器化'),
    (r'(?i)\b(算法|排序|查找|动态规划|递归|复杂度)\b', '算法'),
    (r'(?i)\b(linux|shell|命令行|bash)\b', 'Linux'),
    (r'(?i)\b(安全|xss|csrf|sql注入|加密)\b', '安全'),
    (r'(?i)\b(高并发|高可用|秒杀|限流|熔断)\b', '高可用'),
    (r'(?i)\b(项目|经历|团队|管理|沟通)\b', '软技能'),
]


def classify_question(question: str) -> str:
    """根据题目内容自动分类"""
    text_lower = question.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[cat] = score

    if not scores:
        return "java"  # 默认分类

    return max(scores, key=scores.get)


def auto_tag(question: str) -> list[str]:
    """根据题目内容自动打标签"""
    tags = set()
    for pattern, tag in AUTO_TAG_RULES:
        if re.search(pattern, question):
            tags.add(tag)
    return sorted(tags)


def estimate_difficulty(question: str) -> str:
    """根据题目关键词估计难度"""
    hard_keywords = [
        "源码", "底层", "原理", "为什么选择", "对比", "优化", "调优",
        "分布式", "一致性", "高并发", "亿级", "千万级", "架构",
        "raft", "paxos", "设计一个", "如何实现",
    ]
    easy_keywords = [
        "什么是", "区别", "定义", "介绍", "说说", "用过吗", "有哪些",
    ]

    hard_score = sum(1 for kw in hard_keywords if kw in question)
    easy_score = sum(1 for kw in easy_keywords if kw in question)

    if hard_score >= 2:
        return "hard"
    if easy_score >= 2 and hard_score == 0:
        return "easy"
    return "medium"


def generate_id(question: str, index: dict) -> str:
    """生成唯一题号"""
    existing = {q["id"] for q in index["questions"]}
    num = len(index["questions"]) + 1
    while True:
        qid = f"q{num:04d}"
        if qid not in existing:
            return qid
        num += 1


def slugify(text: str, max_len: int = 60) -> str:
    """生成文件名友好的 slug"""
    slug = re.sub(r'[^\w\s-]', '', text)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:max_len].strip('-')


# ============================================================
# 题库管理器
# ============================================================

class QuestionManager:
    """题库管理核心类"""

    def __init__(self):
        self.index = self._load_index()
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        for cat in self.index["categories"]:
            (DATABASE_DIR / cat).mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict:
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"meta": {}, "categories": {}, "difficulty_levels": {}, "questions": []}

    def _save_index(self):
        self.index["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.index["meta"]["total_questions"] = len(self.index["questions"])
        # 统计每分类数量
        cat_count = {}
        for q in self.index["questions"]:
            c = q.get("category", "java")
            cat_count[c] = cat_count.get(c, 0) + 1
        for cat in self.index["categories"]:
            self.index["categories"][cat]["count"] = cat_count.get(cat, 0)

        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def add(self, question: str, answer: str, *,
            category: Optional[str] = None,
            tags: Optional[list[str]] = None,
            difficulty: Optional[str] = None,
            source: str = "") -> dict:
        """添加一道题到题库"""

        # 去重检查
        q_hash = hashlib.md5(question.strip().lower().encode()).hexdigest()[:8]
        for existing in self.index["questions"]:
            existing_hash = hashlib.md5(existing["question"].strip().lower().encode()).hexdigest()[:8]
            if existing_hash == q_hash:
                print(f"⚠️  题目已存在 (ID: {existing['id']}), 跳过")
                return existing

        # 自动分类
        cat = category or classify_question(question)
        if cat not in self.index["categories"]:
            cat = "java"  # fallback

        # 自动标签
        final_tags = list(set((tags or []) + auto_tag(question)))

        # 自动难度
        diff = difficulty or estimate_difficulty(question)

        # 生成 ID
        qid = generate_id(question, self.index)

        # 生成文件名并写入答案文件
        slug = slugify(question)
        filename = f"{slug}.md"
        filepath = DATABASE_DIR / cat / filename

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 完整的答案文档（含元信息 frontmatter）
        file_content = f"""---
id: {qid}
question: "{question}"
category: {cat}
tags: {json.dumps(final_tags, ensure_ascii=False)}
difficulty: {diff}
created: {now}
source: {source or '用户输入'}
---

# {question}

{answer}

---

> 📋 **分类**: {self.index['categories'].get(cat, {}).get('name', cat)}
> 🏷️ **标签**: {' '.join(f'`{t}`' for t in final_tags)}
> 📊 **难度**: {self.index['difficulty_levels'].get(diff, {}).get('name', diff)}
> 📅 **归档时间**: {now}
"""

        filepath.write_text(file_content, encoding='utf-8')

        # 更新索引
        entry = {
            "id": qid,
            "question": question,
            "category": cat,
            "tags": final_tags,
            "difficulty": diff,
            "file": str(filepath.relative_to(PROJECT_ROOT)),
            "created": now,
            "source": source or "用户输入",
            "hash": q_hash,
        }
        self.index["questions"].append(entry)
        self._save_index()

        print(f"✅ 已归档: [{qid}] {question[:50]}... → {cat}/{filename}")
        return entry

    def search(self, keyword: str) -> list[dict]:
        """全文搜索题库"""
        kw = keyword.lower()
        results = []
        for q in self.index["questions"]:
            if (kw in q["question"].lower() or
                kw in q.get("category", "").lower() or
                any(kw in t.lower() for t in q.get("tags", []))):
                results.append(q)
        return results

    def stats(self) -> dict:
        """题库统计"""
        questions = self.index["questions"]
        stats = {
            "total": len(questions),
            "by_category": {},
            "by_difficulty": {},
            "by_tag": {},
            "recent": [],
        }
        for q in questions:
            cat = q.get("category", "unknown")
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            diff = q.get("difficulty", "medium")
            stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1

            for t in q.get("tags", []):
                stats["by_tag"][t] = stats["by_tag"].get(t, 0) + 1

        # 最近 5 条
        sorted_qs = sorted(questions, key=lambda q: q.get("created", ""), reverse=True)
        stats["recent"] = sorted_qs[:5]

        return stats

    def export(self, fmt: str = "markdown") -> str:
        """导出题库"""
        if fmt == "markdown":
            return self._export_markdown()
        return json.dumps(self.index, ensure_ascii=False, indent=2)

    def _export_markdown(self) -> str:
        lines = ["# 📚 面经题库 (完整归档)", ""]
        lines.append(f"> 共 {len(self.index['questions'])} 道题")
        lines.append(f"> 更新时间: {self.index['meta'].get('last_updated', 'unknown')}")
        lines.append("")

        stats = self.stats()
        lines.append("## 📊 分类统计")
        lines.append("| 分类 | 题目数 |")
        lines.append("|------|--------|")
        for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
            cat_name = self.index["categories"].get(cat, {}).get("name", cat)
            lines.append(f"| {cat_name} | {count} |")
        lines.append("")

        lines.append("## 📋 全部题目")
        for q in self.index["questions"]:
            cat_name = self.index["categories"].get(q.get("category", ""), {}).get("name", q.get("category", ""))
            tags = " ".join(f"`{t}`" for t in q.get("tags", []))
            lines.append(f"- **[{q['id']}]** {q['question']} — _{cat_name}_ {tags}")
        lines.append("")

        return "\n".join(lines)

    def dedup_check(self, question: str) -> Optional[dict]:
        """检查是否与已有题目重复"""
        q_hash = hashlib.md5(question.strip().lower().encode()).hexdigest()[:8]
        for q in self.index["questions"]:
            if q.get("hash") == q_hash:
                return q
        return None


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="题库管理器 — 面试题持久化、分类、索引、检索",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="添加新题")
    p_add.add_argument("--question", "-q", required=True, help="题目文本")
    p_add.add_argument("--answer", "-a", required=True, help="完整答案（Markdown）")
    p_add.add_argument("--category", "-c", help="手动指定分类")
    p_add.add_argument("--tags", "-t", nargs="*", help="手动指定标签")
    p_add.add_argument("--difficulty", "-d", choices=["easy", "medium", "hard"], help="难度")
    p_add.add_argument("--source", default="", help="题目来源")

    # search
    p_search = sub.add_parser("search", help="搜索题库")
    p_search.add_argument("keyword", help="搜索关键词")

    # stats
    sub.add_parser("stats", help="题库统计")

    # export
    p_export = sub.add_parser("export", help="导出题库")
    p_export.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown")
    p_export.add_argument("--output", "-o", help="输出文件路径")

    # tag
    p_tag = sub.add_parser("tag", help="修改标签")
    p_tag.add_argument("id", help="题号 (如 q0001)")
    p_tag.add_argument("--add", nargs="*", dest="add_tags", help="添加标签")
    p_tag.add_argument("--remove", nargs="*", dest="remove_tags", help="移除标签")

    # dedup
    p_dedup = sub.add_parser("dedup", help="去重检查")
    p_dedup.add_argument("question", help="要检查的题目")

    args = parser.parse_args()
    mgr = QuestionManager()

    if args.cmd == "add":
        # 从文件读取答案
        answer = args.answer
        if Path(answer).exists():
            answer = Path(answer).read_text(encoding='utf-8')

        entry = mgr.add(
            question=args.question,
            answer=answer,
            category=args.category,
            tags=args.tags,
            difficulty=args.difficulty,
            source=args.source,
        )
        print(json.dumps(entry, ensure_ascii=False, indent=2))

    elif args.cmd == "search":
        results = mgr.search(args.keyword)
        print(f"\n🔍 搜索 \"{args.keyword}\" — 找到 {len(results)} 条结果\n")
        for q in results:
            cat = mgr.index["categories"].get(q.get("category", ""), {}).get("name", "")
            diff = mgr.index["difficulty_levels"].get(q.get("difficulty", ""), {}).get("name", "")
            tags = " ".join(f"`{t}`" for t in q.get("tags", []))
            print(f"  [{q['id']}] {q['question'][:80]}")
            print(f"       📂 {cat} | 📊 {diff} | {tags}")
            print()

    elif args.cmd == "stats":
        stats = mgr.stats()
        print(f"\n📊 题库统计")
        print(f"{'='*50}")
        print(f"📝 总题数: {stats['total']}")
        print(f"\n📂 按分类:")
        for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
            cat_name = mgr.index["categories"].get(cat, {}).get("name", cat)
            bar = "█" * min(count, 20)
            print(f"  {cat_name:12s} {count:3d}  {bar}")
        print(f"\n📊 按难度:")
        for diff, count in stats["by_difficulty"].items():
            diff_name = mgr.index["difficulty_levels"].get(diff, {}).get("name", diff)
            print(f"  {diff_name}: {count}")
        print(f"\n🏷️  热门标签 Top 10:")
        for tag, count in sorted(stats["by_tag"].items(), key=lambda x: -x[1])[:10]:
            print(f"  {tag}: {count}")
        if stats["recent"]:
            print(f"\n🕐 最近归档:")
            for q in stats["recent"]:
                print(f"  [{q['id']}] {q['question'][:60]}")

    elif args.cmd == "export":
        content = mgr.export(args.format)
        if args.output:
            Path(args.output).write_text(content, encoding='utf-8')
            print(f"✅ 已导出到: {args.output}")
        else:
            print(content)

    elif args.cmd == "tag":
        for q in mgr.index["questions"]:
            if q["id"] == args.id:
                if args.add_tags:
                    for t in args.add_tags:
                        if t not in q["tags"]:
                            q["tags"].append(t)
                if args.remove_tags:
                    q["tags"] = [t for t in q["tags"] if t not in args.remove_tags]
                mgr._save_index()
                print(f"✅ 已更新 [{args.id}] 标签: {q['tags']}")
                return
        print(f"❌ 未找到题目: {args.id}")

    elif args.cmd == "dedup":
        dup = mgr.dedup_check(args.question)
        if dup:
            print(f"⚠️  存在重复: [{dup['id']}] {dup['question'][:80]}")
        else:
            print("✅ 未发现重复，可以添加")


if __name__ == "__main__":
    main()
