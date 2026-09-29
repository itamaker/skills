---
name: webpage-to-pdf
description: Export a live webpage to a pixel-perfect, paginated PDF via headless Chrome screenshots (what is on screen, not print CSS). Use when the user wants to save, archive, or print a URL or article as PDF, including pages behind a login. Not for editing or extracting text from existing PDFs.
allowed-tools: Bash, Read
argument-hint: "<url> [output.pdf] [--login|--headed|--wait N|--page-size a4|letter|legal]"
---

# webpage-to-pdf

Captures a page exactly as Chrome renders it — not through the print pipeline — then paginates the screenshot into an A4/Letter/Legal PDF with a title/date header and a URL/page-number footer. Output is a WYSIWYG image-based PDF: text is not selectable. If the user needs selectable/searchable text, this is the wrong tool — point them at Chrome's own Print to PDF instead.

This skill is self-contained: the CLI's source ships inside this skill folder, so it works with nothing else installed beyond Google Chrome and the two Python dependencies below.

## 1. Confirm the CLI is available

Run `webpage2pdf --version`. If the command is not found, install this skill's bundled copy from this skill's own directory (the folder containing this `SKILL.md`):

```bash
python3 -m pip install -e /absolute/path/to/this/skill/directory
```

Requires Google Chrome; Selenium Manager fetches the matching chromedriver automatically. Done when `webpage2pdf --version` prints a version.

## 2. Pick the flags for the situation

| Situation | Flags |
|---|---|
| Plain page | none — just the URL |
| Slow / JS-heavy / single-page app | `--wait 8` (raise from the 3s default) |
| Bot-check or blocked headless | `--headed`, or `--user-data-dir DIR` with a signed-in profile |
| Infinite-scroll feed ballooning in size | `--no-scroll` |
| US Letter / Legal paper | `--page-size letter` / `--page-size legal` |
| Clean pages, no header/footer | `--no-header --no-footer` |
| Narrow / mobile layout | `--width 800` |
| Selectable/searchable text needed | wrong tool — use Chrome's Print to PDF |

**Page requires signing in first**: `--login` opens a visible Chrome window and blocks on a terminal prompt waiting for Enter — that can't be driven through a non-interactive command. Ask the user to run it themselves, e.g. suggest they type `!webpage2pdf URL --login` so they can sign in and press Enter. For repeat visits to the same site, `--user-data-dir DIR` reuses that signed-in session headlessly afterward.

Full flag reference, ready-made recipes, and troubleshooting live in [references/REFERENCE.md](references/REFERENCE.md).

## 3. Run it

```bash
webpage2pdf <url> [-o output.pdf] [flags...]
```

Without `-o`, the output filename is derived from the URL. Done when the command exits 0 and prints `Saved: <path> (<N> pages)`.

## 4. Report and recover

Tell the user the output path and page count. If the command fails or errors, match the error text against [references/REFERENCE.md](references/REFERENCE.md)'s Troubleshooting table, apply the fix, and retry once before asking the user for guidance.
