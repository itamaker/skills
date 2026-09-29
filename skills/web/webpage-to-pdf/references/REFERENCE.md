# webpage-to-pdf reference

## Full flag reference

| Flag | Default | Description |
|---|---|---|
| `URL` | — | Page to export (`https://` may be omitted) |
| `OUTPUT` / `-o PATH` | derived from URL | Output PDF path |
| `--login` | off | Open a visible browser; export after sign-in + Enter |
| `--headed` | off | Show the browser window |
| `--wait SECONDS` | 3 | Extra wait after page load |
| `--no-scroll` | off | Skip the pre-capture full-page scroll |
| `--width PX` | 1400 | Browser viewport width |
| `--scale {1,2,3}` | 2 | Screenshot scale factor (2 = Retina) |
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

**Slow single-page app**
```bash
webpage2pdf https://app.example.com/report --wait 10
```

## How it works

1. Selenium launches Chrome (headless by default); Selenium Manager fetches the matching chromedriver.
2. Waits for `document.readyState === "complete"` plus `--wait` seconds, scrolls the full page to trigger lazy-loaded images, scrolls back to top.
3. Uses CDP `Page.captureScreenshot` with `captureBeyondViewport` to shoot the page in 4000px chunks at the chosen scale, then stitches them into one image.
4. Slices the image into pages matching the paper's aspect ratio, drawing header/footer bands with Pillow.
5. Writes a multi-page PDF whose embedded DPI makes each page physically A4/Letter/Legal-sized.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Failed to launch Chrome / cannot find Chrome" | Install Google Chrome, or pass `--chrome-binary "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` |
| Page renders blank or half-empty | Raise `--wait`, or try `--headed` — some sites serve empty shells to headless browsers |
| Site blocks the capture / shows a bot check | `--headed`, or `--login` and pass the check manually, or `--user-data-dir` with a cookied profile |
| CJK titles show as boxes (tofu) | Bundled fonts cover macOS/Linux/Windows; on minimal Linux: `sudo apt install fonts-noto-cjk` |
| Infinite-scroll feed produces an enormous PDF | Pre-capture scroll caps at ~200 steps; use `--no-scroll` to capture only what's initially loaded |

## Limitations

- Text is not selectable or searchable — pages are rasterized images.
- File sizes run larger than text-based PDFs (roughly 0.5-2MB/page at 2x; `--scale 1` for smaller files).
- Fixed/sticky elements (navbars, cookie banners) may repeat across captured chunks.
- Pages cut at fixed heights; a line of text can split across a page break.
