#!/usr/bin/env python3
"""
Scrape Dementia UK Nationwide clinic addresses from the HTML page
and output them to a CSV file with the postcode separated.
"""

import csv
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request


def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.dementiauk.org/",
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def extract_clinics(html: str) -> list[dict]:
    # First decode HTML entities so date separators are uniform
    html = html.replace("&#8211;", "–").replace("&#8212;", "—").replace("&amp;", "&")

    # Each clinic is an <li> with a booking link, format:
    # <li><a href="...">Town, Street Address POSTCODE</a> — dates</li>
    # Links may be simplybook.cc or outlook booking pages
    pattern = (
        r'<li><a\s+href="([^"]*)"[^>]*>'
        r'([^<]*[A-Z]{1,2}\d[A-Z\d]?\s+\d[A-Z]{2}[^<]*)'
        r'</a>\s*[—–\-]+\s*([^<]+)</li>'
    )
    matches = re.findall(pattern, html)

    uk_postcode_re = re.compile(r'([A-Z]{1,2}\d[A-Z\d]?\s+\d[A-Z]{2})$')

    clinics = []
    for booking_url, location_text, dates in matches:
        location_text = location_text.strip()
        dates = dates.strip()

        m = uk_postcode_re.search(location_text)
        if m:
            postcode = m.group(1).strip()
            address_part = location_text[: m.start()].strip().rstrip(",").strip()
        else:
            postcode = ""
            address_part = location_text

        # Split "Town, Street Address" into town and street
        parts = address_part.split(",", 1)
        town = parts[0].strip()
        street = parts[1].strip() if len(parts) > 1 else ""

        clinics.append({
            "town": town,
            "street_address": street,
            "postcode": postcode,
            "full_address": location_text,
            "clinic_dates": dates,
            "booking_url": booking_url,
        })

    return clinics


def deduplicate_clinics(clinics: list[dict]) -> list[dict]:
    unique_clinics = []
    seen = set()
    duplicates = 0

    for clinic in clinics:
        row_key = tuple(sorted(clinic.items()))
        if row_key in seen:
            duplicates += 1
            continue
        seen.add(row_key)
        unique_clinics.append(clinic)

    if duplicates:
        print(f"Removed {duplicates} duplicate clinic entr{'y' if duplicates == 1 else 'ies'}.")

    return unique_clinics


def main():
    url = (
        "https://www.dementiauk.org/information-and-support/"
        "how-we-can-support-you/admiral-nurse-clinics/nationwide/"
    )

    print(f"Fetching page: {url}")
    html = fetch_page(url)
    print(f"Page fetched ({len(html):,} chars)")

    clinics = extract_clinics(html)
    print(f"Found {len(clinics)} clinic locations\n")

    clinics = deduplicate_clinics(clinics)

    if not clinics:
        print("No clinics found – the page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    # Write CSV to data folder
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "dementia_uk_clinic_locations.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["town", "street_address", "postcode", "full_address", "clinic_dates", "booking_url"],
        )
        writer.writeheader()
        writer.writerows(clinics)

    print(f"Written to: {output_path}")

    # Preview first 10
    print(f"\n{'#':<4} {'Town':<22} {'Street Address':<35} {'Postcode':<10} {'Dates'}")
    print("-" * 110)
    for i, c in enumerate(clinics[:15], 1):
        print(f"{i:<4} {c['town']:<22} {c['street_address']:<35} {c['postcode']:<10} {c['clinic_dates']}")
    if len(clinics) > 15:
        print(f"... and {len(clinics) - 15} more (see CSV)")


if __name__ == "__main__":
    main()
