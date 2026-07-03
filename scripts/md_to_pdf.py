#!/usr/bin/env python3
"""
Markdown → PDF 转换器
======================
将生成的面试解答 Markdown 文档转换为排版精美的 PDF 文件。

支持两种后端：
  1. weasyprint (推荐) — 专业的 CSS 排版引擎
  2. markdown + reportlab (备选) — 纯 Python 方案

Usage:
  python md_to_pdf.py outputs/面经解答-20260704.md
  python md_to_pdf.py outputs/*.md --style modern
  python md_to_pdf.py answer.md -o my_answer.pdf

安装依赖:
  pip install weasyprint markdown pygments
"""

import sys
import argparse
import textwrap
from pathlib import Path
from datetime import datetime


def check_dependencies():
    """检查并返回可用的后端"""
    backends = []

    # 检查 weasyprint (推荐)
    try:
        import weasyprint  # noqa: F401
        backends.append("weasyprint")
    except ImportError:
        pass

    # 检查 markdown + 基本方案
    try:
        import markdown  # noqa: F401
        backends.append("markdown")
    except ImportError:
        pass

    return backends


def convert_weasyprint(md_path: Path, output_path: Path, style: str = "modern"):
    """使用 weasyprint 转换（最佳效果）"""
    import markdown
    from weasyprint import HTML

    md_text = md_path.read_text(encoding='utf-8')

    # Markdown → HTML
    md_extensions = [
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.nl2br',
    ]
    html_body = markdown.markdown(md_text, extensions=md_extensions)

    # CSS 样式
    css_styles = {
        "modern": """
            @page { margin: 2cm; size: A4; }
            body {
                font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
                font-size: 11pt; line-height: 1.8; color: #333;
            }
            h1 { font-size: 22pt; color: #1a1a2e; border-bottom: 3px solid #58a6ff; padding-bottom: 8px; margin-top: 0; }
            h2 { font-size: 16pt; color: #16213e; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; margin-top: 28px; }
            h3 { font-size: 13pt; color: #0f3460; margin-top: 20px; }
            h4 { font-size: 11pt; color: #555; }
            p { margin: 8px 0; }
            code {
                background: #f5f5f5; padding: 2px 6px; border-radius: 3px;
                font-family: 'JetBrains Mono', 'Fira Code', 'Menlo', monospace; font-size: 9pt;
            }
            pre {
                background: #f8f8f8; border: 1px solid #e0e0e0; border-radius: 6px;
                padding: 14px; overflow-x: auto; font-size: 9pt; line-height: 1.5;
            }
            pre code { background: none; padding: 0; }
            table {
                width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10pt;
            }
            th { background: #f0f4ff; padding: 8px 12px; border: 1px solid #d0d0d0; text-align: left; font-weight: 600; }
            td { padding: 6px 12px; border: 1px solid #e0e0e0; }
            blockquote {
                border-left: 4px solid #58a6ff; margin: 12px 0; padding: 8px 16px;
                background: #f0f7ff; color: #555; border-radius: 0 6px 6px 0;
            }
            ul, ol { margin: 8px 0; padding-left: 24px; }
            li { margin: 4px 0; }
            hr { border: none; border-top: 1px solid #e0e0e0; margin: 24px 0; }
            strong { color: #222; }
            a { color: #58a6ff; text-decoration: none; }
        """,
        "minimal": """
            @page { margin: 2.5cm; size: A4; }
            body {
                font-family: 'PingFang SC', 'Hiragino Sans GB', sans-serif;
                font-size: 10.5pt; line-height: 1.7; color: #333;
            }
            h1 { font-size: 20pt; border-bottom: 1px solid #ccc; padding-bottom: 6px; }
            h2 { font-size: 14pt; margin-top: 24px; }
            h3 { font-size: 12pt; }
            code { background: #f5f5f5; padding: 1px 4px; font-size: 9pt; }
            pre { background: #f9f9f9; padding: 12px; border: 1px solid #eee; font-size: 8.5pt; }
            pre code { background: none; }
            table { border-collapse: collapse; font-size: 9.5pt; }
            th, td { border: 1px solid #ddd; padding: 6px 10px; }
            th { background: #f5f5f5; }
            blockquote { border-left: 3px solid #ddd; padding: 6px 12px; color: #666; }
        """,
    }

    css = css_styles.get(style, css_styles["modern"])
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><style>{css}</style></head>
<body>{html_body}</body>
</html>"""

    HTML(string=full_html).write_pdf(str(output_path))
    return True


def convert_markdown_only(md_path: Path, output_path: Path):
    """仅用 markdown 库做基本转换，保存为 HTML（用户可手动打印为 PDF）"""
    import markdown

    md_text = md_path.read_text(encoding='utf-8')
    html_body = markdown.markdown(
        md_text,
        extensions=['markdown.extensions.tables', 'markdown.extensions.fenced_code',
                    'markdown.extensions.codehilite', 'markdown.extensions.toc']
    )

    basic_css = """
        body { font-family: 'PingFang SC', sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.8; }
        h1 { border-bottom: 2px solid #58a6ff; padding-bottom: 8px; }
        h2 { border-bottom: 1px solid #eee; padding-bottom: 4px; margin-top: 28px; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
        pre { background: #f8f8f8; padding: 14px; border-radius: 6px; overflow-x: auto; }
        pre code { background: none; padding: 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px 12px; }
        th { background: #f5f5f5; }
        blockquote { border-left: 4px solid #58a6ff; padding: 8px 16px; background: #f0f7ff; }
    """

    html_path = output_path.with_suffix('.html')
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{md_path.stem}</title><style>{basic_css}</style></head>
<body>{html_body}</body>
</html>"""

    html_path.write_text(html_content, encoding='utf-8')
    return html_path


def main():
    parser = argparse.ArgumentParser(
        description="Markdown → PDF 转换器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="+", help="Markdown 文件路径")
    parser.add_argument("-o", "--output", help="输出 PDF 文件路径")
    parser.add_argument(
        "--style", choices=["modern", "minimal"],
        default="modern", help="排版风格 (默认: modern)"
    )

    args = parser.parse_args()

    backends = check_dependencies()

    if not backends:
        print("❌ 请安装依赖: pip install markdown weasyprint pygments")
        print("   或最小安装: pip install markdown")
        sys.exit(1)

    use_weasyprint = "weasyprint" in backends

    if not use_weasyprint:
        print("⚠️  weasyprint 未安装，将输出 HTML 文件（可在浏览器中打印为 PDF）")
        print("   推荐安装: pip install weasyprint")

    for fp in args.files:
        md_path = Path(fp)
        if not md_path.exists():
            print(f"⚠️  跳过: {fp}")
            continue

        if args.output and len(args.files) == 1:
            output_path = Path(args.output)
        else:
            output_path = md_path.with_suffix('.pdf')

        print(f"📄 转换: {md_path.name} → {output_path.name}")

        if use_weasyprint:
            try:
                convert_weasyprint(md_path, output_path, args.style)
                print(f"  ✅ 已保存: {output_path}")
            except Exception as e:
                print(f"  ❌ 转换失败: {e}")
                print("  回退到 HTML 模式...")
                html_path = convert_markdown_only(md_path, output_path)
                print(f"  ✅ HTML 已保存: {html_path}")
        else:
            html_path = convert_markdown_only(md_path, output_path)
            print(f"  ✅ HTML 已保存: {html_path}")
            print(f"  💡 在浏览器中打开 {html_path}，按 Cmd+P 打印为 PDF")


if __name__ == "__main__":
    main()
