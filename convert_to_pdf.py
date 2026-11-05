#!/usr/bin/env python3
"""
4K Bible Translation Harness — PDF Converter
Converts Markdown passage analyses to styled HTML and PDF.

Usage:
    python3 convert_to_pdf.py <input.md> [--output <path>] [--theme dark|light]

Outputs:
    <input>.html  — Styled HTML
    <input>.pdf   — Print-ready PDF (via WeasyPrint)
"""

import sys
import re
import argparse
from pathlib import Path

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False
    print("⚠️  WeasyPrint not installed. Install with: pip install weasyprint")

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("⚠️  markdown not installed. Install with: pip install markdown")


DARK_THEME = """
    :root {
        --bg: #1a1a2e;
        --card: #16213e;
        --text: #e0e0e0;
        --accent: #f4a261;
        --heading: #ffd6a5;
        --border: #2a2a4a;
    }
    body {
        font-family: 'Georgia', 'Times New Roman', serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.8;
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 24px;
    }
    h1 { color: var(--heading); font-size: 2em; margin-bottom: 8px; border-bottom: 2px solid var(--accent); padding-bottom: 12px; }
    h2 { color: var(--heading); font-size: 1.5em; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
    h3 { color: var(--accent); font-size: 1.2em; margin: 24px 0 12px; }
    h4 { color: var(--accent); font-size: 1.05em; margin: 20px 0 10px; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9em; }
    th, td { border: 1px solid var(--border); padding: 10px 12px; text-align: left; vertical-align: top; }
    th { background: var(--card); color: var(--heading); font-weight: bold; }
    tr:nth-child(even) { background: rgba(22, 33, 62, 0.5); }
    blockquote { border-left: 3px solid var(--accent); margin: 16px 0; padding: 12px 20px; background: var(--card); font-style: italic; }
    strong { color: var(--accent); }
    em { color: #b0d0ff; }
    code { background: var(--card); padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
    hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border); color: #888; font-size: 0.85em; }
    @media (max-width: 600px) { body { padding: 20px 12px; } table { font-size: 0.8em; } th, td { padding: 6px 8px; } }
"""

LIGHT_THEME = """
    body {
        font-family: 'Georgia', 'Times New Roman', serif;
        line-height: 1.8;
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 24px;
        color: #333;
    }
    h1 { color: #2c3e50; font-size: 2em; margin-bottom: 8px; border-bottom: 2px solid #f4a261; padding-bottom: 12px; }
    h2 { color: #34495e; font-size: 1.5em; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 1px solid #bdc3c7; }
    h3 { color: #7f8c8d; font-size: 1.2em; margin: 24px 0 12px; }
    h4 { color: #7f8c8d; font-size: 1.05em; margin: 20px 0 10px; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9em; }
    th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; vertical-align: top; }
    th { background: #f4a261; color: white; font-weight: bold; }
    tr:nth-child(even) { background-color: #f9f9f9; }
    blockquote { border-left: 4px solid #f4a261; margin: 16px 0; padding: 12px 20px; background: #f8f9fa; font-style: italic; }
    strong { color: #2c3e50; }
    hr { border: none; border-top: 1px solid #bdc3c7; margin: 32px 0; }
"""


def convert_md_to_html(md_path, theme="dark"):
    """Convert markdown to styled HTML."""
    md_content = Path(md_path).read_text()

    if not HAS_MARKDOWN:
        # Basic fallback conversion
        html_body = md_content
        html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
        html_body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)
        html_body = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^---$', '<hr>', html_body, flags=re.MULTILINE)
    else:
        html_body = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'toc', 'nl2br']
        )

    css = DARK_THEME if theme == "dark" else LIGHT_THEME

    title = Path(md_path).stem.replace('_', ' ')

    html_full = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — 4K Translation Analysis</title>
    <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    return html_full


def convert_to_pdf(html_content, pdf_path):
    """Convert HTML to PDF using WeasyPrint."""
    if not HAS_WEASYPRINT:
        print(f"⚠️  WeasyPrint not available. HTML written, but PDF not generated.")
        return False

    HTML(string=html_content).write_pdf(str(pdf_path))
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert 4K Bible Translation Markdown to HTML + PDF"
    )
    parser.add_argument("input", help="Input markdown file path")
    parser.add_argument("--output", "-o", help="Output base path (default: same as input)")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark",
                        help="HTML/PDF theme (default: dark)")
    parser.add_argument("--html-only", action="store_true",
                        help="Generate HTML only (skip PDF)")

    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(f"❌ Input file not found: {md_path}")
        sys.exit(1)

    # Determine output paths
    if args.output:
        base = Path(args.output)
    else:
        base = md_path.with_suffix('')

    html_path = base.with_suffix('.html')
    pdf_path = base.with_suffix('.pdf')

    # Convert
    print(f"📖 Converting {md_path.name}...")

    html_content = convert_md_to_html(md_path, theme=args.theme)
    html_path.write_text(html_content)
    print(f"✅ HTML: {html_path}")

    if not args.html_only:
        if convert_to_pdf(html_content, pdf_path):
            print(f"✅ PDF:  {pdf_path}")
        else:
            print(f"⚠️  PDF not generated (WeasyPrint unavailable)")

    print(f"\n🎉 Conversion complete!")


if __name__ == "__main__":
    main()
