"""Command-line interface for webpage2pdf."""

import argparse
import datetime
import re
import sys
from urllib.parse import urlparse

from . import __version__
from .core import (
    PAGE_SIZES,
    capture_full_page,
    launch_browser,
    log,
    paginate,
    save_pdf,
    trigger_lazy_load,
    wait_for_page,
)


def default_output(url):
    """Derive a filesystem-friendly filename from the URL."""
    parsed = urlparse(url)
    slug = parsed.netloc.replace(".", "-")
    if parsed.path.strip("/"):
        slug += "_" + parsed.path.strip("/").replace("/", "_")
    slug = re.sub(r"[^\w\-.]", "_", slug)[:120]
    return f"{slug or 'page'}.pdf"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="webpage2pdf",
        description="Export a web page as a pixel-perfect paginated PDF "
                    "(Chrome screenshot based), with automatic headers and "
                    "footers showing title, date, URL and page numbers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", help="page to export (the https:// prefix may be omitted)")
    parser.add_argument("output", nargs="?", default=None,
                        help="output PDF path (derived from the URL by default)")
    parser.add_argument("-o", "--output", dest="output_opt", metavar="PATH",
                        help="output PDF path, same as the second positional argument")
    parser.add_argument("--login", action="store_true",
                        help="open a visible browser window; sign in, then press "
                             "Enter in the terminal to start the export")
    parser.add_argument("--headed", action="store_true",
                        help="show the browser window (headless by default; some "
                             "bot-hostile sites need this)")
    parser.add_argument("--wait", type=float, default=3.0, metavar="SECONDS",
                        help="extra wait after the page finishes loading")
    parser.add_argument("--no-scroll", action="store_true",
                        help="skip the pre-capture full-page scroll (the scroll "
                             "triggers lazy-loaded images)")
    parser.add_argument("--width", type=int, default=1400, metavar="PX",
                        help="browser viewport width")
    parser.add_argument("--scale", type=int, default=2, choices=[1, 2, 3],
                        help="screenshot scale factor (2 = Retina)")
    parser.add_argument("--page-size", default="a4", choices=sorted(PAGE_SIZES),
                        help="paper size")
    parser.add_argument("--title", default=None,
                        help="override the header title (defaults to the page <title>)")
    parser.add_argument("--no-header", action="store_true", help="skip the header band")
    parser.add_argument("--no-footer", action="store_true", help="skip the footer band")
    parser.add_argument("--chrome-binary", default=None, metavar="PATH",
                        help="path to the Chrome executable (auto-detected by default)")
    parser.add_argument("--user-data-dir", default=None, metavar="DIR",
                        help="Chrome user-data directory, reuses logged-in sessions")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    url = args.url
    if "://" not in url:
        url = "https://" + url
    out_path = args.output_opt or args.output or default_output(url)
    headless = not (args.login or args.headed)

    log(f"Launching Chrome ({'headless' if headless else 'headed'})...")
    try:
        driver = launch_browser(
            width=args.width,
            headless=headless,
            chrome_binary=args.chrome_binary,
            user_data_dir=args.user_data_dir,
        )
    except Exception as e:
        log(f"error: failed to launch Chrome: {e}")
        log("Make sure Google Chrome is installed, or point at it with --chrome-binary.")
        return 1

    try:
        log(f"Opening: {url}")
        driver.get(url)

        if args.login:
            print("Sign in in the Chrome window, then press Enter here to continue...")
            input()
        wait_for_page(driver, extra_wait=args.wait)

        if not args.no_scroll:
            log("Scrolling to trigger lazy loading...")
            trigger_lazy_load(driver)

        title = args.title or driver.title or url
        log(f"  title: {title}")

        full_img = capture_full_page(driver, width=args.width, scale=args.scale)
        pages = paginate(
            full_img,
            title=title,
            url=url,
            date_str=datetime.date.today().strftime("%Y/%m/%d"),
            page_size=args.page_size,
            with_header=not args.no_header,
            with_footer=not args.no_footer,
        )
        save_pdf(pages, out_path, page_size=args.page_size)
        log(f"Saved: {out_path} ({len(pages)} pages)")
        return 0
    except KeyboardInterrupt:
        log("Cancelled")
        return 130
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
