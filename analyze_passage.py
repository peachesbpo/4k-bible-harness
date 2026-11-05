#!/usr/bin/env python3
"""
4K Bible Translation Harness
Analyzes biblical passages in original languages and produces expanded translations
with diff views showing nuance lost in standard English translations.

Output Format: Results-First (Business Efficiency)
  1. Diff Analysis (what got lost)
  2. Expanded Translation (4K, clean English)
  3. Baseline Translation (ESV)
  4. Original Language Analysis (supporting detail)
  5. Theological Insights
  6. Notes for Further Study

Output Formats: Markdown + HTML + PDF
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from weasyprint import HTML as WeasyHTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


class BiblePassageAnalyzer:
    """Main analyzer class for 4K Bible translation work."""

    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        self.template = self._load_template()
        self.output_options = self.config.get("output_options", {})

    def _load_config(self, config_path):
        default_config = {
            "translations": {
                "ESV": "English Standard Version",
                "NASB": "New American Standard Bible",
                "KJV": "King James Version"
            },
            "api_endpoints": {
                "bible_api": "https://api.scripture.api.bible/v1",
                "biblehub_text": "https://biblehub.com/text/{book}/{chapter}-{verse}.htm",
                "biblehub_strongs": "https://biblehub.com/greek/{strongs}.htm",
                "blue_letter_interlinear": "https://www.blueletterbible.org/interlinear/"
            },
            "default_translation": "ESV",
            "output_dir": "passages",
            "original_language_priority": ["Greek", "Hebrew", "Aramaic"],
            "analysis_options": {
                "include_strongs": True,
                "include_parsing": True,
                "include_lexical_range": True,
                "include_cultural_context": True,
                "include_cross_references": True
            },
            "output_options": {
                "format": "results-first",
                "generate_md": True,
                "generate_html": True,
                "generate_pdf": True,
                "html_theme": "dark",
                "expanded_translation_style": "clean_english",
                "expanded_translation_note_style": "parenthetical"
            }
        }

        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                loaded = json.load(f)
                default_config.update(loaded)

        return default_config

    def _load_template(self):
        template_path = Path(__file__).parent / "template.md"
        if template_path.exists():
            return template_path.read_text()
        else:
            raise FileNotFoundError(f"Template not found at {template_path}")

    def parse_passage_reference(self, passage):
        """Parse a passage reference like 'Matthew 5:3-12' into components."""
        pattern = r'([A-Za-z]+)\s+(\d+):(\d+)(?:-(\d+))?'
        match = re.match(pattern, passage)

        if not match:
            raise ValueError(f"Invalid passage format: {passage}")

        book, chapter, start_verse, end_verse = match.groups()
        return {
            "book": book,
            "chapter": int(chapter),
            "start_verse": int(start_verse),
            "end_verse": int(end_verse) if end_verse else int(start_verse)
        }

    def fetch_baseline_translation(self, passage_ref, translation="ESV"):
        """Fetch the baseline English translation."""
        print(f"📖 Fetching {passage_ref} from {translation}...")
        return "[Baseline translation to be fetched from API]"

    def fetch_original_language(self, passage_ref):
        """Fetch original language text (Greek/Hebrew)."""
        print(f"🔍 Fetching original language text for {passage_ref}...")
        return {"language": "Unknown", "text_version": "Unknown", "verses": {}}

    def create_expanded_translation(self, baseline, original_data, analyses):
        """Create expanded translation incorporating original language nuances.

        Style: Clean English only, parenthetical notes for nuance.
        No Greek, no Strong's numbers, no parsing codes.
        """
        return "[Expanded translation to be generated]"

    def generate_diff_analysis(self, baseline, expanded):
        """Generate analysis of what nuances were lost in baseline."""
        return []

    def render_output(self, passage_ref, baseline, original_data, expanded, diff_notes):
        """Render the final markdown output using the results-first template."""
        ref_data = self.parse_passage_reference(passage_ref)

        # Build verse-by-verse analysis
        verse_analyses = []
        for verse_num in range(ref_data["start_verse"], ref_data["end_verse"] + 1):
            verse_ref = f"{ref_data['chapter']}:{verse_num}"
            greek_text = original_data.get("verses", {}).get(verse_ref, "")
            key_words = self.analyze_key_words(verse_ref, greek_text)

            verse_analyses.append({
                "reference": f"Matthew {verse_ref}",
                "greek": greek_text,
                "key_words": key_words
            })

        # Fill template
        output = self.template
        output = output.replace("{{PASSAGE_REFERENCE}}", passage_ref)
        output = output.replace("{{DATE}}", datetime.now().strftime("%Y-%m-%d"))
        output = output.replace("{{TRANSLATION_NAME}}", self.config["default_translation"])
        output = output.replace("{{LANGUAGE}}", original_data.get("language", "Unknown"))
        output = output.replace("{{TEXT_VERSION}}", original_data.get("text_version", "Unknown"))
        output = output.replace("{{PASSAGE_CONTEXT}}", "Passage context to be added")
        output = output.replace("{{BASELINE_TEXT}}", baseline)
        output = output.replace("{{EXPANDED_CLEAN_ENGLISH}}", expanded if expanded else "[Expanded translation pending]")

        # Build diff table
        diff_rows = []
        for i, note in enumerate(diff_notes, 1):
            diff_rows.append(f"| {i} | \"{note['baseline']}\" | {note.get('what_lost', note.get('expanded', ''))} | {note.get('why_matters', note.get('impact', ''))} |")
        diff_table = "\n".join(diff_rows) if diff_rows else "| [Diff analysis to be added] |"
        output = output.replace("| {{BASELINE_PHRASE}} | {{WHAT_LOST}} | {{WHY_MATTERS}} |", diff_table)

        # Fill remaining placeholders
        output = output.replace("{{VERSE_REFERENCE}}", verse_analyses[0]["reference"] if verse_analyses else "Unknown")
        output = output.replace("{{ORIGINAL_TEXT}}", verse_analyses[0]["greek"] if verse_analyses else "")
        output = output.replace("{{ANALYST}}", "Peaches (4K Bible Translation Harness)")
        output = output.replace("{{REVIEW_STATUS}}", "Draft - Ready for Review")

        # Clear any unfilled template variables
        output = re.sub(r'\{\{[^}]+\}\}', '[To be filled]', output)

        return output

    def generate_html(self, md_content, theme="dark"):
        """Generate styled HTML from markdown content."""
        if HAS_MARKDOWN:
            html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'toc', 'nl2br'])
        else:
            # Fallback: basic regex conversion
            html_body = md_content
            html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
            html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
            html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
            html_body = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_body, flags=re.MULTILINE)
            html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
            html_body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)
            html_body = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html_body, flags=re.MULTILINE)
            html_body = re.sub(r'^---$', '<hr>', html_body, flags=re.MULTILINE)

        if theme == "dark":
            css = self._dark_css()
        else:
            css = self._light_css()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4K Translation Analysis</title>
    <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    def _dark_css(self):
        return """
    :root { --bg: #1a1a2e; --card: #16213e; --text: #e0e0e0; --accent: #f4a261; --heading: #ffd6a5; --border: #2a2a4a; }
    body { font-family: 'Georgia', 'Times New Roman', serif; background: var(--bg); color: var(--text); line-height: 1.8; max-width: 960px; margin: 0 auto; padding: 40px 24px; }
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
    hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
        """

    def _light_css(self):
        return """
    body { font-family: 'Georgia', 'Times New Roman', serif; line-height: 1.8; max-width: 960px; margin: 0 auto; padding: 40px 24px; color: #333; }
    h1 { color: #2c3e50; font-size: 2em; border-bottom: 2px solid #f4a261; padding-bottom: 12px; }
    h2 { color: #34495e; font-size: 1.5em; margin: 32px 0 16px; border-bottom: 1px solid #bdc3c7; padding-bottom: 8px; }
    h3 { color: #7f8c8d; font-size: 1.2em; margin: 24px 0 12px; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9em; }
    th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; vertical-align: top; }
    th { background: #f4a261; color: white; }
    blockquote { border-left: 4px solid #f4a261; margin: 16px 0; padding: 12px 20px; background: #f8f9fa; font-style: italic; }
    hr { border: none; border-top: 1px solid #bdc3c7; margin: 32px 0; }
        """

    def generate_pdf(self, html_content, pdf_path):
        """Generate PDF from HTML using WeasyPrint."""
        if not HAS_WEASYPRINT:
            print("⚠️  WeasyPrint not available. Skipping PDF.")
            return False
        WeasyHTML(string=html_content).write_pdf(str(pdf_path))
        return True

    def analyze_passage(self, passage_ref, translation="ESV", output_file=None):
        """Run the complete analysis pipeline."""
        print(f"\n🍑 Starting 4K Bible Translation Analysis for {passage_ref}...\n")

        # Step 1: Fetch baseline
        baseline = self.fetch_baseline_translation(passage_ref, translation)

        # Step 2: Fetch original language
        original_data = self.fetch_original_language(passage_ref)

        # Step 3: Create expanded translation (clean English)
        expanded = self.create_expanded_translation(baseline, original_data, {})

        # Step 4: Generate diff analysis
        diff_notes = self.generate_diff_analysis(baseline, expanded)

        # Step 5: Render markdown output
        md_output = self.render_output(passage_ref, baseline, original_data, expanded, diff_notes)

        # Step 6: Determine output paths
        if output_file:
            md_path = Path(output_file)
        else:
            output_dir = Path(__file__).parent / self.config["output_dir"]
            output_dir.mkdir(exist_ok=True)
            safe_name = passage_ref.replace(" ", "_").replace(":", "-")
            md_path = output_dir / f"{safe_name}.md"

        # Step 7: Write Markdown
        if self.output_options.get("generate_md", True):
            md_path.write_text(md_output)
            print(f"✅ Markdown: {md_path}")

        # Step 8: Write HTML
        html_path = None
        if self.output_options.get("generate_html", True):
            html_path = md_path.with_suffix('.html')
            theme = self.output_options.get("html_theme", "dark")
            html_content = self.generate_html(md_output, theme=theme)
            html_path.write_text(html_content)
            print(f"✅ HTML:     {html_path}")

        # Step 9: Write PDF
        pdf_path = None
        if self.output_options.get("generate_pdf", True) and html_path:
            pdf_path = md_path.with_suffix('.pdf')
            html_content = html_path.read_text()
            if self.generate_pdf(html_content, pdf_path):
                print(f"✅ PDF:      {pdf_path}")

        print(f"\n📊 Key findings:")
        for note in diff_notes[:3]:
            print(f"   • {note['baseline']} → {note.get('what_lost', note.get('expanded', ''))}")
        if len(diff_notes) > 3:
            print(f"   ...and {len(diff_notes) - 3} more nuance gaps identified")

        print(f"\n🎉 Analysis complete! Ready for review: {md_path}")
        return md_path


def main():
    parser = argparse.ArgumentParser(
        description="4K Bible Translation Harness - Recover original language nuances"
    )
    parser.add_argument("--passage", "-p", required=True,
                        help="Bible passage reference (e.g., 'Matthew 5:3-12')")
    parser.add_argument("--translation", "-t", default="ESV",
                        choices=["ESV", "NASB", "KJV"],
                        help="Baseline translation to use (default: ESV)")
    parser.add_argument("--output", "-o",
                        help="Output file path (default: passages/<passage>.md)")
    parser.add_argument("--config", "-c",
                        help="Path to config.json file")
    parser.add_argument("--md-only", action="store_true",
                        help="Generate Markdown only (skip HTML/PDF)")
    parser.add_argument("--theme", choices=["dark", "light"], default=None,
                        help="HTML/PDF theme (overrides config)")

    args = parser.parse_args()

    analyzer = BiblePassageAnalyzer(args.config)

    if args.md_only:
        analyzer.output_options["generate_html"] = False
        analyzer.output_options["generate_pdf"] = False

    if args.theme:
        analyzer.output_options["html_theme"] = args.theme

    output_path = analyzer.analyze_passage(args.passage, args.translation, args.output)


if __name__ == "__main__":
    main()
