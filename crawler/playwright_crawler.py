"""
Wuwei Data written test - Crawler (Playwright version)

Crawls the MIT Admissions blog feed (https://mitadmissions.org/blogs/)
and saves every blog teaser entry into a CSV file.

Usage:
    pip install playwright
    playwright install chromium
    python playwright_crawler.py --pages 2 --output output/mit_blogs_playwright.csv
"""

import argparse
import csv
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://mitadmissions.org/blogs/"
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

EXTRACT_JS = """
() => {
    const items = [];
    document.querySelectorAll('li.tease-feed-item article.tease').forEach(el => {
        const link = el.querySelector('a.post-tease__h__link');
        const title = el.querySelector('.post-tease__title');
        const subtitle = el.querySelector('.post-tease__subtitle');
        const authorLink = el.querySelector('.post-tease__meta-item--author a');
        const dateEl = el.querySelector('.tease__meta-item--date');
        const img = el.querySelector('img.post-tease__img');
        const mug = el.querySelector('img.post-tease__author-mug');

        items.push({
            title: title ? title.textContent.trim() : '',
            subtitle: subtitle ? subtitle.textContent.trim() : '',
            author: authorLink ? authorLink.textContent.trim() : '',
            author_url: authorLink ? authorLink.href : '',
            date: dateEl ? dateEl.textContent.trim() : '',
            url: link ? link.href : '',
            image_url: img ? img.src : '',
            avatar_url: mug ? mug.src : '',
        });
    });
    return items;
}
"""


def page_url(page_number: int) -> str:
    """The blog archive paginates as /blogs/, /blogs/page/2/, /blogs/page/3/ ..."""
    return BASE_URL if page_number <= 1 else f"{BASE_URL}page/{page_number}/"


def crawl(pages: int) -> list[dict]:
    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"),
        )
        page = context.new_page()

        for n in range(1, pages + 1):
            url = page_url(n)
            print(f"[playwright] fetching page {n}: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("li.tease-feed-item", timeout=30000)
            items = page.evaluate(EXTRACT_JS)
            print(f"[playwright]   -> {len(items)} blog entries")
            rows.extend(items)

        browser.close()
    return rows


def save_csv(rows: list[dict], output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[playwright] saved {len(rows)} rows -> {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="MIT Admissions blogs crawler (Playwright)")
    parser.add_argument("--pages", type=int, default=1, help="number of blog archive pages to crawl")
    parser.add_argument("--output", default="output/mit_blogs_playwright.csv", help="output CSV path")
    args = parser.parse_args()

    rows = crawl(args.pages)
    if not rows:
        print("[playwright] no rows crawled", file=sys.stderr)
        return 1
    save_csv(rows, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
