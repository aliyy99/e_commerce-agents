"""
╔══════════════════════════════════════════════════════════════╗
║          DETECTIVE AGENT  –  Live Marketplace Search         ║
╠══════════════════════════════════════════════════════════════╣
║  RESPONSIBILITIES:                                           ║
║  ▸ Take search_keywords from the Vision Agent (or the user). ║
║  ▸ Search Turkish marketplaces live (Vatan, MediaMarkt).     ║
║  ▸ Let Gemini (DETECTIVE_MODEL) keep only listings that are  ║
║    the product itself — not cases, chargers or other models. ║
║  ▸ Open the matched product pages to collect real ratings    ║
║    and reviews.                                              ║
║  ▸ If nothing matches, shorten the keywords and retry        ║
║    (agentic fallback).                                       ║
╚══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote

import httpx

from ..config import settings
from ..models.requests import CompareSiteData, DetectiveRequest
from ..models.responses import DetectiveResponse, AgentStatus, StoreResult
from ..services.gemini_client import GeminiAuthError
from ..services.gemini_grounded import call_gemini
from .compare_agent import _ACCEPT_ENCODING, _USER_AGENT, _scrape_one

logger = logging.getLogger("technotrack.detective_agent")

_MAX_RETRIES = 3
_MAX_CANDIDATES_PER_STORE = 12
# Product pages opened for reviews (each is one scrape, kept small).
_MAX_REVIEW_PAGES = 3

# Titles containing these are accessories for the searched product; used by
# the keyword fallback when Gemini is unavailable.
_ACCESSORY_WORDS = (
    "kılıf", "kilif", "kapak", "case", "cover", "ekran koruyucu", "cam ",
    "şarj", "sarj", "adaptör", "adaptor", "kablo", "cable", "lens koruyucu",
    "tutucu", "stand", "askı", "aski", "film",
)

_RELEVANCE_SYSTEM = """
You are the Detective Agent of a Turkish price-comparison app. You receive a
search query and marketplace listings. Decide which listings ARE the product
the shopper is looking for.

Rules:
- Keep a listing only if it is the product itself — a different colour of the
  same model counts as a match.
- Reject accessories (cases, screen protectors, chargers, cables, straps),
  bundles built around a different product, and different models or
  generations (e.g. "iPhone 16 Pro" when the query is "iPhone 16", or
  "Galaxy S24" when the query is "Galaxy S25").
- If the query names a storage / RAM variant, reject listings that clearly
  state a different one; keep listings that do not mention it.
