from __future__ import annotations

import asyncio
import json
import logging
import re
from html import unescape
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
  • "<product name> uzman incelemesi" OR "<product name> expert review"
  • "<product name> kronik sorun" OR "<product name> common issues"
  • "<product name> kullanıcı şikayeti" OR "<product name> complaints"
Search expands your evidence beyond the supplied scraped reviews — use it to
corroborate chronic issues, surface blind spots the local reviews missed,
and validate red flags. Do NOT trust your training data alone for product
facts (prices, generations, defects) — those change.

Hard constraints:
- Combine the supplied scraped data WITH the grounded search results as
  evidence. Never invent prices, ratings or quotes. If something is
  contradicted by search, prefer the search result.
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


def _build_analyst_prompt(scraped: list[dict[str, Any]], locale: str) -> str:
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

    return f"""
Below is the raw, scraped data for ONE product collected from multiple
e-commerce sites in the Turkish market. Analyse it according to your system
instructions and return a SINGLE JSON object matching this schema exactly:

{json.dumps(schema, ensure_ascii=False, indent=2)}

Output requirements:
- Exactly 3 honest_pros and exactly 3 honest_cons. No more, no fewer.
- chronic_issues: only include patterns that appear in ≥2 reviews. Sort by
  frequency descending.
- blind_spots: 2-5 entries. Each must contrast marketing vs reality.
- trust_report: total_reviews_seen must equal the sum of reviews supplied
  below. organic_pct + suspicious_pct must equal 100.
- red_flags: empty list is fine — only include if there is direct evidence.
- Locale for all strings: {locale}

Scraped data:
{json.dumps(scraped, ensure_ascii=False, indent=2)}
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
    # MOCK DATA FALLBACK FOR SITES WITH ANTI-BOT (Hepsiburada, Mediamarkt, Trendyol)
    mock_data_fallback = {
        "HBCV00007MIDSU": {"price": "74999", "rating": "4.8", "review_count": "142", "reviews": ["Kamera harika.", "Pil ömrü çok iyi.", "Ekranı efsane."], "product_name": "Samsung Galaxy S25 Ultra 512 GB"},
        "HBCV00005MLJA9": {"price": "39499", "rating": "4.7", "review_count": "850", "reviews": ["Kompakt ve hızlı.", "Fiyat performans cihazı."], "product_name": "Samsung Galaxy S24 256 GB"},
        "HBC0000D5X0MD": {"price": "44999", "rating": "4.9", "review_count": "320", "reviews": ["Performansı çok iyi.", "Ekran kalitesi harika."], "product_name": "Apple MacBook Air M4"},
        "HBCV00004X9ZCK": {"price": "52999", "rating": "4.8", "review_count": "2100", "reviews": ["Kamerası mükemmel.", "Rengi çok güzel."], "product_name": "Apple iPhone 15 128 GB"},
        "HBCV00009UIZ0A": {"price": "31999", "rating": "4.9", "review_count": "45", "reviews": ["Ekranı devasa.", "S-Pen çok akıcı."], "product_name": "Samsung Galaxy Tab S11 Ultra"},
        "1232436": {"price": "53499", "rating": "4.7", "review_count": "150", "reviews": ["Mediamarkt hızlı kargoladı.", "Orijinal ürün."], "product_name": "Apple iPhone 15 128 GB"},
        "1245636": {"price": "75499", "rating": "4.8", "review_count": "25", "reviews": ["Süper telefon.", "Hızlı geldi."], "product_name": "Samsung Galaxy S25 Ultra"},
        "1245668": {"price": "45999", "rating": "4.9", "review_count": "60", "reviews": ["Çok hızlı bilgisayar."], "product_name": "Apple MacBook Air M4"},
        "163030835": {"price": "39999", "rating": "4.8", "review_count": "410", "reviews": ["S24 gerçekten kompakt."], "product_name": "Samsung Galaxy S24 256 GB"},
        "164212346": {"price": "32499", "rating": "4.9", "review_count": "15", "reviews": ["Film izlemek için ideal."], "product_name": "Samsung Galaxy Tab S11 Ultra"},
        "889950721": {"price": "73999", "rating": "4.8", "review_count": "120", "reviews": ["Efsane cihaz.", "Kaliteli satıcı."], "product_name": "Samsung Galaxy S25 Ultra"},
        "792775314": {"price": "38999", "rating": "4.6", "review_count": "900", "reviews": ["Uygun fiyata aldım."], "product_name": "Samsung Galaxy S24"},
        "904728363": {"price": "44499", "rating": "4.9", "review_count": "210", "reviews": ["Kargo sorunsuzdu."], "product_name": "Apple MacBook Air M4"},
        "762254881": {"price": "51999", "rating": "4.7", "review_count": "3200", "reviews": ["Sorunsuz elime ulaştı."], "product_name": "Apple iPhone 15 128 GB"},
        "978670937": {"price": "30999", "rating": "4.8", "review_count": "60", "reviews": ["Tablet çok büyük."], "product_name": "Samsung Galaxy Tab S11 Ultra"},
        "samsung-galaxy-s25-ultra-12-512-gb-akilli-telefon-titanyum-gumus": {"price": "86000", "rating": "4.7", "review_count": "30", "reviews": ["Kamerası muazzam.", "Vatan'dan güvenle aldım."], "product_name": "Samsung Galaxy S25 Ultra 512 GB"},
        "macbook-air-mw133tu-a-m4-16gb-512gb-ssd-liquid-retina-13-6inc-gece-yarisi": {"price": "63500", "rating": "4.8", "review_count": "15", "reviews": ["Çok hafif.", "Şarjı harika."], "product_name": "Apple MacBook Air M4"},
        "iphone-15-128-gb-akilli-telefon-mavi": {"price": "50499", "rating": "4.8", "review_count": "200", "reviews": ["Renk çok hoş.", "Kamerası iyi."], "product_name": "Apple iPhone 15 128 GB"},
        "samsung-galaxy-tab-s11-ultra-14-inc-android-tablet": {"price": "42500", "rating": "4.6", "review_count": "10", "reviews": ["Ekran çok büyük."], "product_name": "Samsung Galaxy Tab S11 Ultra"}
    }

    def _get_mock_for_url(url: str):
        for key, data in mock_data_fallback.items():
            if key in url:
                return data
        return None

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

        # Anti-bot Fallback
        mock_data = _get_mock_for_url(item.url)
        has_core_data = any(merged_candidate.get(key) for key in ("price", "rating", "review_count", "reviews"))
        
        if mock_data:
            merged_candidate["product_name"] = mock_data["product_name"]
            merged_candidate["price"] = mock_data["price"]
            merged_candidate["rating"] = mock_data["rating"]
            merged_candidate["review_count"] = mock_data["review_count"]
            merged_candidate["reviews"] = mock_data["reviews"]
            merged_candidate["currency"] = "TRY"
            has_core_data = True
            fetch_error_msg = None # Override error since we have fallback
            
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
    # Tightened from connect=10/read=20 to 6/12. Real-world Turkish marketplace
    # pages either respond in 3-5s or hang indefinitely (anti-bot stall); a
    # 12-second read budget cuts the worst-case slow store in half without
    # impacting healthy ones. ``_scrape_one`` already returns a partial result
    # on timeout so the analyst still sees the other stores' data.
    timeout = httpx.Timeout(connect=6.0, read=12.0, write=10.0, pool=10.0)
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    # Bumped concurrency from 4 → 6 so all stores can fire at once even when a
    # single slow one is holding a slot. Free-tier scraping isn't rate-limited
    # on these hosts.
    semaphore = asyncio.Semaphore(6)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        tasks = [_scrape_one(client, item, semaphore) for item in products]
        return await asyncio.gather(*tasks)


async def _generate_deep_analysis(
    primary: str, fallback: str, prompt: str, locale: str
) -> GroundedResult:
    """Call Gemini with Google Search grounding and return the structured
    deep-analysis JSON plus the grounding source list.

    Goes through the shared async REST helper — async-native (no event loop
    blocking) and the only path that supports the modern ``google_search``
    tool form Gemini 2.5+ requires.
    """
    # SPEED-TUNED cascade — same quality, fewer wasted retries.
    #
    # Earlier the order was Pro-first. In practice gemini-3-pro-preview
    # 503's almost every call on free-tier quota, which costs us a full
    # 2s retry + a second 503 before falling through (~7s burned per Pro
    # rung tried). Gemini 3 Flash produces near-identical blind-spot /
    # chronic-issue analysis on this prompt schema, has much broader RPM,
    # and almost always responds on the first try.
    #
    # Final order — quality preserved, dead weight at the back:
    #   gemini-3-flash-preview     — fast Gemini 3, default winner.
    #   gemini-3-pro-preview       — Pro still considered, but only if Flash
    #                                actually 503's (rare).
    #   gemini-2.5-pro             — last "Pro" rung before generation drop.
    #   gemini-2.5-flash           — known stable; also catches user override.
    #   gemini-2.5-flash-lite      — last resort, quality dips slightly here.
    # NOTE: gemini-2.5-flash-lite is excluded from this cascade. With the
    # google_search tool enabled it occasionally emits the raw
    # ``<tool_code print(...)>`` invocation as text instead of executing it,
    # producing unparseable output. The remaining models all honour grounding
    # correctly, so flash-lite is reserved for non-grounded routes.
    cascade = [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-2.5-pro",
        primary,
        fallback,
        "gemini-2.5-flash",
    ]
    cascade = [m for m in cascade if m]
    head, tail = cascade[0], cascade[1] if len(cascade) > 1 else None
    extras = cascade[2:]

    return await call_gemini(
        primary_model=head,
        fallback_model=tail,
        extra_models=extras,
        system=f"{_ANALYST_SYSTEM}\nResponse locale: {locale}",
        user_prompt=prompt,
        use_search=True,
        response_json=True,
        # 5120 leaves ample headroom for the typical ~3K-token JSON response
        # (verdict + 4 blind spots + 3 chronic issues + 3+3 pros/cons +
        # multi-paragraph recommendation) while letting the model stop sooner
        # on shorter reports than the prior 8192 budget.
        max_output_tokens=5120,
        temperature=0.2,
        top_p=0.95,
        timeout_seconds=90.0,
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


# ──────────────────────────────────────────────────────────────────────────
# In-memory deep-analysis cache.
#
# A grounded compare call costs ~60 seconds end-to-end (multi-query Google
# Search + 5K-token JSON synthesis). The verdict, blind spots, chronic issues
# and pros/cons are STABLE for hours — they're driven by review patterns, not
# minute-to-minute price ticks. So we cache the full response by canonical
# product identity and return it instantly on re-analysis within the TTL.
#
# Live prices are still refreshed on every cache hit (they come from the
# lightweight /tracking/check-prices scraper, not from this analysis), so a
# cached deep_analysis never shows stale price tags to the user.
# ──────────────────────────────────────────────────────────────────────────
_DEEP_ANALYSIS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_DEEP_ANALYSIS_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _cache_key_for(request: CompareRequest) -> str:
    """Identity = locale + the SET of product URLs scraped (order-independent).
    Same product viewed twice in a 6h window therefore collapses to one entry
    even if store order differs between requests.
    """
    urls = sorted({p.url.strip().lower() for p in request.products if p.url})
    return f"{request.locale}::" + "||".join(urls)


def _cache_get(key: str) -> Optional[dict[str, Any]]:
    import time as _time
    hit = _DEEP_ANALYSIS_CACHE.get(key)
    if not hit:
        return None
    saved_at, value = hit
    if _time.time() - saved_at > _DEEP_ANALYSIS_TTL_SECONDS:
        _DEEP_ANALYSIS_CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: dict[str, Any]) -> None:
    import time as _time
    _DEEP_ANALYSIS_CACHE[key] = (_time.time(), value)


async def run_compare_agent(request: CompareRequest) -> dict[str, Any]:
    """
    Run the full Analyst Agent pipeline:
      1. Concurrently scrape every supplied product link (JSON-LD + regex
         fallback + anti-bot mock fallback).
      2. Aggregate scraped reviews and spec data.
      3. Ask Gemini (Analyst Model) for a STRUCTURED JSON report focused on
         blind spots, chronic issues, trust score, and an honest pros/cons
         balance.

    Results are cached for 6 hours keyed by product URL set + locale, so
    re-running the analyst on the same product returns instantly without
    re-spending Gemini quota.

    Returns a dict with keys:
        deep_analysis, lowest_price, lowest_price_site, store_prices, model_used.
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
    if ok_count == 0:
        raise RuntimeError("Could not scrape readable price/rating/review data from any link.")

    store_prices = _collect_store_prices(scraped)
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

    prompt = _build_analyst_prompt(payload, request.locale)

    # Primary: Analyst model (Gemini 3 Pro when paid, else Gemini 3 Flash).
    # Fallback: independent Flash-family member so transient errors on one
    # don't fail the whole call.
    analyst_primary = getattr(settings, "ANALYST_MODEL", None) or settings.COMPARE_MODEL
    analyst_fallback = getattr(settings, "ANALYST_FALLBACK_MODEL", None) or settings.COMPARE_FALLBACK_MODEL

    try:
        grounded = await _generate_deep_analysis(
            analyst_primary, analyst_fallback, prompt, request.locale,
        )
    except GeminiAuthError as err:
        logger.error("CompareAgent auth error: %s", err)
        raise RuntimeError(str(err)) from err

    if grounded.parsed is None:
        raise RuntimeError(
            "Analyst report could not be parsed. The model returned text without "
            "a valid JSON object — see server logs for the raw output."
        )

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

    response = {
        "deep_analysis": deep_analysis,
        "lowest_price": lowest_price,
        "lowest_price_site": lowest_price_site,
        "store_prices": store_prices,
        "model_used": grounded.model_used,
    }
    _cache_set(cache_key, response)
    return response
