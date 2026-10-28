"""Backend-for-Frontend Gemini wrappers (chat assistant).

The chat runs on the CHAT_MODEL → CHAT_FALLBACK_MODEL → shared extra-rung
ladder through ``gemini_grounded.call_gemini``. Timing / price questions are
grounded with Google Search when the key allows it; otherwise price questions
get today's real marketplace prices from the Detective Agent injected into the
context, and the model is told it has no web access.
"""
import json
import logging
import re

from ..config import settings
from ..models.requests import ChatRequest, DetectiveRequest
from ..models.responses import AgentStatus
from .gemini_client import GeminiAuthError
from .gemini_grounded import call_gemini

logger = logging.getLogger("technotrack.services.gemini_proxy")

_CHAT_SYSTEM = """
You are Techno Track Assistant, a highly intelligent and helpful shopping guide.
Your goal is to help users make informed purchasing decisions based on the product analysis data provided to you.
Be concise, friendly, and data-driven. Always refer to the provided context data when answering.

PRICE GROUNDING RULES — read carefully:
1. If the context contains a ``price_history`` block (12-month chart data
   produced by the Price Graphic), it is the AUTHORITATIVE source for ANY
   price-related answer. Quote its ``lowest`` / ``highest`` / ``average`` /
   latest-month value verbatim. Do NOT invent or contradict these figures.
   When ``price_history.grounded`` is false, only the latest month (note
   "live: <store>") is a real price; earlier months are model estimates —
   say so if you quote them.
2. If the context contains ``live_prices`` (fetched moments ago from Turkish
   marketplaces), those are the current real prices — quote them with the
   store name. They win over any ``stores`` array from the catalog.
3. If the context contains a ``stores`` array (per-retailer prices), you may
   cite those alongside the chart but the chart still wins on disputes.
{price_lookup_rule}
5. Other non-price topics (specs, features, comparisons, advice) — answer
   normally from the context and your own knowledge.

If the context data shows that prices are dropping or an item is overpriced, warn the user.
If the analyst agent found bot reviews or chronic issues (Kronik Sorunlar), mention them.
If the user asks "Bu ürün fiyatına değer mi?" or similar, answer clearly (e.g., "Evet, çünkü..." or "Hayır, bekle...").

ANALYST REPORT RULES — apply only when ``analyst_report`` is in the context:
- ``analyst_report`` is the structured output of the Analyst Agent and is the
  AUTHORITATIVE source for:
    • verdict (BUY / WAIT / AVOID) and confidence
    • blind spots (advertised vs. reality limitations)
    • chronic_issues (recurring complaints with frequency + severity)
    • trust_report (organic_pct / suspicious_pct / trust_score)
    • honest_pros and honest_cons (exactly 3 of each)
    • red_flags (critical warnings)
- When the user asks "why should/shouldn't I buy this?", "are reviews real?",
  "what are the issues?", or anything similar — answer FROM this block and
  cite the concrete fact (e.g. "Trust score 64/100; %36 yorum şüpheli").
- Never contradict a chronic_issue/blind_spot listed there. If the user pushes
  back, repeat the verbatim evidence already in the report.

CAMPAIGNS RULES — apply only when ``campaigns`` is in the context:
- ``campaigns.coupons`` is the AUTHORITATIVE list of the user's currently
  available discount codes / promotions. Each item has: ``store_id``,
  ``store_name``, ``title``, ``description``, optional ``code``,
  ``discount_label``, ``category`` and ``expires_label``.
- ``campaigns.news`` is the AUTHORITATIVE list of fresh tech-pricing and
  product-launch headlines the user has loaded. Each item has: ``title``,
  ``summary``, ``category`` (price-drop | new-product | launch | deal |
  industry), optional ``date_label``, ``source`` and ``url``.
- ``campaigns.connected_accounts`` lists the e-commerce sites the user has
  linked (Hepsiburada, Trendyol, Vatan, ...). When recommending a coupon,
  always say WHICH store it belongs to.
- Some coupons may have ``is_sample=true`` — these are illustrative examples
  the platform shows by default. You can still recommend them, but if the
  user asks "bu kupon gerçek mi?" or pushes back, disclose that this is an
  example coupon and the live code may differ on the retailer's site.
- When the user asks "hangi kuponum var?", "indirim var mı?", "X üründe
  kampanya var mı?", "yeni bir ürün geliyor mu?" or anything similar, answer
  from this block FIRST. Quote the coupon code verbatim, name the store, and
  cite the discount_label and expire date.
- If the user asks for a deal but no matching coupon exists in
  ``campaigns.coupons``, say so honestly ("Şu anda bağlı hesaplarında
  X için aktif kupon yok") instead of inventing one. You may then suggest
  checking related news from ``campaigns.news`` if relevant.
- When considering price/timing/purchase advice, factor in any related
  coupon (extra discount) or news item (incoming price drop, new model on
  the way) before giving your final answer.

DEVICE COMPARISON RULES — apply only when ``device_comparison`` is in the context:
- ``device_comparison`` contains a full head-to-head report (overall_winner,
  per-row winners, scores, pros/cons, best_for, long summary). Treat this as
  the authoritative source on which device wins what.
- When the user asks "which one is better for X?" pick the device whose
  strengths or per-row wins clearly cover X (e.g. camera rows for photography,
  performance + thermals + display rows for gaming, battery + weight for
  travel) and give a 2-3 sentence justification citing the concrete spec or
  row that decides it.
- If the comparison data does not cover X, say so honestly and answer from
  general knowledge of the two named devices.
- Do NOT contradict the per-row winners in the report. If a row was a tie,
  call it a tie.
{timing_rule}
Respond in Turkish.
""".strip()

