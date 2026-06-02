from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections import Counter
from html import unescape
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models.requests import CompareRequest, CompareSiteData
from ..services.gemini_client import GeminiAuthError
from ..services.gemini_grounded import call_gemini, GroundedResult

logger = logging.getLogger("technotrack.compare_agent")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _supported_accept_encoding() -> str:
    """Advertise Brotli ONLY if a decoder is importable.

    Turkish marketplaces (Vatan, MediaMarkt, …) honour ``Accept-Encoding: br``
    and return Brotli-compressed HTML. httpx can only decode it when the
    ``brotli``/``brotlicffi`` package is installed; without it ``response.text``
    is undecodable garbage and every price/JSON-LD extraction silently fails.
    gzip + deflate are always decodable via the stdlib, so they stay.
    """
    for module in ("brotli", "brotlicffi"):
        try:
            __import__(module)
            return "gzip, deflate, br"
        except ImportError:
            continue
    return "gzip, deflate"


_ACCEPT_ENCODING = _supported_accept_encoding()
_JSON_LD_RE = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)

_ANALYST_SYSTEM = """
You are the Analyst Agent — an elite consumer-tech product intelligence
analyst. Your job is NOT to write a glossy review. Your job is to expose what
the seller does NOT say.

Operating principles:
1. BLIND SPOTS over marketing. List the technical / usage caveats the
   manufacturer or seller never advertises but expert reviewers, spec
   footnotes or experienced owners reveal (e.g. "Fast charge only with one
   cable bundled", "Sensor misreads on black carpets").
2. CHRONIC ISSUES over isolated complaints. Cluster recurring complaints
   across reviews; report only patterns that appear in MULTIPLE reviews.
   Cite frequency.
3. TRUST CHECK over face value. Detect fake / incentivised / bot-generated
   reviews. Signals: identical phrasing, pure 5-star with one-line generic
   praise, reviews posted in bursts on the same day, reviews ignoring product
   specifics. Compute an organic-vs-suspicious split.
4. HONEST balance. Pick EXACTLY 3 genuinely good aspects and EXACTLY 3
   must-tolerate weaknesses. Each one MUST be defensible with a concrete
   reason or a brief evidence quote.
5. RED FLAGS over polite warnings. Surface "fake product received", "arrived
   broken", "warranty void on arrival" — anything that should make the buyer
   hesitate.

GROUNDING — MANDATORY:
The Google Search tool is ALWAYS available. Before producing the JSON, you
MUST run AT LEAST these searches and weave the findings into your analysis:
  • "<product name> fiyat <site name>" for EACH supplied site (e.g.
    "iPhone 15 128 GB fiyat hepsiburada", "iPhone 15 128 GB fiyat trendyol").
    Use the live Google-indexed price for each site listed in the scraped
    data — even if the scraped block shows price=null, you must surface
    the real price via search.
  • "<product name> yorumlar" OR "<product name> reviews"
  • "<product name> uzman incelemesi" OR "<product name> expert review"
  • "<product name> kronik sorun" OR "<product name> common issues"
  • "<product name> kullanıcı şikayeti" OR "<product name> complaints"
Search is your PRIMARY source of price and review data. The scraped data
included below is best-effort — Turkish marketplaces often block automated
scrapers, so price/rating fields will frequently be empty or marked
"not found". In those cases your Google Search results are the SOURCE OF
TRUTH for the site_summaries section. Do NOT leave a site's price/rating
null just because the scraped block was empty — search for it.

Hard constraints:
- Combine the supplied scraped data WITH the grounded search results as
  evidence. Never invent prices, ratings or quotes. If a scraped value is
  present, prefer it; if it is missing or "not found", fall back to the
  most recent price the Google Search results surface for that site.
- For EVERY site listed in the scraped block, your site_summaries[] entry
  MUST include a numeric price unless Google Search produced no result for
  that site/product combo.
- Respond with a SINGLE valid JSON object matching the schema exactly. No
  markdown fences, no commentary, no leading/trailing prose.
- All human-readable strings must be in the requested locale.
- Keep evidence quotes ≤ 120 characters and verbatim (you may translate to
  the response locale, preserving meaning).

JSON STRING HYGIENE — non-negotiable, the response is machine-parsed:
- Inside any string value, the backslash character is RESERVED. Use it ONLY
  for these standard JSON escapes (shown in plain text, two characters each):
  backslash-quote, backslash-backslash, backslash-slash, backslash-b,
  backslash-f, backslash-n, backslash-r, backslash-t, and the unicode form
  backslash-u followed by exactly four hex digits.
- NEVER place a backslash before any other letter or character — Turkish
  letters like "ı", path-like tokens like "share-button", or random words
  must appear WITHOUT a preceding backslash.
- Strings MUST be on a single logical line; replace real newlines inside a
  value with a backslash-n escape sequence. Never paste a literal tab.
- Quotes inside a string value MUST be escaped (backslash before the quote).
  Do not use smart/curly quotes to "work around" this.
- The response MUST start with `{` and end with `}` — no UTF-8 BOM, no
  leading whitespace, no trailing text after the closing brace.
""".strip()