- Respond with ONE JSON object: {"matches": [<listing ids>], "reason": "<one short sentence>"}.
""".strip()


def _clean_text(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))).strip()


def _parse_try_price(raw: Any) -> Optional[float]:
    """'72.999' / '72.999,90' / 70499 → float TRY."""
    if isinstance(raw, (int, float)):
        return float(raw) if raw > 0 else None
    text = str(raw or "").strip()
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        value = float(re.sub(r"[^\d.]", "", text))
    except ValueError:
        return None
    return value if value > 0 else None


def _parse_rating(raw: Any) -> Optional[float]:
    try:
        return float(str(raw).replace(",", ".")) if raw not in (None, "") else None
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────
# Marketplace search parsers
# ─────────────────────────────────────────────────────────────
async def _search_vatan(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    url = f"https://www.vatanbilgisayar.com/arama/{quote(query)}/"
    resp = await client.get(url)
    resp.raise_for_status()
    out: list[dict[str, Any]] = []
    # Each result card starts with this wrapper; the price inside an HTML
    # comment is a duplicate, so comments are stripped first.
    body = re.sub(r"<!--.*?-->", "", resp.text, flags=re.S)
    for card in re.split(r'<div class="product-list product-list--list-page', body)[1:]:
        link = re.search(r'class="product-list-link"\s+href="([^"]+)"', card)
        name = re.search(r'class="product-list__product-name">\s*<h3>(.*?)</h3>', card, re.S)
        price = re.search(r"class=['\"]product-list__price['\"]>([\d.,]+)<", card)
        score = re.search(r'class="product-card-bottom__score">([\d,]+)<', card)
        if not (link and name and price):
            continue
        out.append({
            "store": "Vatan Bilgisayar",
            "title": _clean_text(name.group(1)),
            "price": _parse_try_price(price.group(1)),
            "url": link.group(1),
            "rating": _parse_rating(score.group(1)) if score else None,
        })
        if len(out) >= _MAX_CANDIDATES_PER_STORE:
            break
    return out


async def _search_mediamarkt(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    url = f"https://www.mediamarkt.com.tr/tr/search.html?query={quote(query)}"
    resp = await client.get(url)
    resp.raise_for_status()
    out: list[dict[str, Any]] = []
    for block in re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', resp.text, flags=re.S
    ):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "ItemList":
            continue
        for element in data.get("itemListElement") or []:
            item = (element or {}).get("item") or {}
            offers = item.get("offers") or {}
            rating = (item.get("aggregateRating") or {}).get("ratingValue")
            if not item.get("name") or not item.get("url"):
                continue
            out.append({
                "store": "MediaMarkt",
                "title": _clean_text(item["name"]),
                "price": _parse_try_price(offers.get("price")),
                "url": item["url"],
                "rating": _parse_rating(rating),
            })
            if len(out) >= _MAX_CANDIDATES_PER_STORE:
                return out
    return out


_SEARCHERS = {
    "Vatan Bilgisayar": _search_vatan,
    "MediaMarkt": _search_mediamarkt,
}


async def _search_store(client: httpx.AsyncClient, name: str, query: str) -> list[dict[str, Any]]:
    """Search one store, dropping trailing words while it finds nothing.

    Store search engines are literal: Vision keywords such as "Apple iPhone 15
    Blue" return nothing on Vatan ("Mavi" there) while "Apple iPhone 15" works.
    """
    variants = [query]
    words = query.split()
    while len(words) > 2 and len(variants) < 3:
        words = words[:-1]
        variants.append(" ".join(words))
    for variant in variants:
        results = await _SEARCHERS[name](client, variant)
        if results:
            return results
    return []


async def _search_all(client: httpx.AsyncClient, query: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Run every marketplace search in parallel; a failing store is skipped."""
    names = list(_SEARCHERS)
    results = await asyncio.gather(*(_search_store(client, n, query) for n in names), return_exceptions=True)
    listings: list[dict[str, Any]] = []
    errors: list[str] = []
    for name, res in zip(names, results):
        if isinstance(res, Exception):
            logger.warning("DetectiveAgent → %s search failed: %s", name, res)
            errors.append(f"{name}: {type(res).__name__}")
            continue
        listings.extend(r for r in res if r.get("price"))
    return listings, errors


# ─────────────────────────────────────────────────────────────
# Relevance filtering
# ─────────────────────────────────────────────────────────────
def _keyword_match(query: str, listings: list[dict[str, Any]]) -> list[int]:
    """Fallback filter: every query token in the title, no accessory words."""
    tokens = [t for t in re.split(r"\W+", query.lower()) if t]
    keep = []
    for idx, item in enumerate(listings):
        title = item["title"].lower()
        if all(t in title for t in tokens) and not any(w in title for w in _ACCESSORY_WORDS):
            keep.append(idx)
    return keep


async def _select_matches(query: str, listings: list[dict[str, Any]]) -> tuple[list[int], str]:
    """Ask Gemini which listings are the product; fall back to keywords."""
    catalog = [
        {"id": idx, "store": item["store"], "title": item["title"], "price_try": item["price"]}
        for idx, item in enumerate(listings)
    ]
    prompt = (
        f'Search query: "{query}"\n\nListings:\n'
        f"{json.dumps(catalog, ensure_ascii=False, indent=1)}"
    )
    try:
        result = await call_gemini(
            settings.DETECTIVE_MODEL,
            settings.DETECTIVE_FALLBACK_MODEL,
            system=_RELEVANCE_SYSTEM,
            user_prompt=prompt,
            use_search=False,
            response_json=True,
            max_output_tokens=4096,
            temperature=0.0,
            thinking_level="low",
            timeout_seconds=60.0,
        )
        ids = (result.parsed or {}).get("matches") or []
        valid = sorted({int(i) for i in ids if str(i).isdigit() and int(i) < len(listings)})
        return valid, result.model_used
    except GeminiAuthError:
        raise
    except Exception as err:
        logger.warning("DetectiveAgent → Gemini relevance check failed (%s); using keyword match.", err)
        return _keyword_match(query, listings), "keyword-match"


