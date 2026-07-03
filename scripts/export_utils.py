#!/usr/bin/env python3
"""
导出工具集
===========
全面的题库导出功能集。

功能:
  pdf-all       — 全部题目导出为单个 PDF
  pdf-each      — 每道题导出为独立 PDF
  html-all      — 全部题目导出为单个 HTML 文档
  markdown-all  — 全部题目导出为单个 Markdown
  json-all      — 全部题目导出为 JSON
  opml          — 导出为 OPML（思维导图格式）
  rss           — 生成 RSS Feed

Usage:
  python scripts/export_utils.py pdf-all --output all_questions.pdf
  python scripts/export_utils.py html-all --output interview_guide.html
  python scripts/export_utils.py opml --output knowledge_map.opml
  python scripts/export_utils.py rss --output feed.xml
"""

import sys, json, argparse, shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "questions" / "index.json"
DATABASE_DIR = PROJECT_ROOT / "questions" / "database"


def load_index():
    if not INDEX_FILE.exists():
        print("❌ 题库为空")
        sys.exit(1)
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all_answers(index: dict) -> list[dict]:
    """加载所有题目+答案"""
    questions = index.get("questions", [])
    for q in questions:
        filepath = PROJECT_ROOT / q.get("file", "")
        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
            if content.startswith('---'):
                end = content.find('---', 3)
                if end > 0:
                    content = content[end + 3:].strip()
            q["_answer"] = content
        else:
            q["_answer"] = ""
    return questions


def pdf_all(index: dict, output: str):
    """导出全部为 PDF"""
    try:
        import markdown
        from weasyprint import HTML
    except ImportError:
        print("❌ 需要: pip install markdown weasyprint")
        return

    questions = load_all_answers(index)

    # 构建 HTML
    html_parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"><style>',
                  'body{font-family:"PingFang SC",sans-serif;max-width:800px;margin:40px auto;line-height:1.8}',
                  'h1{font-size:20pt;border-bottom:3px solid #58a6ff}',
                  'h2{font-size:14pt;border-bottom:1px solid #eee;margin-top:28px}',
                  'pre{background:#f5f5f5;padding:12px;border-radius:6px}',
                  'code{background:#f5f5f5;padding:2px 6px}',
                  'table{border-collapse:collapse;width:100%}',
                  'th,td{border:1px solid #ddd;padding:8px 12px}',
                  '</style></head><body>']

    html_parts.append(f'<h1>📚 面经题库 (共 {len(questions)} 题)</h1>')
    html_parts.append(f'<p>导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>')

    # 目录
    html_parts.append('<h2>目录</h2><ol>')
    for i, q in enumerate(questions, 1):
        html_parts.append(f'<li><a href="#q{i}">{q["question"][:80]}</a></li>')
    html_parts.append('</ol>')

    # 内容
    for i, q in enumerate(questions, 1):
        html_parts.append(f'<h2 id="q{i}">第{i}题: {q["question"]}</h2>')
        html_parts.append(f'<p><strong>分类:</strong> {q.get("category","")} | <strong>难度:</strong> {q.get("difficulty","")} | <strong>标签:</strong> {", ".join(q.get("tags",[]))}</p>')
        md_html = markdown.markdown(q.get("_answer", ""), extensions=['tables', 'fenced_code'])
        html_parts.append(md_html)
        html_parts.append('<hr>')

    html_parts.append('</body></html>')
    full_html = '\n'.join(html_parts)

    HTML(string=full_html).write_pdf(output)
    print(f"✅ PDF 已导出: {output} ({len(questions)} 题)")


def html_all(index: dict, output: str):
    """导出全部为 HTML"""
    questions = load_all_answers(index)
    cats = index.get("categories", {})

    lines = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<title>面经题库</title>',
             '<style>',
             'body{font-family:"PingFang SC",sans-serif;max-width:860px;margin:0 auto;padding:24px;line-height:1.8;color:#333;background:#fff}',
             'h1{font-size:1.5rem;border-bottom:2px solid #58a6ff;padding-bottom:8px}',
             'h2{font-size:1.2rem;margin-top:32px;border-bottom:1px solid #eee}',
             'pre{background:#f8f8f8;padding:14px;border-radius:8px;overflow-x:auto}',
             'code{background:#f5f5f5;padding:2px 6px;border-radius:3px}',
             '.tag{display:inline-block;padding:2px 8px;margin:2px;background:#e8e0f0;border-radius:4px;font-size:0.8rem}',
             '.cat{color:#58a6ff;font-weight:600}',
             '.meta{color:#888;font-size:0.85rem;margin-bottom:16px}',
             '</style></head><body>']

    lines.append(f'<h1>📚 面经题库</h1>')
    lines.append(f'<p class="meta">共 {len(questions)} 题 · 导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>')

    # TOC
    lines.append('<h2>📑 目录</h2><ol>')
    for i, q in enumerate(questions, 1):
        lines.append(f'<li><a href="#q{i}">[{q["id"]}] {q["question"][:80]}</a></li>')
    lines.append('</ol>')

    # Content
    for i, q in enumerate(questions, 1):
        cat = cats.get(q.get("category", ""), {})
        lines.append(f'<h2 id="q{i}">第{i}题: {q["question"]}</h2>')
        lines.append(f'<p class="meta"><span class="cat">{cat.get("icon","")} {cat.get("name",q.get("category",""))}</span> | {q.get("difficulty","")} | {" ".join(f"<span class=tag>{t}</span>" for t in q.get("tags",[]))}</p>')
        lines.append(f'<div>{q.get("_answer","").replace(chr(10), "<br>")}</div>')
        lines.append('<hr>')

    lines.append('</body></html>')
    Path(output).write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ HTML 已导出: {output} ({len(questions)} 题)")