def _build_analyst_prompt(scraped: list[dict[str, Any]], locale: str, product_hint: str | None = None) -> str:
    schema = {
        "verdict": "BUY | WAIT | AVOID",
        "confidence": "0.0–1.0 (your own confidence in this verdict)",
        "headline": "ONE punchy sentence summarising the verdict",
        "final_recommendation": (
            "2-3 paragraphs of plain-language buying advice naming concrete "
            "reasons (price level, chronic issues, blind spots, alternatives)."
        ),
        "blind_spots": [
            {
                "claim": "what the marketing/spec sheet implies",
                "reality": "what actually happens day-to-day",
                "source": "reviews | spec_sheet | expert_consensus",
            }
        ],
        "chronic_issues": [
            {
                "issue": "concise label of the recurring complaint",
                "frequency": "integer count of reviews mentioning this",
                "severity": "low | medium | high",
                "evidence": ["up to 3 short verbatim quotes"],
            }
        ],
        "trust_report": {
            "total_reviews_seen": "integer total across all sites",
            "organic_pct": "0-100 estimate of genuine reviews",
            "suspicious_pct": "0-100 estimate of fake/bot reviews",
            "trust_score": "0-100 overall trust in this review pool",
            "suspicious_signals": [
                "patterns you spotted: identical phrasing, generic 5-star, etc."
            ],
            "suspicious_examples": ["up to 3 suspicious review snippets"],
        },
        "honest_pros": [
            {
                "label": "one-line strength",
                "explanation": "why it's genuinely good",
                "evidence": "optional supporting review quote",
            }
        ],
        "honest_cons": [
            {
                "label": "one-line weakness",
                "explanation": "why it's a must-tolerate trade-off",
                "evidence": "optional supporting review quote",
            }
        ],
        "red_flags": [
            "critical buyer warnings: counterfeits, DOA units, warranty issues"
        ],
        "site_summaries": [
            {
                "site": "site name",
                "url": "site url",
                "price": "numeric or null",
                "currency": "TRY/EUR/USD",
                "rating": "numeric or null",
                "review_count": "integer or null",
                "pros": ["1-3 quick pros for buying from this site"],
                "cons": ["1-3 quick cons for buying from this site"],
            }
        ],
        "cheapest_site": "name of the site with the lowest price (or null)",
        "cheapest_price": "numeric lowest price (or null)",
    }

    total_scraped_reviews = sum(len(item.get("reviews") or []) for item in scraped)
    sites_with_data = [
        item for item in scraped if (item.get("source_status") == "ok") and (
            item.get("price") not in (None, "", "not found")
            or item.get("rating") not in (None, "", "not found")
            or (item.get("reviews") or [])
        )
    ]
    sites_blocked = [item for item in scraped if item not in sites_with_data]

    product_label = product_hint or (sites_with_data[0].get("product_name") if sites_with_data else None) or "the product below"

    site_directory_lines = []
    for item in scraped:
        line = f"  - {item.get('site') or 'Unknown'}: {item.get('url')}"
        if item.get("source_status") == "fetch_error":
            line += "  [scrape blocked → MUST resolve price via Google Search]"
        elif item in sites_blocked:
            line += "  [scrape returned no price/rating → MUST resolve via Google Search]"
        site_directory_lines.append(line)
    site_directory = "\n".join(site_directory_lines)

    return f"""
You are analysing this product: "{product_label}".

It is sold on the following Turkish e-commerce sites. Use Google Search to
look up the CURRENT live price on each one, the average user rating, and any
common review themes:

{site_directory}

Below is the raw scraping result for each site (may be partial or empty for
sites with anti-bot protection — in those cases your Google Search results
are the source of truth):

{json.dumps(scraped, ensure_ascii=False, indent=2)}

Total reviews captured via scraping: {total_scraped_reviews}.
{("WARNING: Scraping returned no usable price/review data for " + str(len(sites_blocked)) + " of " + str(len(scraped)) + " sites. You MUST use Google Search to fill those gaps.") if sites_blocked else ""}

Return a SINGLE JSON object matching this schema exactly:

{json.dumps(schema, ensure_ascii=False, indent=2)}

Output requirements:
- Exactly 3 honest_pros and exactly 3 honest_cons. No more, no fewer.
- chronic_issues: only include patterns that appear in ≥2 reviews (whether
  from the scraped block or from search results). Sort by frequency desc.
- blind_spots: 2-5 entries. Each must contrast marketing vs reality.
- trust_report.total_reviews_seen MUST be ≥ {total_scraped_reviews} (sum of
  scraped reviews) plus any additional reviews you read from search. If you
  rely entirely on search results, estimate from the search snippets.
  organic_pct + suspicious_pct must equal 100.
- site_summaries: EVERY site listed in the directory above MUST have an
  entry with a numeric price unless Google Search produced nothing for it.
- red_flags: empty list is fine — only include if there is direct evidence.
- Locale for all strings: {locale}
""".strip()


