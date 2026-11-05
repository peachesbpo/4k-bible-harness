"""repair.py — Scan and repair legacy passage files.

Scans existing passages/*.md for known issues:
  - Greek-text transliteration bleed (Latin letters mixed into Greek)
  - Missing/malformed verse metadata

Dry-run by default; applies with --apply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .text_purity import verify_greek, repair_greek


@dataclass
class RepairIssue:
    file: str
    line: int
    issue: str
    snippet: str
    fix: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# Match a Greek-text block: lines after "**Greek Text**" or starting with "> " that
# contain Greek Unicode chars.
GREEK_BLOCK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
GREEK_LINE_RE = re.compile(r"^(?:>\s*)?(.+[\u0370-\u03ff\u1f00-\u1fff].*)$")


def scan_file(path: Path) -> list[RepairIssue]:
    issues: list[RepairIssue] = []
    # Skip review/notes files — they contain prose about fixes, not source text
    if path.name.startswith("_review") or path.name == "SUMMARY.md":
        return issues
    try:
        text = path.read_text("utf-8")
    except Exception:
        return [RepairIssue(str(path), 0, "cannot read file", "")]

    def greek_ratio(s: str) -> float:
        alpha = [c for c in s if c.isalpha()]
        if not alpha:
            return 0.0
        greek = sum(1 for c in alpha if "\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff")
        return greek / len(alpha)

    import re as _re
    for i, line in enumerate(text.splitlines(), 1):
        if not GREEK_BLOCK_RE.search(line):
            continue
        # Skip lines with Strong's number references (table rows, concordance cites)
        if _re.search(r"\b[gG]\d{1,5}\b", line):
            continue
        stripped = re.sub(r"^[>\s]+", "", line)
        # Only check lines that are PRIMARILY Greek (>50% of alphabetic chars).
        # This avoids flagging English commentary with one inline Greek word.
        if greek_ratio(stripped) < 0.5:
            continue
        report = verify_greek(stripped)
        if not report.is_greek and report.latin_letters:
            issues.append(RepairIssue(
                file=str(path),
                line=i,
                issue=f"Greek-text bleed: {report.message}",
                snippet=line[:120],
                fix="greek_text repair",
            ))
    return issues


def scan_directory(dir_path: str) -> list[RepairIssue]:
    root = Path(dir_path)
    if not root.exists():
        return []
    issues: list[RepairIssue] = []
    for md in root.rglob("*.md"):
        if md.name == "SUMMARY.md":
            continue
        issues.extend(scan_file(md))
    return issues


def apply_repairs(issues: list[RepairIssue]) -> int:
    """Apply Greek-text repairs in-place. Returns count of files modified."""
    if not issues:
        return 0
    by_file: dict[str, list[RepairIssue]] = {}
    for i in issues:
        by_file.setdefault(i.file, []).append(i)
    modified = 0

    def greek_ratio(s: str) -> float:
        alpha = [c for c in s if c.isalpha()]
        if not alpha:
            return 0.0
        greek = sum(1 for c in alpha if "\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff")
        return greek / len(alpha)

    for fname, file_issues in by_file.items():
        path = Path(fname)
        try:
            text = path.read_text("utf-8")
        except Exception:
            continue
        new_lines = []
        changed = False
        for line in text.splitlines():
            if GREEK_BLOCK_RE.search(line):
                stripped = re.sub(r"^[>\s]+", "", line)
                if greek_ratio(stripped) >= 0.5:
                    report = verify_greek(stripped)
                    if not report.is_greek and report.latin_letters:
                        repaired, applied = repair_greek(stripped)
                        # Accept the repair if it reduced latin letters (even if
                        # non-latin issues like � remain — those need manual fix)
                        if applied:
                            new_report = verify_greek(repaired)
                            if len(new_report.latin_letters) < len(report.latin_letters):
                                prefix_match = re.match(r"^([>\s]+)", line)
                                prefix = prefix_match.group(1) if prefix_match else ""
                                new_lines.append(prefix + repaired)
                                changed = True
                                continue
            new_lines.append(line)
        if changed:
            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            modified += 1
    return modified
