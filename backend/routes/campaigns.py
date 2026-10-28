"""
Techno Track AI - Campaigns Route
POST /api/v1/campaigns

Returns two feeds for the Campaigns page:

1. ``coupons``  – discount codes / promos for each e-commerce site the user has
   connected. Currently sourced from a curated per-store sample list so the
   panel is never empty; each item is tagged with the store it belongs to and
   ``is_sample=True`` for transparency.

2. ``news``     – fresh tech-pricing & product-launch headlines. With Google
   Search grounding (billed keys) Gemini researches them live. Without it
   (free tier) the Tech-News Agent reads today's RSS feeds of Turkish tech
   sites and Gemini only selects and summarises real articles — title link,
   source and date always come from the feed, never from the model.
   Model ladder: NEWS_MODEL → NEWS_FALLBACK_MODEL → shared extra rungs.
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..config import settings
from ..services.gemini_client import GeminiAuthError
from ..services.gemini_grounded import call_gemini

logger = logging.getLogger("technotrack.routes.campaigns")
router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


# ── Request / Response models ─────────────────────────────────────────────
class ConnectedAccount(BaseModel):
    id: str = Field(..., example="hepsiburada")
    name: str = Field(..., example="Hepsiburada")
    domain: Optional[str] = Field(None, example="hepsiburada.com")


class CampaignsRequest(BaseModel):
    connected_accounts: List[ConnectedAccount] = Field(default_factory=list)
    locale: str = Field(default="tr")


class CouponItem(BaseModel):
    id: str
    store_id: str = Field(..., description="Slug matching the connected account id.")
    store_name: str
    title: str
    description: str
    code: Optional[str] = None
    discount_label: Optional[str] = Field(
        None, description="Human-readable discount, e.g. '%15 indirim' or '2.000 ₺ indirim'."
    )
    category: Optional[str] = Field(
        None, description="Free-form: 'Elektronik', 'Telefon', 'Bilgisayar', etc."
    )
    expires_label: Optional[str] = Field(None, example="2 gün kaldı")
    url: Optional[str] = None
    is_sample: bool = Field(
        default=False,
        description="True when this coupon comes from the curated sample list (not a live web result).",
    )


class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    category: str = Field(
        ..., description="'price-drop' | 'new-product' | 'launch' | 'deal' | 'industry'"
    )
    date_label: Optional[str] = Field(None, example="Bugün")
    source: Optional[str] = None
    url: Optional[str] = None


class CampaignsSource(BaseModel):
    title: Optional[str] = None
    uri: str


class CampaignsResponse(BaseModel):
    coupons: List[CouponItem] = Field(default_factory=list)
    news: List[NewsItem] = Field(default_factory=list)
    sources: List[CampaignsSource] = Field(default_factory=list)
    model_used: str = ""
    grounded: bool = False


# ── Curated sample coupons per store ──────────────────────────────────────
# Each connected account gets 6 plausible coupons so the Coupons tab is never
# empty. Codes mimic the patterns these retailers use in real campaigns but
# the actual offers are illustrative — ``is_sample`` is set to True on output
# so the chat assistant can disclose this if the user asks.
_SAMPLE_COUPONS: dict[str, list[dict]] = {
    "hepsiburada": [
        {
            "title": "MacBook Air M3'te 2.000 ₺ İndirim",
            "description": "50.000 ₺ üzeri MacBook Air / Pro modellerinde anında indirim.",
            "code": "MAC2000",
            "discount_label": "2.000 ₺ indirim",
            "category": "Bilgisayar",
            "expires_label": "5 gün kaldı",
        },
        {
            "title": "Telefon Kategorisinde %10 Sepet İndirimi",
            "description": "Akıllı telefonlarda sepette otomatik %10 indirim (en fazla 1.500 ₺).",
            "code": "HBPHONE10",
            "discount_label": "%10 indirim",
            "category": "Telefon",
            "expires_label": "Bu hafta",
        },
        {
            "title": "Hepsiburada Premium Üyelere Ücretsiz Kargo",
            "description": "Premium üyeliğin aktifken tüm elektronik siparişlerde kargo bedava.",
            "code": None,
            "discount_label": "Kargo bedava",
            "category": "Tüm Kategoriler",
            "expires_label": "Süresiz",
        },
        {
            "title": "Kulaklık & Aksesuarda 250 ₺ İndirim",
            "description": "1.500 ₺ ve üzeri kulaklık alışverişlerinde geçerli sepet kuponu.",
            "code": "AKS250",
            "discount_label": "250 ₺ indirim",
            "category": "Aksesuar",
            "expires_label": "3 gün kaldı",
        },
        {
            "title": "Beyaz Eşyada 1.500 ₺ İndirim",
            "description": "Buzdolabı, çamaşır ve bulaşık makinelerinde sepet indirimi.",
            "code": "BEYAZ1500",
            "discount_label": "1.500 ₺ indirim",
            "category": "Beyaz Eşya",
            "expires_label": "Bugün son",
        },
        {
            "title": "Oyun Konsollarında 1.000 ₺ İndirim",
            "description": "PlayStation 5 ve Xbox Series modellerinde sepete özel indirim.",
            "code": "OYUN1000",
            "discount_label": "1.000 ₺ indirim",
            "category": "Oyun",
            "expires_label": "Stoklarla sınırlı",
        },
    ],
    "trendyol": [
        {
            "title": "İlk Siparişe Özel %20 İndirim",
            "description": "Hesabından yapacağın ilk elektronik siparişte sepette %20 indirim.",
            "code": "HOSGELDIN20",
            "discount_label": "%20 indirim",
            "category": "Elektronik",
            "expires_label": "Hesabına özel",
        },
        {
            "title": "Galaxy Telefonlarda 1.250 ₺ İndirim",
            "description": "Samsung Galaxy S / A serisi telefonlarda sepete özel indirim.",
            "code": "GALAXY1250",
            "discount_label": "1.250 ₺ indirim",
            "category": "Telefon",
            "expires_label": "4 gün kaldı",
        },
        {
            "title": "Trendyol Premium Kargo Bedava",
            "description": "Premium üyeliğin aktifken 150 ₺ altı dahil tüm siparişlerde kargo bedava.",
            "code": None,
            "discount_label": "Kargo bedava",
            "category": "Tüm Kategoriler",
            "expires_label": "Süresiz",
        },
        {
            "title": "Aksesuar Kategorisinde %25 İndirim",
            "description": "Şarj aleti, kılıf, kablo ürünlerinde sepete özel %25 indirim.",
            "code": "AKS25",
            "discount_label": "%25 indirim",
            "category": "Aksesuar",
            "expires_label": "Bu hafta",
        },
        {
            "title": "Süper İndirim Günleri – Laptop'ta 2.500 ₺",
            "description": "Seçili dizüstü bilgisayarlarda 30.000 ₺ üzeri alışverişlere 2.500 ₺ indirim.",
            "code": "SUPER2500",
            "discount_label": "2.500 ₺ indirim",
            "category": "Bilgisayar",
            "expires_label": "2 gün kaldı",
        },
        {
            "title": "Akıllı Saatlerde %15 İndirim",
            "description": "Apple Watch ve Galaxy Watch modellerinde sepete özel %15 indirim.",
            "code": "WATCH15",
            "discount_label": "%15 indirim",
            "category": "Giyilebilir Teknoloji",
            "expires_label": "Bugün son",
        },
    ],
    "vatan": [
        {
            "title": "Oyuncu Laptop'larında 1.500 ₺ İndirim",
            "description": "RTX 40 serisi ekran kartına sahip oyuncu laptoplarında sepet indirimi.",
            "code": "GAMERLAP1500",
            "discount_label": "1.500 ₺ indirim",
            "category": "Bilgisayar",
            "expires_label": "3 gün kaldı",
        },
        {
            "title": "Monitör Kategorisinde %15 İndirim",
            "description": "27\" ve üzeri tüm monitör modellerinde sepete özel %15 indirim.",
            "code": "MON15",
            "discount_label": "%15 indirim",
            "category": "Monitör",
            "expires_label": "Bu hafta",
        },
        {
            "title": "Kulaklıkta 500 ₺ İndirim",
            "description": "Sony, Bose ve JBL üst seviye kulaklıklarda 500 ₺ sepet indirimi.",
            "code": "KULAK500",
            "discount_label": "500 ₺ indirim",
            "category": "Aksesuar",
            "expires_label": "5 gün kaldı",
        },
        {
            "title": "PlayStation 5 Aksesuarda %20",
            "description": "DualSense, kulaklık ve dock'larda sepete özel %20 indirim.",
            "code": "PSEXTRA20",
            "discount_label": "%20 indirim",
            "category": "Oyun",
            "expires_label": "Hafta sonu",
        },
        {
            "title": "Akıllı Saatte 750 ₺ İndirim",
            "description": "Apple Watch Series 9 ve Galaxy Watch 6 modellerinde sepet indirimi.",
            "code": "SAAT750",
            "discount_label": "750 ₺ indirim",
            "category": "Giyilebilir Teknoloji",
            "expires_label": "4 gün kaldı",
        },
        {
            "title": "Vatan Klüp Üyelerine Hediye Çeki",
            "description": "Bu ay 5.000 ₺ üzeri alışverişe 250 ₺ hediye çeki kazan.",
            "code": "VATANKLUP250",
            "discount_label": "250 ₺ hediye",
            "category": "Tüm Kategoriler",
            "expires_label": "Ay sonu",
        },
    ],
    "amazon": [
        {
            "title": "Amazon Prime Üyelerine %15 İndirim",
            "description": "Elektronik kategorisinde Prime üyelerine sepete özel %15 indirim.",
            "code": "PRIME15",
            "discount_label": "%15 indirim",
            "category": "Elektronik",
            "expires_label": "Bu hafta",
        },
        {
            "title": "Kindle Cihazlarda 700 ₺ İndirim",
            "description": "Kindle Paperwhite ve Oasis modellerinde sepete özel indirim.",
            "code": "KINDLE700",
            "discount_label": "700 ₺ indirim",
            "category": "Aksesuar",
            "expires_label": "3 gün kaldı",
        },
        {
            "title": "Aksesuarda 2 Al 1 Öde",
            "description": "Belirli şarj kablosu ve adaptör setlerinde 2 al 1 öde fırsatı.",
            "code": "BOGOAMZ",
            "discount_label": "2 al 1 öde",
            "category": "Aksesuar",
            "expires_label": "Stoklarla sınırlı",
        },
        {
            "title": "Echo Hoparlörlerde %25 İndirim",
            "description": "Echo Dot, Echo Show ailesinde sepete özel %25 indirim.",
            "code": "ECHO25",
            "discount_label": "%25 indirim",
            "category": "Akıllı Ev",
            "expires_label": "5 gün kaldı",
        },
        {
            "title": "Bilgisayar Aksesuarında 300 ₺",
            "description": "Logitech ve Razer marka klavye / mouse modellerinde 300 ₺ indirim.",
            "code": "PC300",
            "discount_label": "300 ₺ indirim",
            "category": "Bilgisayar",
            "expires_label": "Hafta sonu",
        },
        {
            "title": "Tüm Siparişlerde Kargo Bedava",
            "description": "Prime üyelerine 200 ₺ üzeri alışverişlerde kargo ücretsiz.",
            "code": None,
            "discount_label": "Kargo bedava",
            "category": "Tüm Kategoriler",
            "expires_label": "Süresiz",
        },
    ],
    "mediamarkt": [
        {
            "title": "Televizyonlarda 3.000 ₺ İndirim",
            "description": "55\" ve üzeri OLED / QLED TV modellerinde sepete özel indirim.",
            "code": "TV3000",
            "discount_label": "3.000 ₺ indirim",
            "category": "Televizyon",
            "expires_label": "Bu hafta",
        },
        {
            "title": "MediaMarkt Card'a Özel %12 İndirim",
            "description": "MediaMarkt Card sahiplerine elektronikte sepette %12 indirim.",
            "code": "MMCARD12",
            "discount_label": "%12 indirim",
            "category": "Elektronik",
            "expires_label": "Ay sonu",
        },
        {
            "title": "Küçük Ev Aletlerinde 500 ₺",
            "description": "Süpürge, ütü, kahve makinelerinde sepete özel 500 ₺ indirim.",
            "code": "EVALET500",
            "discount_label": "500 ₺ indirim",
            "category": "Küçük Ev Aletleri",
            "expires_label": "5 gün kaldı",
        },
        {
            "title": "Konsolda 12 Taksit + 750 ₺",
            "description": "PlayStation 5 ve Xbox Series X'te 12 taksit ve 750 ₺ sepet indirimi.",
            "code": "KONSOL750",
            "discount_label": "750 ₺ indirim",
            "category": "Oyun",
            "expires_label": "3 gün kaldı",
        },
        {
            "title": "Telefonlarda 1.000 ₺ İndirim",
            "description": "iPhone ve Galaxy üst segment telefonlarda 1.000 ₺ sepet indirimi.",
            "code": "PHONE1000",
            "discount_label": "1.000 ₺ indirim",
            "category": "Telefon",
            "expires_label": "Hafta sonu",
        },
        {
            "title": "MediaMarkt Plus 30 Gün Ücretsiz",
            "description": "Plus üyelik denemen aktifken hızlı teslimat ve özel fırsatlar açık.",
            "code": "MMPLUS30",
            "discount_label": "30 gün ücretsiz",
            "category": "Üyelik",
            "expires_label": "Süresiz",
        },
    ],
    "n11": [
        {
            "title": "Telefonda 1.000 ₺ Sepet İndirimi",
            "description": "Seçili akıllı telefonlarda 20.000 ₺ üzeri alışverişe 1.000 ₺ indirim.",
            "code": "N11PHONE1000",
            "discount_label": "1.000 ₺ indirim",
            "category": "Telefon",
            "expires_label": "Bu hafta",
        },
        {
            "title": "N11 Pro Üyelere %10 Ekstra İndirim",
            "description": "Pro üyeliğin aktifken elektronik kategorisinde sepete %10 ekstra indirim.",
            "code": "PRO10",
            "discount_label": "%10 indirim",
            "category": "Elektronik",
            "expires_label": "Ay sonu",
        },
        {
            "title": "Bilgisayar Aksesuarında 350 ₺",
            "description": "Klavye, mouse, mouse pad setlerinde 350 ₺ sepet indirimi.",
            "code": "PCEXTRA350",
            "discount_label": "350 ₺ indirim",
            "category": "Bilgisayar",
            "expires_label": "5 gün kaldı",
        },
        {
            "title": "Akıllı Ev Ürünlerinde %15",
            "description": "Akıllı ampul, priz ve robot süpürgelerde sepette %15 indirim.",
            "code": "AKILLI15",
            "discount_label": "%15 indirim",
            "category": "Akıllı Ev",
            "expires_label": "Hafta sonu",
        },
        {
            "title": "Kulaklıkta 400 ₺ İndirim",
            "description": "JBL, Sony ve Anker markalarında 400 ₺ sepet indirimi.",
            "code": "KULAK400",
            "discount_label": "400 ₺ indirim",
            "category": "Aksesuar",
            "expires_label": "3 gün kaldı",
        },
        {
            "title": "İlk Kargo Bedava",
            "description": "Hesabından yapacağın ilk siparişte kargo n11 tarafından karşılanır.",
            "code": None,
            "discount_label": "Kargo bedava",
            "category": "Tüm Kategoriler",
            "expires_label": "Hesabına özel",
        },
    ],
}


def _build_sample_coupons(accounts: List[ConnectedAccount]) -> List[CouponItem]:
    """Materialise the curated sample coupons for each connected account."""
    out: List[CouponItem] = []
    for acc in accounts:
        samples = _SAMPLE_COUPONS.get(acc.id, [])
        for idx, sample in enumerate(samples):
            out.append(
                CouponItem(
                    id=f"{acc.id}-sample-{idx}",
                    store_id=acc.id,
                    store_name=acc.name,
                    title=sample["title"],
                    description=sample["description"],
                    code=sample.get("code"),
                    discount_label=sample.get("discount_label"),
                    category=sample.get("category"),
                    expires_label=sample.get("expires_label"),
                    url=sample.get("url"),
                    is_sample=True,
                )
            )
    return out


# ── Prompting (news only) ─────────────────────────────────────────────────
_NEWS_SYSTEM = """
You are the Techno Track Tech-News Agent for the Turkish technology market.
The Google Search tool is ALWAYS available to you — you MUST call it at the
start of every request before writing any answer. Your job is to surface
real, currently-circulating tech-price and tech-product news from live web
sources, not generic suggestions.

