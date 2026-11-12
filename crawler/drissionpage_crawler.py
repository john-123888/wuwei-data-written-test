"""
Wuwei Data written test - Crawler (DrissionPage version)

Crawls the MIT Admissions blog feed (https://mitadmissions.org/blogs/)
and saves every blog teaser entry into a CSV file.

Usage:
    pip install DrissionPage
    python drissionpage_crawler.py --pages 2 --output output/mit_blogs_drissionpage.csv
"""

import argparse
import csv
import shutil
import sys
from pathlib import Path

from DrissionPage import ChromiumPage, ChromiumOptions

BASE_URL = "https://mitadmissions.org/blogs/"

# Candidate Chromium-based browsers (checked in order)
BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

HEADERS = [
    "title",
    "subtitle",
    "author",
    "author_url",
    "date",
    "url",
    "image_url",
    "avatar_url",
]


def page_url(page_number: int) -> str:
    """The blog archive paginates as /blogs/, /blogs/page/2/, /blogs/page/3/ ..."""
    return BASE_URL if page_number <= 1 else f"{BASE_URL}page/{page_number}/"


def find_browser() -> str:
    """Return the first existing Chrome/Edge executable, or '' if none found."""
    for candidate in BROWSER_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in ("chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    return ""


def crawl(pages: int) -> list[dict]:
    rows: list[dict] = []

    co = ChromiumOptions()
    co.headless()
    co.auto_port()
    co.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    browser_path = find_browser()
    if browser_path:
        co.set_browser_path(browser_path)
        print(f"[drissionpage] using browser: {browser_path}")
    else:
        print("[drissionpage] no local Chrome/Edge found, using DrissionPage default")

    page = ChromiumPage(co)
    # Keep per-element waits short so missing fields (no image, no subtitle, ...)
    # do not stall the crawl for 10s each time (DrissionPage default).
    page.set.timeouts(base=2, page_load=60, script=10)
    try:
        for n in range(1, pages + 1):
            url = page_url(n)
            print(f"[drissionpage] fetching page {n}: {url}")
            page.get(url)
            page.wait.ele_displayed("css:li.tease-feed-item", timeout=30)

            items = page.eles("css:li.tease-feed-item article.tease")
            print(f"[drissionpage]   -> {len(items)} blog entries")

            for item in items:
                link = item.ele("css:a.post-tease__h__link")
                title = item.ele("css:.post-tease__title")
                subtitle = item.ele("css:.post-tease__subtitle")
                author_link = item.ele("css:.post-tease__meta-item--author a")
                date_el = item.ele("css:.tease__meta-item--date")
                img = item.ele("css:img.post-tease__img")
                mug = item.ele("css:img.post-tease__author-mug")

                rows.append({
                    "title": title.text.strip() if title else "",
                    "subtitle": subtitle.text.strip() if subtitle else "",
                    "author": author_link.text.strip() if author_link else "",
                    "author_url": author_link.attr("href") if author_link else "",
                    "date": date_el.text.strip() if date_el else "",
                    "url": link.attr("href") if link else "",
                    "image_url": img.attr("src") if img else "",
                    "avatar_url": mug.attr("src") if mug else "",
                })
    finally:
        page.quit()

    return rows


def save_csv(rows: list[dict], output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[drissionpage] saved {len(rows)} rows -> {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="MIT Admissions blogs crawler (DrissionPage)")
    parser.add_argument("--pages", type=int, default=1, help="number of blog archive pages to crawl")
    parser.add_argument("--output", default="output/mit_blogs_drissionpage.csv", help="output CSV path")
    args = parser.parse_args()

    rows = crawl(args.pages)
    if not rows:
        print("[drissionpage] no rows crawled", file=sys.stderr)
        return 1
    save_csv(rows, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
