# webpage-to-pdf reference

## Full flag reference

| Flag | Default | Description |
|---|---|---|
| `URL` | — | Page to export (`https://` may be omitted) |
| `OUTPUT` / `-o PATH` | derived from URL | Output PDF path |
| `--mode {image,text}` | image | `image`: pixel-exact screenshot pages. `text`: vector PDF from Chrome's print engine with selectable, searchable text |
| `--login` | off | Open a visible browser; export after sign-in + Enter |
| `--headed` | off | Show the browser window |
| `--wait SECONDS` | 3 | Extra wait after page load |
| `--no-scroll` | off | Skip the pre-capture full-page scroll |
| `--width PX` | 1400 | Layout width the page is rendered at (viewport width; in `text` mode the print scale is derived from it) |
| `--scale {1,2,3}` | 2 | Screenshot scale factor (2 = Retina); `image` mode only |
| `--page-size {a4,letter,legal}` | a4 | Paper size |
| `--title TEXT` | page `<title>` | Override the header title |
| `--no-header` | off | Skip the header band |
| `--no-footer` | off | Skip the footer band |
| `--chrome-binary PATH` | auto-detect | Path to the Chrome executable |
| `--user-data-dir DIR` | — | Chrome user-data directory (reuse logged-in sessions) |

## Recipes

**Skip login every time**
```bash
webpage2pdf URL --login --user-data-dir ~/.webpage2pdf-profile   # first run: sign in once
webpage2pdf URL --user-data-dir ~/.webpage2pdf-profile           # later runs: headless
```
Chrome refuses to share a user-data directory with a running instance — use a dedicated directory, not the daily browser profile.

**Searchable archive of an article**
```bash
webpage2pdf https://example.com/article --mode text --width 900 -o article.pdf
pdftotext article.pdf -   # the page text comes back
```

**Slow single-page app**
```bash
webpage2pdf https://app.example.com/report --wait 10
```

## How it works

Both modes start the same way:

1. Selenium launches Chrome (headless by default); Selenium Manager fetches the matching chromedriver.
2. Waits for `document.readyState === "complete"` plus `--wait` seconds, scrolls the full page to trigger lazy-loaded images, scrolls back to top.

Then `--mode image` (default):

3. Uses CDP `Page.captureScreenshot` with `captureBeyondViewport` to shoot the page in 4000px chunks at the chosen scale, then stitches them into one image.
4. Slices the image into pages matching the paper's aspect ratio, drawing header/footer bands with Pillow.
5. Writes a multi-page PDF whose embedded DPI makes each page physically A4/Letter/Legal-sized.

Or `--mode text`:

3. Emulates the `screen` media type, so the PDF shows the on-screen styles rather than print CSS.
4. Calls CDP `Page.printToPDF` with backgrounds on, 0.4in margins, and Chrome header/footer templates (title and date on top; URL and `pageNumber / totalPages` below). `--no-header` / `--no-footer` blank the matching template.
5. Sets the print `scale` to printable paper width in CSS px divided by `--width` (clamped to Chrome's 0.1-2 range), so the layout is computed at `--width` and responsive sites keep the same breakpoint as in `image` mode. A4 at the default 1400 gives scale 0.51; `--width 900` gives 0.83.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Failed to launch Chrome / cannot find Chrome" | Install Google Chrome, or pass `--chrome-binary "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` |
| Page renders blank or half-empty | Raise `--wait`, or try `--headed` — some sites serve empty shells to headless browsers |
| Site blocks the capture / shows a bot check | `--headed`, or `--login` and pass the check manually, or `--user-data-dir` with a cookied profile |
| CJK titles show as boxes (tofu) | Bundled fonts cover macOS/Linux/Windows; on minimal Linux: `sudo apt install fonts-noto-cjk` |
| `error: Chrome printToPDF failed` in `--mode text` | Rerun without `--headed`/`--login`; headed Chrome builds may not implement printToPDF. To keep a login, sign in once with `--user-data-dir DIR`, then rerun headless with the same DIR |
| Infinite-scroll feed produces an enormous PDF | Pre-capture scroll caps at ~200 steps; use `--no-scroll` to capture only what's initially loaded |

## Limitations

`--mode image`:

- Text is not selectable or searchable; pages are rasterized images.
- File sizes run larger than text-based PDFs (roughly 0.5-2MB/page at 2x; `--scale 1` for smaller files).
- Fixed/sticky elements (navbars, cookie banners) may repeat across captured chunks.
- Pages cut at fixed heights; a line of text can split across a page break.

`--mode text`:

- Layout is close to `image` mode, not identical. Both render the page at `--width`, but `text` mode keeps 0.4in page margins, shrinks everything by the print scale (type at the default `--width 1400` is about half its on-screen size; lower `--width` for larger type), and breaks pages in Chrome's print layout, which moves content that `image` mode would cut mid-line.
- Fixed/sticky elements repeat on every page; canvas and WebGL drawing, and text inside images, stay bitmaps and are not selectable.
- A site's `@media print` rules are ignored (`screen` media is emulated).
- Chrome embeds the fonts it used, so a tiny page still weighs about 100 KB.
- Header and footer text is 8px and truncated with an ellipsis when too long; the page count shown on the `Saved:` line comes from the PDF structure and is omitted if it cannot be read.
