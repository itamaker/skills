"""Validate per-role lessons files in references/lessons/.

Each file starts with a YAML frontmatter block listing its lessons, in
the same order as the body:

    ---
    lessons:
      - id: pm-001
        added: 2026-11-22
        status: active
    ---

The checker enforces: required fields present (`id`, `added`,
`status`), valid `status` values (`active` | `retired`), retired
entries carry a `retired` date and a `retired_reason`, ids unique per
file and matching the `## [id] Title` body sections, and the general-
only rule (no project names, repo paths, commit hashes, version
numbers, or product identifiers anywhere in the file). An empty
`lessons:` list is valid: a role with no recorded lessons yet.

The frontmatter is parsed by the small strict parser below, not by
PyYAML: the schema is fixed (a `lessons:` list of flat scalar pairs),
and this skill's scripts stay standard-library only. Anything outside
that shape is a parse error, not a silent pass.

The general-only check is a heuristic, not a guarantee: the patterns
catch the common shapes of project-specific identifiers (absolute
paths, commit-hash-like hex, version-number-like strings).
Project/product names are checked via --ban NAME (repeatable). No name
is hardcoded here: hardcoding one project's product name into the
shared skill would itself be a project-specific identifier.

Usage: python3 scripts/check_lessons.py [--ban NAME ...] [directory]
"""

import argparse
from datetime import date
import re
import sys
from pathlib import Path

