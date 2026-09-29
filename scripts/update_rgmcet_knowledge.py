"""Fetch only approved RGMCET pages into reviewable knowledge snapshots.

Snapshots are unverified by default. Use --approve-reviewed-content only after
checking the extracted text against the official page and updating the curated
department/faculty/facility JSON records used by the chat retrieval service.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "rgmcet_knowledge" / "source_snapshots.json"
OFFICIAL_HOST = "www.rgmcet.edu.in"
APPROVED_SOURCES = {
    "homepage": "https://www.rgmcet.edu.in/",
    "about": "https://www.rgmcet.edu.in/about-us",
    "contact": "https://www.rgmcet.edu.in/contact.php",
    "cseds": "https://www.rgmcet.edu.in/department-of-cseds.php",
    "cseds_faculty": "https://www.rgmcet.edu.in/cseds_faculty1.php",
    "cseds_program": "https://www.rgmcet.edu.in/cseds_dp.php",
    "cse": "https://www.rgmcet.edu.in/department-of-cse.php",
    "aiml": "https://www.rgmcet.edu.in/department-of-aiml.php",
    "cyber_security": "https://www.rgmcet.edu.in/department-of-csecs.php",
    "csbs": "https://www.rgmcet.edu.in/department-of-csbs.php",
    "it": "https://www.rgmcet.edu.in/department-of-it.php",
    "ece": "https://www.rgmcet.edu.in/department-of-ece.php",
    "eee": "https://www.rgmcet.edu.in/department-of-eee.php",
    "civil": "https://www.rgmcet.edu.in/department-of-ce.php",
    "mechanical": "https://www.rgmcet.edu.in/department-of-me.php",
    "mba": "https://www.rgmcet.edu.in/department-of-mba.php",
    "mca": "https://www.rgmcet.edu.in/department-of-mca.php",
    "facilities": "https://www.rgmcet.edu.in/campus%20facilities",
    "library": "https://www.rgmcet.edu.in/library",
}


class VisibleText(HTMLParser):
    ignored = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.ignored:
            self._ignored_depth += 1
        elif tag in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def normalize_html(html: str) -> str:
    parser = VisibleText()
    parser.feed(html)
    lines = [re.sub(r"\s+", " ", line).strip() for line in " ".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def approved_url(page_id: str) -> str:
    if page_id not in APPROVED_SOURCES:
        raise ValueError(f"Page id is not in the approved RGMCET source list: {page_id}")
    url = APPROVED_SOURCES[page_id]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise ValueError("Approved source URL must use official HTTPS RGMCET host")
    return url


async def fetch_snapshot(client: httpx.AsyncClient, page_id: str, verified: bool) -> dict:
    url = approved_url(page_id)
    response = await client.get(url)
    response.raise_for_status()
    if response.url.scheme != "https" or response.url.host != OFFICIAL_HOST:
        raise ValueError(f"Unexpected redirect host while fetching approved page id {page_id}")
    content = normalize_html(response.text)
    return {
        "kind": "official_page_snapshot",
        "title": page_id.replace("_", " ").title(),
        "content": content[:30000],
        "source": url,
        "verified": verified,
        "last_checked": date.today().isoformat(),
    }


async def update(page_ids: list[str], approve_reviewed_content: bool = False) -> list[dict]:
    for page_id in page_ids:
        approved_url(page_id)
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        return [
            await fetch_snapshot(client, page_id, approve_reviewed_content)
            for page_id in page_ids
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        nargs="+",
        choices=sorted(APPROVED_SOURCES),
        default=["homepage", "about", "contact", "cseds", "cseds_faculty", "cseds_program", "facilities", "library"],
        help="Approved RGMCET page ids only.",
    )
    parser.add_argument(
        "--approve-reviewed-content",
        action="store_true",
        help="Mark snapshots verified only after an operator has reviewed their extracted content.",
    )
    args = parser.parse_args()
    snapshots = asyncio.run(update(args.pages, args.approve_reviewed_content))
    OUTPUT.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(snapshots)} official RGMCET page snapshots to {OUTPUT}")
    print("Snapshots are verified=" + str(args.approve_reviewed_content))


if __name__ == "__main__":
    main()