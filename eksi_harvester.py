#!/usr/bin/env python3
"""
Playwright-based Ekşi Sözlük topic scraper.

Features:
- Headless Chromium scraping (default).
- Follows "rel=next" (next-page) links until the end.
- Optional cookie injection (single-line Cookie header or EKSI_COOKIE env var).
- Progress prints so you know scraping is continuing when many entries/pages exist.
- Output: UTF-8 JSON file with entries (no 'favorites' field).
- All comments and CLI help texts are in English.
"""

import asyncio
import json
import re
import sys
import os
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE = "https://eksisozluk.com"


def normalize_topic_url(topic: str) -> str:
    """Normalize a slug or a full URL to a canonical first-page URL with ?p=1."""
    if topic.startswith("http"):
        path = urlparse(topic).path.strip("/")
        return f"{BASE}/{path}?p=1"
    return f"{BASE}/{topic.strip().strip('/')}?p=1"


def parse_entries_from_html(html: str):
    """Parse entries from the HTML and return a list of dicts.

    Returned dict fields: entry_id, author, author_url, date, permalink, content
    """
    soup = BeautifulSoup(html, "html.parser")
    out = []
    nodes = soup.select("li[data-id]") or soup.select("li[class*=stream-item]")
    for li in nodes:
        entry_id = li.get("data-id") or ""

        content_el = li.select_one(".content") or li.select_one(".entry-content")
        content = content_el.get_text("\n", strip=True) if content_el else ""

        author_el = li.select_one("a.entry-author") or li.select_one("a[data-author]")
        author = author_el.get_text(strip=True) if author_el else ""
        if author_el and author_el.get("href", "").startswith("/"):
            author_url = BASE + author_el["href"]
        else:
            author_url = (author_el.get("href") if author_el else "")

        date_el = li.select_one("a.entry-date") or li.select_one("a.permalink")
        date_text = date_el.get_text(strip=True) if date_el else ""
        if date_el and date_el.get("href", "").startswith("/"):
            permalink = BASE + date_el["href"]
        else:
            permalink = (date_el.get("href") if date_el else "")

        out.append(
            {
                "entry_id": entry_id,
                "author": author,
                "author_url": author_url,
                "date": date_text,
                "permalink": permalink,
                "content": content,
            }
        )
    return out


def get_next_page_url_from_html(html: str, current_url: str) -> str | None:
    """Return the absolute URL of the next page (rel='next') or None if not found."""
    soup = BeautifulSoup(html, "html.parser")
    a = soup.select_one('a[rel="next"]') or soup.select_one("div.pager a.next")
    if a and a.get("href"):
        return urljoin(current_url, a["href"])
    return None


def cookie_header_to_list(cookie_header: str):
    """Convert a 'name=value; a=b; c=d' cookie header to Playwright cookie list."""
    cookies = []
    for part in cookie_header.split(";"):
        if "=" in part:
            name, value = part.strip().split("=", 1)
            cookies.append(
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": "eksisozluk.com",
                    "path": "/",
                }
            )
    return cookies


async def scrape(
    topic: str,
    output: str,
    max_pages: int | None = None,
    delay_ms: int = 1200,
    cookie_header: str | None = None,
    headless: bool = True,
):
    """Main scraping coroutine.

    - topic: slug or full topic URL
    - output: path to JSON output file
    - max_pages: optional upper bound on visited pages
    - delay_ms: wait between page navigations (milliseconds)
    - cookie_header: optional single-line Cookie header string
    - headless: run browser in headless mode if True
    """
    start_url = normalize_topic_url(topic)
    print(f"Starting scraper for: {start_url}")
    print(f"Headless: {headless}   Delay between pages: {delay_ms} ms")
    if cookie_header:
        print("Cookie header provided: cookies will be injected into the browser context.")
    else:
        print("No cookie header provided: public pages only.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="tr-TR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 800},
        )

        # Inject cookies into the browser context if provided
        if cookie_header:
            try:
                cookie_list = cookie_header_to_list(cookie_header)
                await context.add_cookies(cookie_list)
            except Exception as exc:
                print(f"Warning: failed to add cookies to context: {exc}", file=sys.stderr)

        page = await context.new_page()

        # Use a sensible referer for the first navigation
        await page.set_extra_http_headers({"Referer": BASE + "/"})
        await page.goto(start_url, wait_until="domcontentloaded")
        # short wait to allow JS protections to settle (if any)
        await page.wait_for_timeout(800)

        all_entries = []
        seen_ids = set()
        pages_visited = 0
        current_url = start_url

        print("Scraping pages... (progress will be printed below)")

        while True:
            # Print progress: which page we are visiting
            pages_visited += 1
            print(f"[page {pages_visited}] Visiting: {current_url}", flush=True)

            html = await page.content()
            entries = parse_entries_from_html(html)

            # De-duplicate by entry_id and count newly found entries
            new_count = 0
            for e in entries:
                eid = e.get("entry_id")
                if eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    all_entries.append(e)
                    new_count += 1

            print(
                f"[page {pages_visited}] Found {len(entries)} raw entries, {new_count} new -> total {len(all_entries)}",
                flush=True,
            )

            # Respect optional max_pages cap
            if max_pages and pages_visited >= max_pages:
                print(f"Reached max_pages limit ({max_pages}). Stopping.", flush=True)
                break

            # Find next page URL via rel=next or pager "next" link
            next_url = get_next_page_url_from_html(html, current_url)
            if not next_url:
                print("No next page found. Reached the end.", flush=True)
                break

            # Navigate to next page with referer set to current page
            await page.set_extra_http_headers({"Referer": current_url})
            await page.goto(next_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(delay_ms)
            current_url = next_url

        # Write results to output file
        try:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(all_entries, f, ensure_ascii=False, indent=2)
            print(f"Scraping finished. {len(all_entries)} entries saved -> {output}")
        except Exception as exc:
            print(f"Error writing output file: {exc}", file=sys.stderr)

        await browser.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Eksisozluk topic scraper (Playwright).")
    parser.add_argument("topic", help="Topic slug or full topic URL (e.g. 'python--12345' or the full URL).")
    parser.add_argument("-o", "--output", default="entries.json", help="Output JSON filename.")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional maximum number of pages to visit.")
    parser.add_argument("--delay", type=int, default=1200, help="Delay between page navigations in milliseconds (default: 1200).")
    parser.add_argument("--cookie", type=str, default=None, help="Optional Cookie header (single-line) or set EKSI_COOKIE env var.")
    parser.add_argument("--no-headless", action="store_true", help="Run with visible browser window (default is headless).")
    args = parser.parse_args()

    cookie_header = args.cookie or os.environ.get("EKSI_COOKIE")
    headless_mode = not args.no_headless  # default: headless True

    asyncio.run(
        scrape(
            topic=args.topic,
            output=args.output,
            max_pages=args.max_pages,
            delay_ms=args.delay,
            cookie_header=cookie_header,
            headless=headless_mode,
        )
    )