OUTPUT FORMAT (strict):
- Return ONLY a single valid JSON object. No markdown fences, no commentary,
  no trailing text.
- All user-facing text fields ("title", "summary", "date_label", "source")
  MUST be in Turkish, written for a Turkish shopper.
- Every news item MUST include a working ``url`` that points to the original
  source you cited via Google Search. Skip items where you cannot supply a
  real URL.
""".strip()


def _build_news_prompt() -> str:
    schema_hint = """
{
  "news": [
    {
      "id": "stable-slug",
      "title": "Haber başlığı",
      "summary": "2-3 cümlede neden önemli ve hangi fiyat/ürünü etkiliyor",
      "category": "price-drop | new-product | launch | deal | industry",
      "date_label": "Bugün | Dün | Bu hafta | 2 gün önce",
      "source": "shiftdelete | webtekno | donanimhaber | hepsiburada | trendyol | ...",
      "url": "Haberin orijinal kaynağı"
    }
  ]
}
""".strip()

    return f"""
Son 1 hafta içinde Türkiye'de ve dünyada teknoloji fiyatlarını veya yeni
ürünleri ilgilendiren 8-12 haber topla. Şu konulara odaklan:

  - Belirli bir model için fiyat düşüşü, fiyat artışı veya kampanya
  - Yakında piyasaya çıkacak yeni telefon, laptop, konsol, kulaklık vb.
  - Apple, Samsung, Sony, Xiaomi, AMD, NVIDIA gibi büyük markaların duyurusu
  - Türkiye'de başlayan büyük indirim dönemleri (Black Friday, Efsane Cuma,
    Yaz İndirimi vb.) ve büyük e-ticaret kampanyaları

