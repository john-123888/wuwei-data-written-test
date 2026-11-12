"""
Wuwei Data written test - Crawler (Playwright version)

Crawls the MIT Admissions blog feed (https://mitadmissions.org/blogs/)
and saves every blog entry into a CSV file with the columns required
by the written test:

    Title | Author | Comment Count | Time | Article Content | Images In Article

Steps:
    1. Visit the blog archive list page(s) to collect entry links,
       authors, dates and comment counts (rendered by Disqus JS).
    2. Visit every entry page to extract the article content and
       the images inside the article body.

Usage:
    pip install playwright
    playwright install chromium
    python playwright_crawler.py --pages 2 --output output/mit_blogs_playwright.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://mitadmissions.org/blogs/"

HEADERS = [
    "Title",
    "Author",
    "Comment Count",
    "Time",
    "Article Content",
    "Images In Article",
]

LIST_JS = """
() => {
    const items = [];
    document.querySelectorAll('li.tease-feed-item article.tease').forEach(el => {
        const link = el.querySelector('a.post-tease__h__link');
        const title = el.querySelector('.post-tease__title');
        const authorLink = el.querySelector('.post-tease__meta-item--author a');
        const dateEl = el.querySelector('.tease__meta-item--date');
        const commentsEl = el.querySelector('.tease__meta-item--comments');

        items.push({
            title: title ? title.textContent.trim() : '',
            author: authorLink ? authorLink.textContent.trim() : '',
            time: dateEl ? dateEl.textContent.trim() : '',
            url: link ? link.href : '',
            comment_count: commentsEl ? commentsEl.textContent.trim() : '',
        });
    });
    return items;
}
"""


def parse_comment_count(raw: str) -> str:
    """'6 Comments' / '6条评论' -> '6'; empty if Disqus did not render."""
    m = re.search(r"\d+", raw or "")
    return m.group(0) if m else ""


def page_url(page_number: int) -> str:
    """The blog archive paginates as /blogs/, /blogs/page/2/, ..."""
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

        # ---- Step 1: list pages ----
        entries: list[dict] = []
        for n in range(1, pages + 1):
            url = page_url(n)
            print(f"[playwright] list page {n}: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("li.tease-feed-item", timeout=30000)
            page.wait_for_timeout(4000)  # give the Disqus count script time to render
            items = page.evaluate(LIST_JS)
            print(f"[playwright]   -> {len(items)} entries")
            entries.extend(items)

        # ---- Step 2: article pages ----
        for i, e in enumerate(entries, 1):
            url = e["url"]
            if not url:
                continue
            try:
                print(f"[playwright] article {i}/{len(entries)}: {e['title']}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector(".article__body", timeout=30000)

                content = page.evaluate(
                    """() => {
                        const paras = [...document.querySelectorAll('.article__body p, .article__body li')]
                            .map(el => el.innerText.trim())
                            .filter(t => t.length > 0);
                        const imgs = [...document.querySelectorAll('.article__body img')]
                            .map(img => img.src);
                        return {content: paras.join('\\n'), images: imgs};
                    }"""
                )
                rows.append({
                    "Title": e["title"],
                    "Author": e["author"],
                    "Comment Count": parse_comment_count(e["comment_count"]),
                    "Time": e["time"],
                    "Article Content": content["content"],
                    "Images In Article": ";".join(content["images"]),
                })
            except Exception as exc:  # keep crawling even if one article fails
                print(f"[playwright]   !! failed: {exc}", file=sys.stderr)
                rows.append({
                    "Title": e["title"], "Author": e["author"],
                    "Comment Count": parse_comment_count(e["comment_count"]),
                    "Time": e["time"], "Article Content": "", "Images In Article": "",
                })

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