LESSONS_DIR = Path(__file__).resolve().parents[1] / "references" / "lessons"
FIELDS = ("Trigger", "Pattern", "Do instead", "Why")
FIELD_RE = re.compile(r"^-\s*(Trigger|Pattern|Do instead|Why):\s*(.+?)\s*$")
SECTION_RE = re.compile(r"^## \[([A-Za-z0-9-]+)\](?:\s+(.+?))?\s*$")
ITEM_RE = re.compile(r"^  - (\w+):\s*(.*?)\s*$")
KEY_RE = re.compile(r"^    (\w+):\s*(.*?)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_KEYS = ("id", "added", "status")
ALLOWED_KEYS = REQUIRED_KEYS + ("retired", "retired_reason")
BANNED_PATTERNS = [
    ("absolute path", r"/(?:home|Users|var|opt|tmp|workspace|etc)/"),
    ("home path", r"~/\S"),
    ("windows path", r"[A-Za-z]:\\"),
    ("commit-hash-like hex", r"\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"),
    ("version-number-like", r"\bv?\d+\.\d+\.\d+\b"),
    ("build-number-like", r"\bbuild\s+\d{3,}\b"),
]


def find_banned(text, extra_names=()):
    """Return [(label, match)] for banned identifiers in text."""
    hits = [(label, m.group(0)) for label, pat in BANNED_PATTERNS
            for m in re.finditer(pat, text)]
    hits += [("name", m.group(0)) for name in extra_names
             for m in re.finditer(r"\b" + re.escape(name) + r"\b", text, re.I)]
    return hits


def parse_frontmatter(lines):
    """Parse the restricted frontmatter schema.

    Return (lessons, errors): lessons is a list of dicts, errors a list
    of strings. Any line outside the expected shape is an error, and
    on error the returned list is empty so callers do not cascade.
    """
    errors, lessons, current = [], [], None
    if lines == ["lessons: []"]:
        return [], []
    if not lines or lines[0] != "lessons:":
        return [], ["frontmatter must start with a 'lessons:' list"]
    for line in lines[1:]:
        item = ITEM_RE.match(line)
        key = KEY_RE.match(line)
        if item:
            current = {}
            lessons.append(current)
            key, value = item.group(1), item.group(2)
        elif key and current is not None:
            key, value = key.group(1), key.group(2)
        else:
            return [], [f"frontmatter: cannot parse line: {line!r}"]
        if key not in ALLOWED_KEYS:
            return [], [f"frontmatter: unknown key: {key!r}"]
        if key in current:
            return [], [f"frontmatter: duplicate key: {key!r}"]
        if not value or value[0] in "[{":
            return [], [f"frontmatter: bad value for {key}: {value!r}"]
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        current[key] = value
    return lessons, errors


def valid_date(value):
    if not DATE_RE.match(value or ""):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def check_file(path, extra_names=()):
    """Return (errors, entry_count) for one lessons file."""
    path = Path(path)
    errors, text = [], path.read_text(encoding="utf-8")
    errors += [f"{path}: banned {label}: {match!r}"
               for label, match in find_banned(text, extra_names)]
    lines = text.splitlines()
    if len(lines) < 2 or lines[0] != "---" or "---" not in lines[1:]:
        return errors + [f"{path}: missing YAML frontmatter block"], 0
    end = lines[1:].index("---") + 1
    lessons, parse_errors = parse_frontmatter(lines[1:end])
    errors += [f"{path}: {error}" for error in parse_errors]
    sections, current = [], None
    for line in lines[end + 1:]:
        section = SECTION_RE.match(line)
        if section:
            current = {"id": section.group(1), "title": section.group(2) or "", "lines": []}
            sections.append(current)
        elif line.startswith("## "):
            errors.append(f"{path}: unexpected heading: {line!r}")
        elif current is not None and line.strip():
            current["lines"].append(line)
    if parse_errors:
        return errors, 0
    prefix = "".join(part[0] for part in path.stem.split("-"))
    seen_ids = []
    for lesson in lessons:
        where = f"{path} [{lesson.get('id', '?')}]"
        for key in REQUIRED_KEYS:
            if key not in lesson:
                errors.append(f"{where}: missing {key}")
        if "id" in lesson:
            if lesson["id"] in seen_ids:
                errors.append(f"{where}: duplicate id")
            seen_ids.append(lesson["id"])
            if not re.fullmatch(rf"{prefix}-\d{{3}}", lesson["id"]):
                errors.append(f"{where}: id must look like {prefix}-NNN")
        if "added" in lesson and not valid_date(lesson["added"]):
            errors.append(f"{where}: added is not a YYYY-MM-DD date: {lesson['added']!r}")
        status = lesson.get("status")
        if status and status not in ("active", "retired"):
            errors.append(f"{where}: status must be active or retired: {status!r}")
        if status == "retired":
            if "retired" not in lesson:
                errors.append(f"{where}: retired entry needs a retired date")
            elif not valid_date(lesson["retired"]):
                errors.append(f"{where}: retired is not a YYYY-MM-DD date: {lesson['retired']!r}")
            elif lesson["retired"] < lesson.get("added", ""):
                errors.append(f"{where}: retired date is before added date")
            if len(lesson.get("retired_reason", "").strip()) < 10:
                errors.append(f"{where}: retired entry needs a retired_reason")
        elif status == "active":
            for key in ("retired", "retired_reason"):
                if key in lesson:
                    errors.append(f"{where}: active entry must not carry {key}")
    if [lesson.get("id") for lesson in lessons] != [s["id"] for s in sections]:
        errors.append(f"{path}: frontmatter ids do not match body sections in order")
    for section in sections:
        where = f"{path} [{section['id']}]"
        if not section["title"]:
            errors.append(f"{where}: empty title")
        seen = []
        for line in section["lines"]:
            match = FIELD_RE.match(line)
            if match:
                expected = FIELDS[len(seen)] if len(seen) < 4 else None
                if match.group(1) == expected:
                    seen.append(match.group(1))
                else:
                    errors.append(f"{where}: expected {expected or 'no more fields'}, got {line!r}")
            else:
                errors.append(f"{where}: unexpected line: {line!r}")
        errors += [f"{where}: missing {field} line" for field in FIELDS[len(seen):]]
    return errors, len(sections)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate lessons files.")
    parser.add_argument("--ban", action="append", default=[],
                        help="extra banned project/product name (repeatable)")
    parser.add_argument("directory", nargs="?", default=str(LESSONS_DIR))
    args = parser.parse_args(argv)
    errors, total, files = [], 0, sorted(Path(args.directory).glob("*.md"))
    if not files:
        print(f"{args.directory}: no lessons files found", file=sys.stderr)
        return 1
    for path in files:
        file_errors, count = check_file(path, args.ban)
        errors += file_errors
        total += count
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {total} lessons in {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