ZORUNLU ARAMA ADIMI — yanıtı yazmadan önce Google Search'ü mutlaka çağır.
En az şu sorguları çalıştır (gerekirse daha fazlasını da dene):
  1. "iPhone fiyat düştü" 2026
  2. "Samsung Galaxy yeni model 2026"
  3. "MacBook indirim Hepsiburada"
  4. "PlayStation 5 fiyat" Türkiye
  5. "Trendyol kampanya 2026"
  6. "Hepsiburada efsane cuma"
  7. site:shiftdelete.net teknoloji haber
  8. site:webtekno.com yeni telefon

Her haber için kaynak URL'sini ``url`` alanına yaz; uydurma URL koyma. Bir
kaynak bulamadığın bir haberi listeden çıkar. ``category`` alanına şu
değerlerden birini ver: price-drop | new-product | launch | deal | industry.

ÇIKTI ŞEMASI (sadece bu JSON'u döndür, başka hiçbir şey yazma):
{schema_hint}
""".strip()


# ── Sanitization ──────────────────────────────────────────────────────────
_NEWS_CATEGORIES = {"price-drop", "new-product", "launch", "deal", "industry"}


def _str_or_none(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_news(raw) -> List[NewsItem]:
    if not isinstance(raw, list):
        return []
    out: List[NewsItem] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        title = _str_or_none(item.get("title"))
        summary = _str_or_none(item.get("summary"))
        if not title or not summary:
            continue
        category = _str_or_none(item.get("category")) or "industry"
        if category not in _NEWS_CATEGORIES:
            category = "industry"
        news_id = _str_or_none(item.get("id")) or f"news-{idx}"
        out.append(
            NewsItem(
                id=news_id,
                title=title,
                summary=summary,
                category=category,
                date_label=_str_or_none(item.get("date_label")),
                source=_str_or_none(item.get("source")),
                url=_str_or_none(item.get("url")),
            )
        )
    return out


# ── Live RSS source (used when Google Search grounding is unavailable) ───
_RSS_FEEDS = {
    "webtekno": "https://www.webtekno.com/rss.xml",
    "shiftdelete": "https://shiftdelete.net/feed",
    "donanimhaber": "https://www.donanimhaber.com/rss/tum/",
    "chip": "https://www.chip.com.tr/rss",
    "technopat": "https://www.technopat.net/feed/",
}
_RSS_MAX_AGE = timedelta(days=7)
_RSS_PER_FEED = 25
_RSS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _rss_field(item_xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", item_xml, flags=re.S)
    if not match:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", match.group(1), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


async def _fetch_feed(client: httpx.AsyncClient, source: str, url: str) -> list[dict]:
    resp = await client.get(url)
    resp.raise_for_status()
    now = datetime.now(timezone.utc)
    out: list[dict] = []
    for item_xml in re.findall(r"<item>(.*?)</item>", resp.text, flags=re.S)[:_RSS_PER_FEED]:
        title = _rss_field(item_xml, "title")
        link = _rss_field(item_xml, "link")
        try:
            published = parsedate_to_datetime(_rss_field(item_xml, "pubDate"))
        except (TypeError, ValueError):
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if not title or not link.startswith("http") or now - published > _RSS_MAX_AGE:
            continue
        out.append({
            "source": source,
            "title": title,
            "url": link,
            "published": published,
            "snippet": _rss_field(item_xml, "description")[:280],
        })
    return out


async def _fetch_rss_articles() -> list[dict]:
    """Recent articles from every feed, newest first; a failing feed is skipped."""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0), follow_redirects=True, headers={"User-Agent": _RSS_USER_AGENT},
    ) as client:
        results = await asyncio.gather(
            *(_fetch_feed(client, name, url) for name, url in _RSS_FEEDS.items()),
            return_exceptions=True,
        )
    articles: list[dict] = []
    for name, res in zip(_RSS_FEEDS, results):
        if isinstance(res, Exception):
            logger.warning("RSS feed %s failed: %s", name, res)
            continue
        articles.extend(res)
    articles.sort(key=lambda a: a["published"], reverse=True)
    return articles


def _date_label(published: datetime) -> str:
    days = (datetime.now(timezone.utc).date() - published.astimezone(timezone.utc).date()).days
    if days <= 0:
        return "Bugün"
    if days == 1:
        return "Dün"
    return f"{days} gün önce"


_NEWS_OFFLINE_SYSTEM = """
You are the Techno Track Tech-News Agent for the Turkish technology market.
You receive a numbered list of REAL articles published this week by Turkish
tech sites. Pick the ones a Turkish shopper of phones, laptops, tablets,
consoles, headphones and other consumer electronics cares about: price
changes, discounts and campaigns, new product launches and announcements.
Skip unrelated stories (cars, games' story news, politics, science).

OUTPUT FORMAT (strict):
- Return ONLY a single valid JSON object. No markdown fences, no commentary.
- Reference articles ONLY by their numeric ``article_id``. Never invent an
  article, a URL, a price or a date.
- ``title`` and ``summary`` MUST be in Turkish. The summary is 1-2 sentences
  based only on the title and snippet you were given.
""".strip()


def _build_news_offline_prompt(articles: list[dict]) -> str:
    listing = [
        {"article_id": idx, "source": a["source"], "title": a["title"], "snippet": a["snippet"]}
        for idx, a in enumerate(articles)
    ]
    schema_hint = """
{
  "news": [
    {
      "article_id": 0,
      "title": "Kısa Türkçe başlık",
      "summary": "1-2 cümlede neden önemli",
      "category": "price-drop | new-product | launch | deal | industry"
    }
  ]
}
""".strip()
    return f"""
Bu haftanın gerçek teknoloji haberleri (en yeniden eskiye):

{json.dumps(listing, ensure_ascii=False, indent=1)}

Bunlardan alışveriş yapan biri için en ilgili 8-12 haberi seç ve şu şemayla
döndür (yalnızca bu JSON):
{schema_hint}
""".strip()


def _parse_offline_news(raw, articles: list[dict]) -> List[NewsItem]:
    """Map the model's picks back onto real articles (url/source/date from RSS)."""
    if not isinstance(raw, list):
        return []
    out: List[NewsItem] = []
    used: set[int] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("article_id"))
        except (TypeError, ValueError):
            continue
        if idx in used or not 0 <= idx < len(articles):
            continue
        used.add(idx)
        article = articles[idx]
        category = _str_or_none(item.get("category")) or "industry"
        out.append(NewsItem(
            id=f"{article['source']}-{idx}",
            title=_str_or_none(item.get("title")) or article["title"],
            summary=_str_or_none(item.get("summary")) or article["snippet"] or article["title"],
            category=category if category in _NEWS_CATEGORIES else "industry",
            date_label=_date_label(article["published"]),
            source=article["source"],
            url=article["url"],
        ))
    return out


# ── Endpoint ──────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=CampaignsResponse,
    summary="Personalised coupons + live tech-news feed",
    status_code=status.HTTP_200_OK,
)
async def get_campaigns(body: CampaignsRequest) -> CampaignsResponse:
    logger.info(
        "POST /campaigns connected=%d", len(body.connected_accounts)
    )

    # 1. Coupons → always serve curated samples for each connected store.
    coupons = _build_sample_coupons(body.connected_accounts)

    # 2. News → Google-grounded research when the key allows it, otherwise
    #    real RSS articles selected and summarised by the same model ladder.
    articles = await _fetch_rss_articles()
    try:
        result = await call_gemini(
            settings.NEWS_MODEL,
            settings.NEWS_FALLBACK_MODEL,
            system=_NEWS_SYSTEM,
            user_prompt=_build_news_prompt(),
            offline_system=_NEWS_OFFLINE_SYSTEM,
            offline_prompt=_build_news_offline_prompt(articles),
            use_search=True,
            response_json=True,
            # Room for ~10 news items plus the 3.x thinking pass so the JSON
            # doesn't get truncated mid-array.
            max_output_tokens=8192,
            temperature=0.4,
            thinking_level="low",
            timeout_seconds=120.0,
        )
    except GeminiAuthError as auth_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(auth_err),
        ) from auth_err
    except Exception as err:
        # If the entire news cascade fails, still return the coupons so the
        # Coupons tab works — flag the failure on the response.
        logger.error("Campaigns news cascade failed: %s", err, exc_info=True)
        return CampaignsResponse(
            coupons=coupons,
            news=[],
            sources=[],
            model_used="",
            grounded=False,
        )

    payload = result.parsed or {}
    if result.search_used:
        news = _parse_news(payload.get("news"))
        sources = result.sources
    else:
        news = _parse_offline_news(payload.get("news"), articles)
        sources = [{"title": item.title, "uri": item.url} for item in news if item.url]

    return CampaignsResponse(
        coupons=coupons,
        news=news,
        sources=[CampaignsSource(**s) for s in sources],
        model_used=result.model_used,
        grounded=bool(result.search_used and result.sources),
    )