def markdown_all(index: dict, output: str):
    """导出全部为 Markdown"""
    questions = load_all_answers(index)
    cats = index.get("categories", {})

    lines = [
        f"# 📚 面经题库",
        f"",
        f"> 共 {len(questions)} 题 · 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 📑 目录",
        f"",
    ]

    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. [{q['id']}] {q['question'][:80]}")

    lines.append("")
    lines.append("---")
    lines.append("")

    for i, q in enumerate(questions, 1):
        cat = cats.get(q.get("category", ""), {})
        lines.append(f"## 第{i}题: {q['question']}")
        lines.append(f"")
        lines.append(f"> 📂 {cat.get('icon','')} {cat.get('name', q.get('category', ''))} | 📊 {q.get('difficulty', '')} | 🏷️ {' '.join(q.get('tags', []))}")
        lines.append(f"")
        lines.append(q.get("_answer", ""))
        lines.append("")
        lines.append("---")
        lines.append("")

    Path(output).write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ Markdown 已导出: {output} ({len(questions)} 题)")


def json_all(index: dict, output: str):
    """导出全部为 JSON"""
    questions = load_all_answers(index)
    export = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(questions),
        "questions": [{**{k: v for k, v in q.items() if not k.startswith('_')}, "answer": q.get("_answer", "")} for q in questions],
    }
    Path(output).write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✅ JSON 已导出: {output} ({len(questions)} 题)")


def opml(index: dict, output: str):
    """导出为 OPML（思维导图格式）"""
    questions = load_all_answers(index)
    cats = index.get("categories", {})

    # 按分类分组
    groups = {}
    for q in questions:
        cat = q.get("category", "unknown")
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(q)

    opml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        '<head><title>Interview Coach — 知识图谱</title></head>',
        '<body>',
        f'<outline text="📚 面经题库 ({len(questions)} 题)">',
    ]

    for cat_key, cat_qs in sorted(groups.items()):
        cat = cats.get(cat_key, {})
        opml_parts.append(f'<outline text="{cat.get("icon","")} {cat.get("name", cat_key)} ({len(cat_qs)} 题)">')
        for q in cat_qs:
            escaped = q["question"].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            opml_parts.append(f'<outline text="[{q["id"]}] {escaped[:80]}"/>')
        opml_parts.append('</outline>')

    opml_parts.extend(['</outline>', '</body>', '</opml>'])
    Path(output).write_text('\n'.join(opml_parts), encoding='utf-8')
    print(f"✅ OPML 已导出: {output} ({len(questions)} 题, {len(groups)} 分类)")
    print(f"   可导入到 XMind、MindNode 等思维导图工具")


def rss(index: dict, output: str):
    """生成 RSS Feed"""
    questions = load_all_answers(index)
    repo_url = "https://github.com/Dddddduo/dduo-interview-coach"

    items = []
    for q in sorted(questions, key=lambda q: q.get("created", ""), reverse=True)[:50]:
        pub_date = q.get("created", datetime.now().strftime("%Y-%m-%d"))
        items.append(f"""    <item>
      <title>{q['question'].replace('&','&amp;').replace('<','&lt;')}</title>
      <link>{repo_url}</link>
      <guid isPermaLink="false">{q['id']}</guid>
      <pubDate>{pub_date}</pubDate>
      <category>{q.get('category','')}</category>
      <description><![CDATA[<p>分类: {q.get('category','')} | 难度: {q.get('difficulty','')} | 标签: {', '.join(q.get('tags',[]))}</p>]]></description>
    </item>""")

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Interview Coach — 面经题库</title>
    <link>{repo_url}</link>
    <description>基于 Harness Engineering 的 AI 面试备考系统 — 题库 RSS Feed</description>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>"""

    Path(output).write_text(rss_content, encoding='utf-8')
    print(f"✅ RSS Feed 已导出: {output} ({len(items)} 条)")


def main():
    parser = argparse.ArgumentParser(description="导出工具集")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for cmd_name in ["pdf-all", "pdf-each", "html-all", "markdown-all", "json-all", "opml", "rss"]:
        p = sub.add_parser(cmd_name, help=f"导出为 {cmd_name}")
        p.add_argument("--output", "-o", required=True, help="输出文件路径")
        if "category" not in cmd_name:
            p.add_argument("--category", "-c", help="按分类筛选")

    args = parser.parse_args()
    index = load_index()

    exporters = {
        "pdf-all": pdf_all,
        "html-all": html_all,
        "markdown-all": markdown_all,
        "json-all": json_all,
        "opml": opml,
        "rss": rss,
    }

    exporter = exporters.get(args.cmd)
    if exporter:
        exporter(index, args.output)


if __name__ == "__main__":
    main()
