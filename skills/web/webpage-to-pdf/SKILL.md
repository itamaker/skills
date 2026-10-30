---
name: webpage-to-pdf
description: Export a live webpage to a paginated PDF with headless Chrome, as pixel-exact screenshots or (--mode text) selectable, searchable text. Use when the user wants to save, archive, or print a URL or article as PDF, including pages behind a login.
allowed-tools: Bash, Read
argument-hint: "<url> [output.pdf] [--mode image|text|--login|--headed|--wait N|--page-size a4|letter|legal]"
---

# webpage-to-pdf

Exports a page as an A4/Letter/Legal PDF with a title/date header and a URL/page-number footer, in one of two modes:

| `--mode` | Output | Pick when |
|---|---|---|
| `image` (default) | Chrome screenshot sliced into pages; pixel-exact, text not selectable, about 1 MB per page | The page must look exactly as it does on screen |
| `text` | Chrome's print engine; vector PDF with selectable, searchable text, typically 10x or more smaller | The user will search, copy, quote or have an agent read the PDF, or wants a small archive |

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
| Selectable/searchable text, small file | `--mode text` |
| Larger type in `--mode text` | lower `--width` (e.g. `--width 900`) |

**Page requires signing in first**: `--login` opens a visible Chrome window and blocks on a terminal prompt waiting for Enter — that can't be driven through a non-interactive command. Ask the user to run it themselves, e.g. suggest they type `!webpage2pdf URL --login` so they can sign in and press Enter. For repeat visits to the same site, `--user-data-dir DIR` reuses that signed-in session headlessly afterward.

Full flag reference, ready-made recipes, and troubleshooting live in [references/REFERENCE.md](references/REFERENCE.md).

## 3. Run it

```bash
webpage2pdf <url> [-o output.pdf] [flags...]
```

Without `-o`, the output filename is derived from the URL. Done when the command exits 0 and prints `Saved: <path>`.

## 4. Report and recover

Tell the user the output path and, when the `Saved:` line gives it, the page count. If the command fails or errors, match the error text against [references/REFERENCE.md](references/REFERENCE.md)'s Troubleshooting table, apply the fix, and retry once before asking the user for guidance.