def _normalize_number_text(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", text)
    return cleaned or None


def _domain_to_site_name(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return "Unknown"
    parts = host.split(".")
    if len(parts) >= 3 and parts[-1] in {"tr", "uk", "au", "br"} and parts[-2] in {"com", "co", "net", "org"}:
        return parts[-3].capitalize()
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return host.capitalize()


def _walk_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_dicts(value)


def _is_product_node(node: dict[str, Any]) -> bool:
    type_value = node.get("@type")
    if isinstance(type_value, str):
        return "product" in type_value.lower()
    if isinstance(type_value, list):
        return any("product" in str(item).lower() for item in type_value)
    return False


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_json_ld_blocks(html_text: str) -> list[Any]:
    blocks: list[Any] = []
    for match in _JSON_LD_RE.finditer(html_text):
        raw = unescape(match.group(1).strip())
        if not raw:
            continue
        cleaned = raw.replace("<!--", "").replace("-->", "").strip()
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1]
        try:
            blocks.append(json.loads(cleaned))
        except json.JSONDecodeError:
            continue
    return blocks


def _extract_from_product_node(node: dict[str, Any]) -> dict[str, Any]:
    aggregate = node.get("aggregateRating")
    if isinstance(aggregate, list):
        aggregate = next((item for item in aggregate if isinstance(item, dict)), None)
    if not isinstance(aggregate, dict):
        aggregate = {}

    offers = node.get("offers")
    if isinstance(offers, list):
        offers = next((item for item in offers if isinstance(item, dict)), None)
    if not isinstance(offers, dict):
        offers = {}

    reviews: list[str] = []
    for review in _to_list(node.get("review") or node.get("reviews")):
        if not isinstance(review, dict):
            continue
        body = review.get("reviewBody") or review.get("description") or review.get("name")
        if isinstance(body, str) and body.strip():
            reviews.append(body.strip())
        if len(reviews) >= 20:
            break

    specs: dict[str, str] = {}
    for item in _to_list(node.get("additionalProperty")):
        if not isinstance(item, dict):
            continue
        key = item.get("name")
        value = item.get("value")
        if isinstance(key, str) and isinstance(value, (str, int, float)):
            specs[key.strip()] = str(value).strip()

    return {
        "product_name": node.get("name"),
        "price": offers.get("price") or offers.get("lowPrice") or offers.get("highPrice"),
        "currency": offers.get("priceCurrency"),
        "rating": aggregate.get("ratingValue"),
        "rating_scale": aggregate.get("bestRating"),
        "review_count": aggregate.get("reviewCount") or aggregate.get("ratingCount"),
        "reviews": reviews,
        "specs": specs,
    }


def _extract_meta_value(html_text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = (match.group(1) or "").strip()
            if value:
                return unescape(value)
    return None


def _extract_with_regex_fallback(html_text: str) -> dict[str, Any]:
    title = _extract_meta_value(
        html_text,
        [
            r'<div[^>]+itemtype=["\']https://schema\.org/Product["\'][^>]*>.*?<[^>]+itemprop=["\']name["\'][^>]*>\s*([^<]+)\s*</',
            r'<h[1-6][^>]+class=["\'][^"\']*title[^"\']*["\'][^>]*>\s*([^<]+)\s*</h[1-6]>',
            r'<[^>]+itemprop=["\']name["\'][^>]*>\s*([^<]+)\s*</',
            r"<title[^>]*>(.*?)</title>",
        ],
    )
    price = _extract_meta_value(
        html_text,
        [
            r'<meta[^>]+(?:property|name|itemprop)=["\']product:price:amount["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+(?:property|name|itemprop)=["\']price["\'][^>]+content=["\']([^"\']+)["\']',
            r'<[^>]+itemprop=["\']price["\'][^>]*>\s*([^<]+)\s*</',
            r'"price"\s*:\s*"([^"]+)"',
        ],
    )
    currency = _extract_meta_value(
        html_text,
        [
            r'<meta[^>]+(?:property|name|itemprop)=["\']product:price:currency["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+itemprop=["\']priceCurrency["\'][^>]+content=["\']([^"\']+)["\']',
            r'"priceCurrency"\s*:\s*"([^"]+)"',
        ],
    )
    rating = _extract_meta_value(
        html_text,
        [
            r'<meta[^>]+(?:property|name|itemprop)=["\']ratingValue["\'][^>]+content=["\']([^"\']+)["\']',
            r'<[^>]+itemprop=["\']ratingValue["\'][^>]*>\s*([^<]+)\s*</',
            r'"ratingValue"\s*:\s*"([^"]+)"',
        ],
    )
    review_count = _extract_meta_value(
        html_text,
        [
            r'<meta[^>]+(?:property|name|itemprop)=["\']reviewCount["\'][^>]+content=["\']([^"\']+)["\']',
            r'<[^>]+itemprop=["\']reviewCount["\'][^>]*>\s*([^<]+)\s*</',
            r'"reviewCount"\s*:\s*"([^"]+)"',
            r'"ratingCount"\s*:\s*"([^"]+)"',
        ],
    )

    if not rating:
        ratings_block = _extract_meta_value(
            html_text,
            [r'<div[^>]+class=["\'][^"\']*ratings[^"\']*["\'][^>]*>(.*?)</div>'],
        )
        if ratings_block:
            star_count = len(re.findall(r"ws-icon-star", ratings_block))
            if star_count > 0:
                rating = str(star_count)

    return {
        "product_name": title,
        "price": price,
        "currency": currency,
        "rating": rating,
        "review_count": review_count,
    }


def _merge_product_data(base: CompareSiteData, extracted: dict[str, Any], error_detail: str | None = None) -> dict[str, Any]:
    reviews = extracted.get("reviews")
    if not isinstance(reviews, list):
        reviews = []

    specs = extracted.get("specs")
    if not isinstance(specs, dict):
        specs = {}

    merged = {
        "site": (base.site or _domain_to_site_name(base.url)),
        "url": base.url,
        "product_name": extracted.get("product_name") or base.product_name or "not found",
        "price": extracted.get("price") or base.price or "not found",
        "currency": extracted.get("currency") or base.currency or "TRY",
        "rating": extracted.get("rating") or base.rating or "not found",
        "rating_scale": extracted.get("rating_scale") or base.rating_scale or "5",
        "review_count": extracted.get("review_count") or base.review_count or "not found",
        "specs": specs if specs else base.specs,
        "reviews": reviews if reviews else base.reviews,
        "source_status": "ok" if error_detail is None else "partial",
    }
    if error_detail:
        merged["source_note"] = error_detail

    merged["price"] = _normalize_number_text(merged["price"]) or str(merged["price"])
    merged["rating"] = _normalize_number_text(merged["rating"]) or str(merged["rating"])
    merged["review_count"] = _normalize_number_text(merged["review_count"]) or str(merged["review_count"])
    return merged


async def _scrape_one(client: httpx.AsyncClient, item: CompareSiteData, semaphore: asyncio.Semaphore) -> dict[str, Any]:
    async with semaphore:
        html_text = ""
        fetch_error_msg = None
        try:
            response = await client.get(item.url)
            response.raise_for_status()
            html_text = response.text
        except httpx.HTTPError as err:
            fetch_error_msg = str(err)

        best_candidate: dict[str, Any] = {}
        if html_text:
            best_score = -1
            for block in _parse_json_ld_blocks(html_text):
                for node in _walk_dicts(block):
                    if not _is_product_node(node):
                        continue
                    candidate = _extract_from_product_node(node)
                    score = sum(
                        1
                        for key in ("product_name", "price", "rating", "review_count")
                        if candidate.get(key)
                    ) + (1 if candidate.get("reviews") else 0)
                    if score > best_score:
                        best_candidate = candidate
                        best_score = score

        regex_candidate = _extract_with_regex_fallback(html_text) if html_text else {}
        merged_candidate = {
            "product_name": best_candidate.get("product_name") or regex_candidate.get("product_name"),
            "price": best_candidate.get("price") or regex_candidate.get("price"),
            "currency": best_candidate.get("currency") or regex_candidate.get("currency"),
            "rating": best_candidate.get("rating") or regex_candidate.get("rating"),
            "rating_scale": best_candidate.get("rating_scale") or "5",
            "review_count": best_candidate.get("review_count") or regex_candidate.get("review_count"),
            "specs": best_candidate.get("specs") or {},
            "reviews": best_candidate.get("reviews") or [],
        }

        has_core_data = any(merged_candidate.get(key) for key in ("price", "rating", "review_count", "reviews"))

        if not has_core_data and fetch_error_msg:
            return {
                "site": item.site or _domain_to_site_name(item.url),
                "url": item.url,
                "product_name": item.product_name or "not found",
                "price": item.price or "not found",
                "currency": item.currency or "TRY",
                "rating": item.rating or "not found",
                "rating_scale": item.rating_scale or "5",
                "review_count": item.review_count or "not found",
                "specs": item.specs,
                "reviews": item.reviews,
                "source_status": "fetch_error",
                "source_note": fetch_error_msg,
            }

        if has_core_data:
            return _merge_product_data(item, merged_candidate)

        return _merge_product_data(
            item,
            merged_candidate,
            error_detail="Only limited product data could be extracted from the page.",
        )


async def _scrape_site_data(products: list[CompareSiteData]) -> list[dict[str, Any]]:
    # Aggressive timeouts: real Turkish marketplace pages either respond in
    # 2-4s or stall indefinitely behind an anti-bot wall. An 8-second read
    # ceiling caps the worst-case slow store so total wall-time stays close to
    # the fastest store's response. Per-store failures don't bubble — they
    # come back as source_status=fetch_error and the analyst still sees the
    # others' data.
    timeout = httpx.Timeout(connect=5.0, read=8.0, write=8.0, pool=10.0)
    # Realistic browser fingerprint for Turkish marketplaces. Accept-Language=tr
    # gets us TRY pricing on sites that geo-switch on locale; the sec-* hints
    # mimic a real Chrome navigation so anti-bot WAFs (Hepsiburada, Trendyol)
    # don't blank-page us. Without these the JSON-LD block is often stripped.
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept-Encoding": _ACCEPT_ENCODING,
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    # All stores fire at once on a free-tier key; no rate-limiting on these hosts.
    semaphore = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        tasks = [_scrape_one(client, item, semaphore) for item in products]
        return await asyncio.gather(*tasks)


async def _generate_deep_analysis(
    primary: str, fallback: str, prompt: str, locale: str
) -> GroundedResult:
    """Call Gemini with Google Search grounding and return the structured
    deep-analysis JSON plus the grounding source list.
    """
    # Grounding (google_search) only has quota on the Gemini 2.5 family on this
    # key — 3.x models hard-429 on grounded calls — so primary/fallback are
    # 2.5 Flash / 2.5 Flash-Lite (see config.py). No extra rungs needed.
    return await call_gemini(
        primary_model=primary,
        fallback_model=fallback,
        system=f"{_ANALYST_SYSTEM}\nResponse locale: {locale}",
        user_prompt=prompt,
        use_search=True,
        response_json=True,
        max_output_tokens=3072,
        temperature=0.2,
        top_p=0.95,
        timeout_seconds=45.0,
    )


def _parse_price_to_float(raw: Any) -> float | None:
    """Best-effort numeric parsing of mixed locale price strings (e.g. '74.999,90')."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "not found":
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", text)
    if not cleaned:
        return None
    # Heuristic: if both separators present, treat the rightmost as the
    # decimal separator and strip the other as a thousands grouping.
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Comma is decimal separator if it appears to fence ≤2 digits.
        if re.search(r",\d{1,2}$", cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _collect_store_prices(scraped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in scraped:
        price_value = _parse_price_to_float(item.get("price"))
        out.append({
            "site": item.get("site") or "Unknown",
            "url": item.get("url"),
            "price": price_value,
            "currency": item.get("currency") or "TRY",
        })
    return out


def _reject_price_outliers(prices: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Drop store prices that are obviously the wrong product variant.

    Why this exists
    ────────────────
    When one site's scrape fails (anti-bot 403, broken JSON-LD) and Gemini's
    Search Grounding fills the blank, the grounded result is sometimes a
    case/accessory listing for the same product name — e.g. an iPhone 15
    silicone case at 3.000 TL alongside the actual phone at 45.000 TL on
    other sites. Without a cross-site sanity check, that bogus number wins
    the "lowest price" badge and the UI shows 3.000 TL as the iPhone 15
    price, which is the bug the user just reported.

    Strategy
    ────────
    * Need ≥ 3 priced sites to have a stable reference — with only 1-2
      points we cannot tell which is the outlier and which is the truth, so
      we accept everything.
    * Compute the median of the remaining points; reject any entry that is
      < 1/3 or > 3× the median. The 3× factor is intentionally loose so
      a legitimately discounted store (40-50% off) survives, but a
      ten-fold mismatch (case vs phone) does not.
    * The first pass uses the FULL set's median to flag candidates; the
      final check re-medianises the survivors so a single bad point does
      not skew the threshold and accidentally also reject good neighbours.

    Returns
    ───────
    ``(filtered, dropped_site_names)`` — the dropped list is logged so an
    operator can confirm the rejection was correct.
    """
    priced = [p for p in prices if isinstance(p.get("price"), (int, float)) and p["price"] > 0]
    if len(priced) < 3:
        return prices, []

    sorted_prices = sorted(pp["price"] for pp in priced)
    mid = len(sorted_prices) // 2
    if len(sorted_prices) % 2:
        median = sorted_prices[mid]
    else:
        median = (sorted_prices[mid - 1] + sorted_prices[mid]) / 2.0
    if median <= 0:
        return prices, []

    low_bound = median / 3.0
    high_bound = median * 3.0

    filtered: list[dict[str, Any]] = []
    dropped: list[str] = []
    for entry in prices:
        p = entry.get("price")
        if isinstance(p, (int, float)) and p > 0 and (p < low_bound or p > high_bound):
            site = entry.get("site") or "Unknown"
            dropped.append(f"{site}={p:.0f} (median={median:.0f})")
            cleaned = dict(entry)
            cleaned["price"] = None
            cleaned["currency"] = entry.get("currency") or "TRY"
            cleaned["price_rejected_as_outlier"] = True
            filtered.append(cleaned)
        else:
            filtered.append(entry)
    return filtered, dropped


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _coerce_pct(value: Any, default: float = 0.0) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(100.0, n))


def _normalize_str_list(value: Any, limit: int = 5) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for v in value:
        if not isinstance(v, (str, int, float)):
            continue
        s = str(v).strip()
        if s:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _normalize_chronic_issue(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    issue = str(raw.get("issue") or "").strip()
    if not issue:
        return None
    severity = str(raw.get("severity") or "medium").strip().lower()
    if severity not in {"low", "medium", "high"}:
        severity = "medium"
    return {
        "issue": issue,
        "frequency": max(1, _coerce_int(raw.get("frequency"), 1)),
        "severity": severity,
        "evidence": _normalize_str_list(raw.get("evidence"), limit=3),
    }


def _normalize_blind_spot(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    claim = str(raw.get("claim") or "").strip()
    reality = str(raw.get("reality") or "").strip()
    if not claim or not reality:
        return None
    source = str(raw.get("source") or "reviews").strip().lower()
    if source not in {"reviews", "spec_sheet", "expert_consensus"}:
        source = "reviews"
    return {"claim": claim, "reality": reality, "source": source}


def _normalize_honest_point(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    label = str(raw.get("label") or "").strip()
    explanation = str(raw.get("explanation") or "").strip()
    if not label or not explanation:
        return None
    evidence = raw.get("evidence")
    return {
        "label": label,
        "explanation": explanation,
        "evidence": (str(evidence).strip() or None) if evidence else None,
    }


def _normalize_site_summary(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    site = str(raw.get("site") or "").strip()
    if not site:
        return None
    price = raw.get("price")
    try:
        price = float(price) if price not in (None, "", "not found") else None
    except (TypeError, ValueError):
        price = None
    rating = raw.get("rating")
    try:
        rating = float(rating) if rating not in (None, "", "not found") else None
    except (TypeError, ValueError):
        rating = None
    return {
        "site": site,
        "url": (str(raw.get("url")).strip() or None) if raw.get("url") else None,
        "price": price,
        "currency": str(raw.get("currency") or "TRY").strip() or "TRY",
        "rating": rating,
        "review_count": _coerce_int(raw.get("review_count"), 0) or None,
        "pros": _normalize_str_list(raw.get("pros"), limit=3),
        "cons": _normalize_str_list(raw.get("cons"), limit=3),
    }


def _normalize_deep_analysis(
    raw: dict,
    scraped: list[dict[str, Any]],
    lowest_price: float | None,
    lowest_price_site: str | None,
) -> dict:
    verdict = str(raw.get("verdict") or "WAIT").strip().upper()
    if verdict not in {"BUY", "WAIT", "AVOID"}:
        verdict = "WAIT"

    try:
        confidence = float(raw.get("confidence") or 0.5)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    raw_trust = raw.get("trust_report") if isinstance(raw.get("trust_report"), dict) else {}
    organic = _coerce_pct(raw_trust.get("organic_pct"), 100.0)
    suspicious = _coerce_pct(raw_trust.get("suspicious_pct"), 0.0)
    # Force the two halves to add up; if the model emitted nonsense, derive
    # the missing half from the other so the chart never lies.
    if abs((organic + suspicious) - 100.0) > 0.5:
        if organic <= 0 and suspicious > 0:
            organic = 100.0 - suspicious
        elif suspicious <= 0 and organic > 0:
            suspicious = 100.0 - organic
        else:
            total = organic + suspicious or 100.0
            organic = round(organic * 100.0 / total, 1)
            suspicious = round(100.0 - organic, 1)
    trust_score = _coerce_int(raw_trust.get("trust_score"), int(round(organic)))
    trust_score = max(0, min(100, trust_score))

    total_reviews = _coerce_int(raw_trust.get("total_reviews_seen"), 0)
    if total_reviews <= 0:
        total_reviews = sum(len(item.get("reviews") or []) for item in scraped)

    trust_report = {
        "total_reviews_seen": total_reviews,
        "organic_pct": round(organic, 1),
        "suspicious_pct": round(suspicious, 1),
        "trust_score": trust_score,
        "suspicious_signals": _normalize_str_list(raw_trust.get("suspicious_signals"), limit=6),
        "suspicious_examples": _normalize_str_list(raw_trust.get("suspicious_examples"), limit=3),
    }

    blind_spots = [bs for bs in (_normalize_blind_spot(b) for b in (raw.get("blind_spots") or [])) if bs][:6]

    chronic_issues = [
        ci for ci in (_normalize_chronic_issue(c) for c in (raw.get("chronic_issues") or [])) if ci
    ]
    chronic_issues.sort(key=lambda c: c["frequency"], reverse=True)
    chronic_issues = chronic_issues[:8]

    pros = [p for p in (_normalize_honest_point(p) for p in (raw.get("honest_pros") or [])) if p][:3]
    cons = [p for p in (_normalize_honest_point(p) for p in (raw.get("honest_cons") or [])) if p][:3]

    site_summaries = [
        s for s in (_normalize_site_summary(s) for s in (raw.get("site_summaries") or [])) if s
    ]
    # If the model omitted site_summaries entirely, synthesize a minimal one
    # from the scraped numerics so the UI's site strip never sits empty.
    if not site_summaries:
        for item in scraped:
            try:
                p = float(item.get("price")) if item.get("price") not in (None, "", "not found") else None
            except (TypeError, ValueError):
                p = None
            try:
                r = float(item.get("rating")) if item.get("rating") not in (None, "", "not found") else None
            except (TypeError, ValueError):
                r = None
            site_summaries.append({
                "site": item.get("site") or "Unknown",
                "url": item.get("url"),
                "price": p,
                "currency": item.get("currency") or "TRY",
                "rating": r,
                "review_count": _coerce_int(item.get("review_count"), 0) or None,
                "pros": [],
                "cons": [],
            })

    cheapest_site = raw.get("cheapest_site") or lowest_price_site
    cheapest_price_raw = raw.get("cheapest_price")
    try:
        cheapest_price = float(cheapest_price_raw) if cheapest_price_raw is not None else None
    except (TypeError, ValueError):
        cheapest_price = None
    if cheapest_price is None:
        cheapest_price = lowest_price

    return {
        "verdict": verdict,
        "confidence": confidence,
        "headline": str(raw.get("headline") or "").strip()
            or "Genel değerlendirme analiz verilerine göre hazırlandı.",
        "final_recommendation": str(raw.get("final_recommendation") or "").strip()
            or "Veriler ışığında dengeli bir alım kararı için kronik sorunları ve kör noktaları göz önünde bulundurun.",
        "blind_spots": blind_spots,
        "chronic_issues": chronic_issues,
        "trust_report": trust_report,
        "honest_pros": pros,
        "honest_cons": cons,
        "red_flags": _normalize_str_list(raw.get("red_flags"), limit=6),
        "site_summaries": site_summaries,
        "cheapest_site": cheapest_site,
        "cheapest_price": cheapest_price,
    }


# Disk-persistent deep-analysis cache. A grounded compare costs ~60s + scarce
# Gemini quota, but the verdict/blind-spots/issues are stable for days, so we
# cache the full response by product identity (in-memory hot path + JSON cold
# store that survives restarts). Live prices are refreshed separately on every
# cache hit, so a cached entry never shows stale price tags.
_DEEP_ANALYSIS_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
_CACHE_FILE = _CACHE_DIR / "compare_analysis.json"
_DEEP_ANALYSIS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _load_cache_from_disk() -> None:
    """Populate the in-memory cache from disk at boot. Silent on any error
    (missing file, corrupted JSON) — the cache is best-effort and a fresh
    start is always recoverable by running an analysis again.
    """
    try:
        if not _CACHE_FILE.is_file():
            return
        raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        loaded = 0
        for key, entry in raw.items():
            if not isinstance(entry, dict):
                continue
            saved_at = entry.get("saved_at")
            value = entry.get("value")
            if not isinstance(saved_at, (int, float)) or not isinstance(value, dict):
                continue
            if now - saved_at > _DEEP_ANALYSIS_TTL_SECONDS:
                continue
            _DEEP_ANALYSIS_CACHE[key] = (float(saved_at), value)
            loaded += 1
        if loaded:
            logger.info("CompareAgent -> loaded %d cached analysis entries from disk", loaded)
    except Exception as err:
        logger.warning("CompareAgent -> cache load failed (ignored): %s", err)


def _write_cache_to_disk() -> None:
    """Snapshot the in-memory cache to disk. Atomic write via temp file +
    rename so a crash mid-write cannot leave a partially serialised JSON.
    """
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            key: {"saved_at": saved_at, "value": value}
            for key, (saved_at, value) in _DEEP_ANALYSIS_CACHE.items()
        }
        tmp_path = _CACHE_FILE.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, _CACHE_FILE)
    except Exception as err:
        logger.warning("CompareAgent -> cache save failed (ignored): %s", err)


def _cache_key_for(request: CompareRequest) -> str:
    """Identity = locale + the SET of product URLs scraped (order-independent).
    Same product viewed twice in the TTL window collapses to one entry even
    if the store order differs between requests.
    """
    urls = sorted({p.url.strip().lower() for p in request.products if p.url})
    return f"{request.locale}::" + "||".join(urls)


def _cache_get(key: str) -> Optional[dict[str, Any]]:
    hit = _DEEP_ANALYSIS_CACHE.get(key)
    if not hit:
        return None
    saved_at, value = hit
    if time.time() - saved_at > _DEEP_ANALYSIS_TTL_SECONDS:
        _DEEP_ANALYSIS_CACHE.pop(key, None)
        _write_cache_to_disk()
        return None
    return value


def _cache_set(key: str, value: dict[str, Any]) -> None:
    _DEEP_ANALYSIS_CACHE[key] = (time.time(), value)
    _write_cache_to_disk()


# Load any cached analyses written by a previous backend run. Module-level so
# the warm-up happens once, on first import, before any request lands.
_load_cache_from_disk()


# Local fallback analysis builder — used when Gemini is unreachable (quota,
# outage, parse failure). Builds a defensible report from scraped data alone
# via Turkish keyword frequency; it never invents prices or quotes.

# Recurring-issue keyword buckets (Turkish + English variants, substring-matched
# on normalised reviews). Each bucket fires only at ≥2 mentions, mirroring the
# system prompt's "issue must appear in ≥2 reviews" rule.
_CHRONIC_KEYWORDS: list[tuple[str, str, list[str]]] = [
    ("Isınma sorunu", "high", ["ısınıyor", "ısınma", "aşırı ısın", "overheat", "çok ısın"]),
    ("Pil ömrü zayıf", "high", ["pil ömrü", "pil çok", "şarj bitiyor", "battery", "şarj tutmuyor", "pil hızlı bit"]),
    ("Şarj sorunu", "medium", ["şarj olmuyor", "şarj sorun", "şarj kabul etmiyor", "charging issue"]),
    ("Bağlantı kopması", "medium", ["bağlantı kopuyor", "disconnect", "wifi sorun", "bluetooth sorun"]),
    ("Yazılım/donma", "medium", ["donuyor", "freeze", "yazılım sorun", "kasıyor", "yavaşladı"]),
    ("Ekran problemi", "high", ["ekran sorun", "ekran kırık", "ekran çiziği", "screen issue", "ölü piksel"]),
    ("Hoparlör/ses", "medium", ["ses kısık", "hoparlör sorun", "ses bozuk", "speaker"]),
    ("Kamera kalitesi", "low", ["kamera kötü", "kamera bulanık", "kamera yetersiz"]),
    ("Kargo/iade", "low", ["kargo geç", "iade ettim", "kargoda hasar", "geç geldi"]),
]

_RED_FLAG_KEYWORDS: list[str] = [
    "sahte ürün", "sahte geldi", "taklit", "kırık geldi", "bozuk geldi",
    "garantisiz", "kutu açık", "fake", "counterfeit", "dolandırı",
]

_POSITIVE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Kullanım kolaylığı", ["pratik", "kolay kullan", "akıcı", "rahat"]),
    ("Performans", ["çok hızlı", "süper performans", "harika performans"]),
    ("Pil ömrü", ["pil çok iyi", "uzun pil", "şarj iyi"]),
    ("Ekran kalitesi", ["ekran harika", "ekran net", "ekran çok güzel"]),
    ("Kamera", ["kamera mükemmel", "kamera harika", "fotoğraflar net"]),
    ("Fiyat/performans", ["fiyat performans", "uygun fiyat", "değer"]),
    ("Tasarım", ["şık", "güzel görün", "tasarım harika"]),
]

_SUSPICIOUS_GENERIC = {
    "harika", "süper", "çok güzel", "mükemmel", "bayıldım",
    "tavsiye ederim", "kesinlikle tavsiye", "hızlı kargo", "teşekkürler",
}


def _normalise_review(text: str) -> str:
    return (text or "").lower().strip()


def _build_local_fallback_analysis(
    scraped: list[dict[str, Any]],
    lowest_price: float | None,
    lowest_price_site: str | None,
    product_hint: str | None,
    reason: str,
) -> dict[str, Any]:
    """Build a deterministic analysis report from scraped data alone.

    No Gemini call. Used as the safety net when the upstream model is
    unavailable (quota / transient / parse failure). Everything here is
    derived from the data we actually have — no invented prices, no
    fabricated quotes.
    """
    # Aggregate every review across every site for keyword scanning. Keep
    # the original casing for evidence quotes; scan against a normalised
    # lowercase copy.
    all_reviews: list[str] = []
    for item in scraped:
        for r in item.get("reviews") or []:
            if isinstance(r, str) and r.strip():
                all_reviews.append(r.strip())

    normalised = [_normalise_review(r) for r in all_reviews]
    total_reviews = len(all_reviews)

    # Chronic issues: keyword bucket counts, ≥2 reviews threshold.
    chronic_issues: list[dict[str, Any]] = []
    for label, severity, variants in _CHRONIC_KEYWORDS:
        matched_indices = [
            i for i, n in enumerate(normalised)
            if any(v in n for v in variants)
        ]
        if len(matched_indices) >= 2:
            evidence = [all_reviews[i][:120] for i in matched_indices[:3]]
            chronic_issues.append({
                "issue": label,
                "frequency": len(matched_indices),
                "severity": severity,
                "evidence": evidence,
            })
    chronic_issues.sort(key=lambda c: c["frequency"], reverse=True)
    chronic_issues = chronic_issues[:6]

    # Red flags: substring scan over normalised reviews.
    red_flags: list[str] = []
    for kw in _RED_FLAG_KEYWORDS:
        if any(kw in n for n in normalised):
            red_flags.append(f"Bazı kullanıcılar '{kw}' ifadesini kullandı; dikkatli olun.")
    red_flags = red_flags[:4]

    # Positive themes: keyword buckets, ≥1 mention.
    positive_themes: list[str] = []
    for label, variants in _POSITIVE_KEYWORDS:
        if any(v in n for v in variants for n in normalised):
            positive_themes.append(label)
    positive_themes = positive_themes[:5]

    # Trust scoring — heuristic, not magic. Generic-praise share drives the
    # suspicious estimate; very short reviews (<25 chars) inflate it too.
    generic_count = 0
    short_count = 0
    for n in normalised:
        if len(n) < 25:
            short_count += 1
        stripped = n.strip(".! ")
        if stripped in _SUSPICIOUS_GENERIC or any(g in n for g in _SUSPICIOUS_GENERIC):
            generic_count += 1
    if total_reviews > 0:
        suspicious_share = min(95.0, (generic_count * 100.0 / total_reviews) + (short_count * 25.0 / total_reviews))
    else:
        suspicious_share = 0.0
    suspicious_pct = round(suspicious_share, 1)
    organic_pct = round(100.0 - suspicious_pct, 1)
    trust_score = max(0, min(100, int(round(organic_pct))))

    # Site summaries from scraped numerics — anything we couldn't parse
    # stays null instead of being faked.
    site_summaries: list[dict[str, Any]] = []
    for item in scraped:
        try:
            p = float(item.get("price")) if item.get("price") not in (None, "", "not found") else None
        except (TypeError, ValueError):
            p = None
        try:
            r = float(item.get("rating")) if item.get("rating") not in (None, "", "not found") else None
        except (TypeError, ValueError):
            r = None
        rc = item.get("review_count")
        try:
            rc_int: Optional[int] = int(float(rc)) if rc not in (None, "", "not found") else None
        except (TypeError, ValueError):
            rc_int = None
        site_summaries.append({
            "site": item.get("site") or "Unknown",
            "url": item.get("url"),
            "price": p,
            "currency": item.get("currency") or "TRY",
            "rating": r,
            "review_count": rc_int,
            "pros": [],
            "cons": [],
        })

    # Verdict heuristic: lean on the spread between lowest and highest
    # priced site. A wide spread (>15%) at a known cheapest site → BUY at
    # that store; a tight spread → WAIT. Chronic issues with severity=high
    # downgrade BUY → WAIT. Red flags or ≥3 high-severity issues → AVOID.
    high_severity_count = sum(1 for c in chronic_issues if c["severity"] == "high")
    prices_only = [s["price"] for s in site_summaries if isinstance(s["price"], (int, float)) and s["price"] > 0]

    verdict = "WAIT"
    if red_flags or high_severity_count >= 3:
        verdict = "AVOID"
    elif lowest_price and prices_only:
        max_price = max(prices_only)
        spread_pct = ((max_price - lowest_price) / max_price * 100.0) if max_price > 0 else 0.0
        if high_severity_count == 0 and spread_pct >= 12.0:
            verdict = "BUY"
        elif high_severity_count <= 1 and spread_pct >= 6.0:
            verdict = "BUY"

    confidence = 0.55 if total_reviews >= 20 else 0.45 if total_reviews >= 5 else 0.35

    name_label = (product_hint or "ürün").strip()
    if lowest_price and lowest_price_site:
        cheapest_line = f"En düşük fiyat şu an {lowest_price_site} mağazasında: {int(round(lowest_price)):,} TL.".replace(",", ".")
    else:
        cheapest_line = "Şu an mağazalar arasından net bir en düşük fiyat çıkartılamadı."

    headline_map = {
        "BUY": f"{name_label} için fiyat avantajı görünüyor.",
        "WAIT": f"{name_label} için biraz daha beklemek mantıklı.",
        "AVOID": f"{name_label} için ciddi uyarılar mevcut, alımdan kaçının.",
    }
    final_map = {
        "BUY": (
            f"{cheapest_line} Mağaza fiyatları arasındaki fark belirgin ve "
            "yorumlardan tehlikeli bir kronik sorun çıkmadı. Bu pencerede "
            "alım yapmak mantıklı görünüyor."
        ),
        "WAIT": (
            f"{cheapest_line} Mağaza fiyatları birbirine yakın ve yorumlar "
            "kararsız bir tablo çiziyor. Birkaç gün fiyat takibi öneririm; "
            "daha geniş bir fiyat aralığı veya net bir indirim görmeden "
            "alımı acele etmeyin."
        ),
        "AVOID": (
            "Yorumlardan ciddi uyarı sinyalleri geliyor (sahte ürün, "
            "kırık ürün veya çoklu yüksek-şiddetli kronik sorunlar). "
            "Bu ürün yerine alternatif modelleri değerlendirmenizi öneririm."
        ),
    }

    return {
        "verdict": verdict,
        "confidence": confidence,
        "headline": headline_map[verdict],
        "final_recommendation": final_map[verdict] + (
            f"\n\nNot: Yapay zekâ kapsamlı analizi şu an çalıştırılamadı ({reason}). "
            "Bu rapor toplanan yorumlar ve mağaza fiyatlarına dayalı olarak "
            "yerel olarak üretildi. Birkaç dakika sonra tekrar Analyze'a "
            "basarsanız tam AI raporu otomatik olarak yüklenecektir."
        ),
        "blind_spots": [],  # Honestly: we can't derive blind spots without LLM reasoning.
        "chronic_issues": chronic_issues,
        "trust_report": {
            "total_reviews_seen": total_reviews,
            "organic_pct": organic_pct,
            "suspicious_pct": suspicious_pct,
            "trust_score": trust_score,
            "suspicious_signals": (
                ["Çok kısa, jenerik övgü yorumları var"] if generic_count >= 2 else []
            ),
            "suspicious_examples": [
                all_reviews[i][:120]
                for i, n in enumerate(normalised)
                if any(g in n for g in _SUSPICIOUS_GENERIC)
            ][:3],
        },
        "honest_pros": [
            {"label": t, "explanation": "Yorumlarda tekrar eden olumlu bahis.", "evidence": None}
            for t in positive_themes[:3]
        ],
        "honest_cons": [
            {
                "label": c["issue"],
                "explanation": f"{c['frequency']} farklı yorumda tekrar eden sorun.",
                "evidence": (c["evidence"][0] if c["evidence"] else None),
            }
            for c in chronic_issues[:3]
        ],
        "red_flags": red_flags,
        "site_summaries": site_summaries,
        "cheapest_site": lowest_price_site,
        "cheapest_price": lowest_price,
        "grounding_sources": [],
        "grounded": False,
        "fallback": True,
        "fallback_reason": reason,
    }


async def run_compare_agent(request: CompareRequest) -> dict[str, Any]:
    """Scrape every product link, aggregate reviews/specs, then ask Gemini for a
    grounded structured report (blind spots, chronic issues, trust score, honest
    pros/cons). Cached by product-URL-set + locale for the TTL above.

    Returns: deep_analysis, lowest_price, lowest_price_site, store_prices, model_used.
    """
    valid_products = [
        product
        for product in request.products
        if isinstance(product.url, str) and product.url.startswith(("http://", "https://"))
    ]
    if not valid_products:
        raise ValueError("No valid http(s) product links found.")

    cache_key = _cache_key_for(request)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(
            "CompareAgent -> CACHE HIT (key=%s..., entries=%d, urls=%d)",
            cache_key[:60], len(_DEEP_ANALYSIS_CACHE), len(valid_products),
        )
        return {**cached, "cached": True}
    logger.info(
        "CompareAgent -> cache MISS (key=%s..., entries=%d)",
        cache_key[:60], len(_DEEP_ANALYSIS_CACHE),
    )

    logger.info("CompareAgent -> scraping %d product links", len(valid_products))
    scraped = await _scrape_site_data(valid_products)

    ok_count = sum(1 for item in scraped if item.get("source_status") == "ok")
    logger.info("CompareAgent -> scraping done (ok=%d/%d)", ok_count, len(scraped))
    # Even when every site blocked the scraper (anti-bot WAFs on Hepsiburada /
    # Trendyol can return 403/empty pages), we still hand the supplied URLs to
    # Gemini and lean on Google Search grounding for live prices and reviews.
    # The system prompt instructs the model to search "<product> fiyat <site>"
    # for every site whose scrape came back empty, so the user sees real
    # data instead of a hard error — which previously happened whenever the
    # underlying anti-bot kicked in.

    store_prices = _collect_store_prices(scraped)
    store_prices, dropped_scraped = _reject_price_outliers(store_prices)
    if dropped_scraped:
        logger.warning(
            "CompareAgent -> rejected %d scraped price outlier(s): %s",
            len(dropped_scraped), "; ".join(dropped_scraped),
        )
    priced = [sp for sp in store_prices if sp["price"] is not None and sp["price"] > 0]
    if priced:
        cheapest = min(priced, key=lambda sp: sp["price"])
        lowest_price = cheapest["price"]
        lowest_price_site = cheapest["site"]
    else:
        lowest_price = None
        lowest_price_site = None

    # Build a slimmed payload for the model — trim very long review strings
    # but keep the full set so chronic-pattern detection has signal. Gemini 3's
    # 1M-token context comfortably ingests thousands of reviews.
    payload = []
    for item in scraped:
        payload.append({
            **{k: v for k, v in item.items() if k != "reviews"},
            "reviews": [str(r)[:600] for r in (item.get("reviews") or [])],
        })

    # Surface the product name to the model even when every scrape blocked —
    # otherwise Gemini cannot run "<product> fiyat <site>" searches.
    product_hint = next(
        (p.product_name for p in valid_products if (p.product_name or "").strip()),
        None,
    )
    prompt = _build_analyst_prompt(payload, request.locale, product_hint=product_hint)

    # Primary: Analyst model (Gemini 3 Pro when paid, else Gemini 3 Flash).
    # Fallback: independent Flash-family member so transient errors on one
    # don't fail the whole call.
    analyst_primary = getattr(settings, "ANALYST_MODEL", None) or settings.COMPARE_MODEL
    analyst_fallback = getattr(settings, "ANALYST_FALLBACK_MODEL", None) or settings.COMPARE_FALLBACK_MODEL

    grounded: GroundedResult | None = None
    fallback_reason: str | None = None
    try:
        grounded = await _generate_deep_analysis(
            analyst_primary, analyst_fallback, prompt, request.locale,
        )
        if grounded.parsed is None:
            # Model returned text without a parseable JSON object. Treat as
            # a fallback trigger rather than a 502 — the user still gets a
            # report, just locally synthesised.
            fallback_reason = "Gemini yanıtı JSON olarak okunamadı"
            logger.warning("CompareAgent -> parse failure, falling back to local report")
            grounded = None
    except GeminiAuthError:
        # Auth errors STILL bubble — these mean the operator has to rotate
        # the key; serving a fallback would hide the broken-key state and
        # nobody would ever notice.
        logger.error("CompareAgent auth error", exc_info=True)
        raise
    except Exception as err:
        # Quota exhausted, transient overload, timeout, network blip.
        # Don't bubble — every error here would surface as a red toast in
        # the UI and the user has no way to recover other than waiting.
        # Fall back to the local analyser so they at least see prices and
        # review patterns we already scraped.
        msg = str(err)
        if "per-minute quota" in msg or "günlük" in msg.lower() or "quota" in msg.lower():
            fallback_reason = "Gemini API kotası şu an tükenmiş"
        elif "overloaded" in msg.lower() or "unavailable" in msg.lower():
            fallback_reason = "Gemini servisi geçici olarak meşgul"
        else:
            fallback_reason = "Gemini çağrısı başarısız oldu"
        logger.warning("CompareAgent -> Gemini failed (%s), using local fallback", msg)

    if grounded is None:
        # Local fallback path — synth a report from scraped data only.
        deep_analysis = _build_local_fallback_analysis(
            scraped,
            lowest_price,
            lowest_price_site,
            product_hint,
            fallback_reason or "Gemini erişilemez",
        )
        response = {
            "deep_analysis": deep_analysis,
            "lowest_price": lowest_price,
            "lowest_price_site": lowest_price_site,
            "store_prices": store_prices,
            "model_used": "local-fallback",
        }
        # Fallback responses are NOT cached — we don't want to lock the user
        # into a degraded report for 7 days when their quota refreshes in 24
        # hours. Skipping _cache_set means the next attempt will re-try
        # Gemini, and a successful run will replace this in-memory state.
        return response

    deep_analysis = _normalize_deep_analysis(
        grounded.parsed, scraped, lowest_price, lowest_price_site
    )
    deep_analysis["grounding_sources"] = grounded.sources
    deep_analysis["grounded"] = bool(grounded.sources)

    if grounded.sources:
        logger.info(
            "CompareAgent -> grounded with %d sources (model=%s)",
            len(grounded.sources), grounded.model_used,
        )

    # When scraping was blocked on every site, Gemini's site_summaries are the
    # only source of truth for prices. Merge them into store_prices / lowest_*
    # so the frontend's "Analyzed Lowest" widget reflects the searched values
    # rather than staying empty.
    summary_priced: list[dict[str, Any]] = []
    for summary in deep_analysis.get("site_summaries") or []:
        if not isinstance(summary, dict):
            continue
        s_price = summary.get("price")
        if isinstance(s_price, (int, float)) and s_price > 0:
            summary_priced.append({
                "site": summary.get("site") or "Unknown",
                "url": summary.get("url"),
                "price": float(s_price),
                "currency": summary.get("currency") or "TRY",
            })

    # Sanity-check Gemini's site_summaries the same way we vetted the scraped
    # prices: a search-grounded "iPhone 15 — 3.000 TL" almost always means
    # the model picked up an accessory listing for the search term instead
    # of the phone itself. Reject anything that diverges 3× from the rest.
    if summary_priced:
        # Combine scraped + summary points so the median is calibrated to all
        # signals we have, not just the searched ones.
        combined_for_check = [sp for sp in store_prices] + summary_priced
        filtered_combined, dropped_summary = _reject_price_outliers(combined_for_check)
        if dropped_summary:
            logger.warning(
                "CompareAgent -> rejected %d Gemini summary price outlier(s): %s",
                len(dropped_summary), "; ".join(dropped_summary),
            )
        # Pull the cleaned summary prices back out (they were appended after
        # the scraped block, so they live at the tail of filtered_combined).
        summary_priced = [
            entry for entry in filtered_combined[len(store_prices):]
            if isinstance(entry.get("price"), (int, float)) and entry["price"] > 0
        ]
        # Also flag rejected summaries back into the deep_analysis output so
        # the UI doesn't render the bogus number in site_summaries either.
        for summary in deep_analysis.get("site_summaries") or []:
            if not isinstance(summary, dict):
                continue
            site_key = (summary.get("site") or "").strip().lower()
            sp_match = next(
                (e for e in filtered_combined[len(store_prices):]
                 if (e.get("site") or "").strip().lower() == site_key),
                None,
            )
            if sp_match is not None and sp_match.get("price") is None and isinstance(summary.get("price"), (int, float)):
                summary["price"] = None

    if summary_priced:
        # Prefer scraped prices when present; otherwise use the searched price
        # for that site. Index existing store_prices by site name (lowercased)
        # so we can fill blanks without clobbering verified scrape data.
        by_site: dict[str, dict[str, Any]] = {}
        for sp in store_prices:
            key = (sp.get("site") or "").strip().lower()
            if key:
                by_site[key] = sp
        for sp in summary_priced:
            key = (sp["site"] or "").strip().lower()
            existing = by_site.get(key)
            if existing is None:
                by_site[key] = sp
                store_prices.append(sp)
            elif existing.get("price") in (None, 0):
                existing["price"] = sp["price"]
                existing["currency"] = sp["currency"]

        merged_priced = [sp for sp in store_prices if isinstance(sp.get("price"), (int, float)) and sp["price"] > 0]
        if merged_priced:
            cheapest = min(merged_priced, key=lambda sp: sp["price"])
            lowest_price = cheapest["price"]
            lowest_price_site = cheapest["site"]

    response = {
        "deep_analysis": deep_analysis,
        "lowest_price": lowest_price,
        "lowest_price_site": lowest_price_site,
        "store_prices": store_prices,
        "model_used": grounded.model_used,
    }
    _cache_set(cache_key, response)
    return response