_SEARCH_PRICE_RULE = """4. If neither ``price_history`` nor ``live_prices`` is present AND the user asks
   about price, you MUST call the Google Search tool to look up current
   Turkish e-commerce prices (hepsiburada, trendyol, akakce, cimri,
   vatanbilgisayar, mediamarkt) before giving any number. Never quote a price
   from training data alone."""

_OFFLINE_PRICE_RULE = """4. You have NO web access in this conversation. If neither ``price_history``
   nor ``live_prices`` is present AND the user asks about price, say you
   could not verify today's price and suggest opening the Price Graphic.
   Never quote a price from training data."""

_SEARCH_TIMING_RULE = """When the user asks about WHEN to buy (timing, deals, upcoming sales, new model releases), use Google Search
to gather fresh real-world data (current promos, expected next-gen launch dates, recent price trends) and
ground your timing advice on those findings. Cite the key facts you used inline (e.g. "Eylül 2025'te yeni
model çıkacağı için ...")."""

_OFFLINE_TIMING_RULE = """When the user asks about WHEN to buy, base the advice on the context (price
history, live prices, campaigns news) and the product's usual release cycle, and make clear that upcoming
launch dates or sales are not verified live."""


def _chat_system(*, grounded: bool) -> str:
    return _CHAT_SYSTEM.format(
        price_lookup_rule=_SEARCH_PRICE_RULE if grounded else _OFFLINE_PRICE_RULE,
        timing_rule=_SEARCH_TIMING_RULE if grounded else _OFFLINE_TIMING_RULE,
    )


_TIMING_PATTERNS = re.compile(
    r"(ne zaman|şimdi mi al|şu an mı al|alay[ıi]m m[ıi]|bekleye?y?im mi|"
    r"erteleye?y?im|fiyat d[uü]ş[eü]r m[uü]|yeni model|yeni s[uü]r[uü]m|"
    r"kampanya ne zaman|bu fiyat[a]? de[gğ]er mi|when to buy|"
    r"should i (buy|wait)|right time|good time|upcoming (sale|release)|"
    r"next (model|version)|black friday|cyber monday|prime day|11\.11|sale)",
    re.IGNORECASE,
)