async def _collect_reviews(
    client: httpx.AsyncClient, matches: list[dict[str, Any]]
) -> list[str]:
    """Open up to _MAX_REVIEW_PAGES matched product pages and pool their reviews."""
    # Prefer one page per store first, then fill with the remaining matches.
    picked: list[dict[str, Any]] = []
    for store in dict.fromkeys(m["store"] for m in matches):
        picked.append(next(m for m in matches if m["store"] == store))
    picked += [m for m in matches if m not in picked]
    picked = picked[:_MAX_REVIEW_PAGES]

    semaphore = asyncio.Semaphore(3)
    pages = await asyncio.gather(
        *(_scrape_one(client, CompareSiteData(site=m["store"], url=m["url"]), semaphore) for m in picked),
        return_exceptions=True,
    )
    reviews: list[str] = []
    for page in pages:
        if isinstance(page, Exception):
            continue
        for review in page.get("reviews") or []:
            text = str(review).strip()
            if text and text not in reviews:
                reviews.append(text)
    return reviews


# ─────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────
async def run_detective_agent(
    request: DetectiveRequest,
    emit_status=None,
    *,
    collect_reviews: bool = True,
) -> DetectiveResponse:
    """
    AGENT: Detective Agent
    ──────────────────────────────────────
    Live marketplace search → Gemini relevance check → review collection,
    shortening the keywords when a search comes back empty. Callers that only
    need current prices pass ``collect_reviews=False`` to skip the page visits.
    """
    logger.info("DetectiveAgent → starting (keywords=%r)", request.product_keywords)

    async def status(msg: str) -> None:
        if emit_status:
            await emit_status(msg)

    await status(f"Detective Agent searching {', '.join(_SEARCHERS)}: {request.product_keywords}")

    current_query = request.product_keywords.strip()
    retries = 0
    matches: list[dict[str, Any]] = []
    model_used: Optional[str] = None
    last_errors: list[str] = []

    timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=20.0)
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept-Encoding": _ACCEPT_ENCODING,
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        while True:
            listings, last_errors = await _search_all(client, current_query)
            logger.info("DetectiveAgent → %d listings for %r", len(listings), current_query)
            if listings:
                await status(f"{len(listings)} listings found, checking which ones are the exact product...")
                ids, model_used = await _select_matches(current_query, listings)
                matches = [listings[i] for i in ids]
            if matches:
                break

            # Agentic fallback: drop the most specific (last) word and retry.
            words = current_query.split()
            if retries >= _MAX_RETRIES or len(words) <= 1:
                break
            current_query = " ".join(words[:-1])
            retries += 1
            await status(f"No matching listing, retrying with shortened keywords: {current_query}")

        if not matches:
            detail = "No matching listing found on the searched marketplaces."
            if last_errors:
                detail += " Failed stores: " + ", ".join(last_errors)
            return DetectiveResponse(
                status=AgentStatus.ERROR,
                query_used=current_query,
                retries=retries,
                stores_searched=list(_SEARCHERS),
                model_used=model_used,
                error_detail=detail,
            )

        matches.sort(key=lambda m: m["price"])
        reviews: list[str] = []
        if collect_reviews:
            await status(f"{len(matches)} matching listings; reading customer reviews...")
            reviews = await _collect_reviews(client, matches)

    await status(f"Prices from {len({m['store'] for m in matches})} store(s) and {len(reviews)} reviews collected.")

    return DetectiveResponse(
        status=AgentStatus.SUCCESS if retries == 0 else AgentStatus.FALLBACK,
        query_used=current_query,
        retries=retries,
        found_prices=[
            StoreResult(store=m["store"], price=m["price"], url=m["url"], title=m["title"], rating=m["rating"])
            for m in matches
        ],
        reviews_found=reviews,
        stores_searched=list(_SEARCHERS),
        model_used=model_used,
    )
