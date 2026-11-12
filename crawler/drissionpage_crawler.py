"""
Wuwei Data written test - Crawler (DrissionPage version)

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
    pip install DrissionPage
    python drissionpage_crawler.py --pages 2 --output output/mit_blogs_drissionpage.csv
"""

import argparse
import csv
import re
import shutil
import sys
import time
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
    "Title",
    "Author",
    "Comment Count",
    "Time",
    "Article Content",
    "Images In Article",
]


def parse_comment_count(raw: str) -> str:
    """'6 Comments' / '6条评论' -> '6'; empty if Disqus did not render."""
    m = re.search(r"\d+", raw or "")
    return m.group(0) if m else ""


def page_url(page_number: int) -> str:
    """The blog archive paginates as /blogs/, /blogs/page/2/, ..."""
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
    # Keep per-element waits short so missing fields do not stall the crawl
    page.set.timeouts(base=2, page_load=60, script=10)
    try:
        # ---- Step 1: list pages ----
        entries: list[dict] = []
        for n in range(1, pages + 1):
            url = page_url(n)
            print(f"[drissionpage] list page {n}: {url}")
            page.get(url)
            page.wait.ele_displayed("css:li.tease-feed-item", timeout=30)
            time.sleep(4)  # give the Disqus count script time to render

            items = page.eles("css:li.tease-feed-item article.tease")
            print(f"[drissionpage]   -> {len(items)} entries")
            for item in items:
                link = item.ele("css:a.post-tease__h__link")
                title = item.ele("css:.post-tease__title")
                author_link = item.ele("css:.post-tease__meta-item--author a")
                date_el = item.ele("css:.tease__meta-item--date")
                comments_el = item.ele("css:.tease__meta-item--comments")

                entries.append({
                    "title": title.text.strip() if title else "",
                    "author": author_link.text.strip() if author_link else "",
                    "time": date_el.text.strip() if date_el else "",
                    "url": link.attr("href") if link else "",
                    "comment_count": comments_el.text.strip() if comments_el else "",
                })

        # ---- Step 2: article pages ----
        for i, e in enumerate(entries, 1):
            url = e["url"]
            if not url:
                continue
            try:
                print(f"[drissionpage] article {i}/{len(entries)}: {e['title']}")
                page.get(url)
                page.wait.ele_displayed("css:.article__body", timeout=30)

                paras = page.eles("css:.article__body p, .article__body li")
                content = "\n".join(
                    p.text.strip() for p in paras if p.text.strip()
                )
                imgs = page.eles("css:.article__body img")
                images = ";".join(filter(None, (img.attr("src") for img in imgs)))

                rows.append({
                    "Title": e["title"],
                    "Author": e["author"],
                    "Comment Count": parse_comment_count(e["comment_count"]),
                    "Time": e["time"],
                    "Article Content": content,
                    "Images In Article": images,
                })
            except Exception as exc:  # keep crawling even if one article fails
                print(f"[drissionpage]   !! failed: {exc}", file=sys.stderr)
                rows.append({
                    "Title": e["title"], "Author": e["author"],
                    "Comment Count": parse_comment_count(e["comment_count"]),
                    "Time": e["time"], "Article Content": "", "Images In Article": "",
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