# Plain "what is the price / how much" style asks — distinct from timing.
# Triggers a live price lookup only when no price_history is in the context.
_PRICE_PATTERNS = re.compile(
    r"(fiyat[ıi]?|kaç (tl|lira|para)|ne kadar|kaça|"
    r"ucuz|pahal[ıi]|indirim|kampanya|en d[uü]ş[uü]k|en y[uü]ksek|ortalama|"
    r"price|cost|how much|cheapest|most expensive|average price|deal)",
    re.IGNORECASE,
)


def _is_timing_question(user_message: str) -> bool:
    """Heuristic: does the user need fresh web data to answer 'when to buy?'."""
    if not user_message:
        return False
    return bool(_TIMING_PATTERNS.search(user_message))


def _is_price_question(user_message: str) -> bool:
    """Heuristic: is the user asking about a price/cost figure?"""
    if not user_message:
        return False
    return bool(_PRICE_PATTERNS.search(user_message))


def _has_price_history(context_data) -> bool:
    """True when the frontend handed us a populated price_history block."""
    if not isinstance(context_data, dict):
        return False
    ph = context_data.get("price_history")
    if not isinstance(ph, dict):
        return False
    points = ph.get("points")
    return isinstance(points, list) and len(points) > 0


async def _live_prices(product_name: str) -> list[dict]:
    """Today's marketplace prices for the product in context (Detective Agent)."""
    # Imported lazily: the agents package imports routes that import this module.
    from ..agents.detective_agent import run_detective_agent

    try:
        result = await run_detective_agent(
            DetectiveRequest(product_keywords=product_name), collect_reviews=False,
        )
    except GeminiAuthError:
        raise
    except Exception as err:
        logger.warning("Chat live price lookup failed: %s", err)
        return []
    if result.status == AgentStatus.ERROR:
        return []
    return [
        {"store": p.store, "price_try": p.price, "title": p.title, "url": p.url}
        for p in result.found_prices[:6]
    ]


def _build_turns(request: ChatRequest, context_data) -> tuple[list[dict], str]:
    """Split the request into prior turns and the latest user message."""
    history = [
        {"role": "user" if msg.role == "user" else "model", "text": msg.content}
        for msg in request.history
    ]
    latest_message = request.user_message
    if context_data:
        context_str = json.dumps(context_data, ensure_ascii=False, indent=2)
        latest_message = f"Product Analysis Context Data:\n{context_str}\n\nUser Question:\n{request.user_message}"
    return history, latest_message


def _citations(sources: list[dict]) -> str:
    if not sources:
        return ""
    lines = [f"- [{s.get('title') or s['uri']}]({s['uri']})" for s in sources[:5]]
    return "\n\n**Kaynaklar:**\n" + "\n".join(lines)


async def generate_chat_reply(request: ChatRequest) -> str:
    """Proxy frontend chat payload to Gemini and return plain reply text."""
    context_data = dict(request.context_data) if isinstance(request.context_data, dict) else request.context_data
    has_chart = _has_price_history(context_data)
    price_question = _is_price_question(request.user_message) and not has_chart

    # Ground with Google Search when the user asks WHEN to buy, or asks about
    # price before any chart exists. For price questions also attach today's
    # real marketplace prices, so the answer is factual even without search.
    use_search = _is_timing_question(request.user_message) or price_question
    if price_question and isinstance(context_data, dict):
        product_name = context_data.get("product_name") or context_data.get("name")
        if product_name:
            live = await _live_prices(str(product_name))
            if live:
                context_data["live_prices"] = live

    history, latest_message = _build_turns(request, context_data)
    result = await call_gemini(
        settings.CHAT_MODEL,
        settings.CHAT_FALLBACK_MODEL,
        system=_chat_system(grounded=True),
        offline_system=_chat_system(grounded=False),
        user_prompt=latest_message,
        history=history,
        use_search=use_search,
        response_json=False,
        max_output_tokens=4096,
        temperature=0.6,
        thinking_level="low",
        timeout_seconds=90.0,
    )
    return result.text + _citations(result.sources)
