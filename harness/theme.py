"""theme.py — CSS themes for HTML/PDF output."""

DARK_CSS = """
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

LIGHT_CSS = """
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
