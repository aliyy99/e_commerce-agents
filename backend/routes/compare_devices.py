"""
Techno Track AI - Device Comparison Route
POST /api/v1/compare-devices

Takes two device specs and uses Gemini Flash to produce an exhaustive,
spec-by-spec head-to-head comparison: a winner table grouped by category
(performance, display, camera, battery, software, design, value, etc.) plus
a long-form summary article and per-device "best for" guidance.

The returned JSON is consumed by the frontend Device Compare page and is
also fed into the chat widget so the assistant can answer follow-up
questions like "which one is better for gaming?" with full context.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..config import settings
from ..models.responses import GroundingSource
from ..services.gemini_client import GeminiAuthError
from ..services.gemini_grounded import call_gemini

logger = logging.getLogger("technotrack.routes.compare_devices")
router = APIRouter(prefix="/compare-devices", tags=["Device Comparison"])


# ── Request / Response models ─────────────────────────────────────────────
class DeviceSpec(BaseModel):
    label: str
    value: str


class DevicePayload(BaseModel):
    id: Optional[str | int] = None
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    specs: List[DeviceSpec] = Field(default_factory=list)
    price: Optional[float] = None


class CompareDevicesRequest(BaseModel):
    device_a: DevicePayload
    device_b: DevicePayload
    locale: str = Field(default="tr")


class ComparisonRow(BaseModel):
    feature: str
    value_a: str
    value_b: str
    winner: str = Field(..., description="'A' | 'B' | 'tie'")
    explanation: str


class ComparisonGroup(BaseModel):
    title: str
    icon: Optional[str] = None
    rows: List[ComparisonRow] = Field(default_factory=list)


class CompareDevicesResponse(BaseModel):
    overall_winner: str = Field(..., description="'A' | 'B' | 'tie'")
    overall_verdict: str
    score_a: int = Field(..., ge=0, le=100)
    score_b: int = Field(..., ge=0, le=100)
    groups: List[ComparisonGroup]
    pros_a: List[str] = Field(default_factory=list)
    cons_a: List[str] = Field(default_factory=list)
    pros_b: List[str] = Field(default_factory=list)
    cons_b: List[str] = Field(default_factory=list)
    best_for_a: str
    best_for_b: str
    summary: str
    model_used: str
    grounding_sources: List[GroundingSource] = Field(default_factory=list)
    grounded: bool = False


# ── Prompt ────────────────────────────────────────────────────────────────
_COMPARE_SYSTEM = """
You are a senior consumer-tech analyst with deep, hands-on knowledge of
smartphones, laptops, tablets, wearables, headphones, gaming consoles and
TVs. Your job is to deliver an exhaustive, fair, and decisive head-to-head
technical comparison of two devices.

Hard rules:
- Use ONLY the supplied specs as the source of truth for numeric facts.
- Where specs are missing or unclear, fall back to widely-known public
  knowledge about the model — never invent figures.
- For every comparison row pick a single winner: "A", "B" or "tie". Do not
  hedge. A "tie" is reserved for genuinely equivalent capability, not
  laziness.
- Each row's ``explanation`` must be a single sentence that names the
  concrete reason (numbers, generation, technology) the winner is ahead.
- Cover EVERY meaningful angle for the device class. For phones that means
  display, processor / chipset, RAM, storage, main camera system, front
  camera, battery + charging, software / OS, connectivity, build / durability,
  audio, biometrics, software update window, and value-for-money.
- If the two devices belong to DIFFERENT categories (e.g. a phone vs a
  tablet, or a laptop vs a phone), focus the comparison on dimensions they
  meaningfully share (compute, display, battery life, software ecosystem,
  portability, value) and explicitly call out the form-factor difference
  in the overall verdict and summary. Still produce per-row winners on
  the shared dimensions.
- Output ONLY a single valid JSON object that matches the supplied schema —
  no markdown fences, no prose around it.

KNOWLEDGE SOURCE:
You do NOT have a live web-search tool on this call. Rely on (1) the supplied
specs as the source of truth for numeric facts, and (2) your own up-to-date
product knowledge of these specific models to:
  - fill gaps where a spec is missing or unclear
  - cite the real-world performance differences expert reviewers report
  - mention a newer model on the horizon if it materially affects "wait vs
    buy" timing
Never invent figures — if a fact isn't in the supplied specs AND you are not
confident of it from your own knowledge of the model, omit it rather than
guess.

Write all human-readable text in the requested locale.
""".strip()


def _build_prompt(req: CompareDevicesRequest) -> str:
    schema = {
        "overall_winner": "A | B | tie",
        "overall_verdict": "one-line decisive verdict",
        "score_a": "integer 0-100 (overall capability score)",
        "score_b": "integer 0-100",
        "groups": [
            {
                "title": "Performance",
                "icon": "Cpu",
                "rows": [
                    {
                        "feature": "Processor",
                        "value_a": "spec A value",
                        "value_b": "spec B value",
                        "winner": "A | B | tie",
                        "explanation": "one concrete sentence",
                    }
                ],
            }
        ],
        "pros_a": ["3-6 short bullet strengths of Device A"],
        "cons_a": ["3-6 short bullet weaknesses of Device A"],
        "pros_b": ["3-6 short bullet strengths of Device B"],
        "cons_b": ["3-6 short bullet weaknesses of Device B"],
        "best_for_a": "2-3 sentence portrait of the user A is built for",
        "best_for_b": "2-3 sentence portrait of the user B is built for",
        "summary": (
            "DETAILED 4-6 paragraph article comparing the two devices. "
            "Cover positioning, day-to-day performance, media + creator "
            "workloads, gaming, battery + thermals, software longevity, "
            "and end with a concrete buying recommendation that names "
            "scenarios where each device wins."
        ),
    }

    valid_icons = [
        "Cpu", "Monitor", "Camera", "Battery", "Smartphone", "Wifi",
        "Shield", "Speaker", "Fingerprint", "RefreshCw", "Sparkles",
        "DollarSign", "Layers",
    ]

    payload = {
        "device_a": req.device_a.model_dump(),
        "device_b": req.device_b.model_dump(),
        "locale": req.locale,
    }

    return f"""
Compare these two devices head-to-head. Be DECISIVE and CONCISE — the JSON
gets cropped if you ramble. Keep:
  - 6 to 8 ``groups`` total (cover the meaningful angles, not all of them)
  - 3 to 5 ``rows`` per group
  - ``explanation`` ≤ 90 characters, ONE sentence
  - ``summary``: 3 SHORT paragraphs (~70 words each), not 6
  - ``best_for_a`` / ``best_for_b`` ≤ 220 chars
  - ``pros`` / ``cons`` lists capped at 4 items each, short phrases only

Use these lucide-react icon names for ``group.icon`` where they fit:
{', '.join(valid_icons)}.

Required output schema (return EXACTLY one JSON object, no markdown fences,
no surrounding prose):
{json.dumps(schema, ensure_ascii=False, indent=2)}

Devices to compare:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Locale for human-readable strings: {req.locale}
""".strip()


def _coerce_winner(raw: object) -> str:
    if not isinstance(raw, str):
        return "tie"
    v = raw.strip().lower()
    if v in {"a", "device a", "1"}:
        return "A"
    if v in {"b", "device b", "2"}:
        return "B"
    return "tie"


def _coerce_score(raw: object, fallback: int = 50) -> int:
    try:
        n = int(round(float(raw)))
    except (TypeError, ValueError):
        return fallback
    return max(0, min(100, n))


def _normalize_payload(parsed: dict) -> dict:
    groups_raw = parsed.get("groups") or []
    groups: list[dict] = []
    for g in groups_raw:
        if not isinstance(g, dict):
            continue
        rows_raw = g.get("rows") or []
        rows = []
        for r in rows_raw:
            if not isinstance(r, dict):
                continue
            rows.append({
                "feature": str(r.get("feature") or "").strip() or "Feature",
                "value_a": str(r.get("value_a") or "—").strip(),
                "value_b": str(r.get("value_b") or "—").strip(),
                "winner": _coerce_winner(r.get("winner")),
                "explanation": str(r.get("explanation") or "").strip(),
            })
        if not rows:
            continue
        groups.append({
            "title": str(g.get("title") or "Section").strip(),
            "icon": (str(g.get("icon")).strip() if g.get("icon") else None),
            "rows": rows,
        })

    def _strs(value) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(x).strip() for x in value if isinstance(x, (str, int, float)) and str(x).strip()]

    return {
        "overall_winner": _coerce_winner(parsed.get("overall_winner")),
        "overall_verdict": str(parsed.get("overall_verdict") or "").strip()
            or "Both devices are competitive in their own categories.",
        "score_a": _coerce_score(parsed.get("score_a")),
        "score_b": _coerce_score(parsed.get("score_b")),
        "groups": groups,
        "pros_a": _strs(parsed.get("pros_a")),
        "cons_a": _strs(parsed.get("cons_a")),
        "pros_b": _strs(parsed.get("pros_b")),
        "cons_b": _strs(parsed.get("cons_b")),
        "best_for_a": str(parsed.get("best_for_a") or "").strip(),
        "best_for_b": str(parsed.get("best_for_b") or "").strip(),
        "summary": str(parsed.get("summary") or "").strip(),
    }


# ── Endpoint ──────────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=CompareDevicesResponse,
    summary="Deep head-to-head technical comparison of two devices",
    status_code=status.HTTP_200_OK,
)
async def compare_devices(body: CompareDevicesRequest) -> CompareDevicesResponse:
    if body.device_a.name.strip().lower() == body.device_b.name.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please pick two different devices to compare.",
        )
    # Cross-category comparisons are allowed: the prompt asks the model to
    # focus on shared dimensions when categories differ, and the small demo
    # catalog often only has one device per non-phone category.

    logger.info(
        "POST /compare-devices a=%r b=%r",
        body.device_a.name, body.device_b.name,
    )

    prompt = _build_prompt(body)

    # UNGROUNDED call → Gemini 3.5 Flash primary, 2.5 Flash fallback on an
    # independent quota counter. We deliberately skip google_search here: it
    # has zero free-tier quota on every Gemini 3.x model (instant 429), and a
    # spec-vs-spec device verdict leans on the model's own product knowledge,
    # not a live web fetch — the frontend never renders grounding sources for
    # this page. thinking_level="low" keeps the 3.x reasoning model fast on
    # what is really a structured-JSON extraction (3.x-only; the 2.5 fallback
    # transparently ignores it).
    primary = getattr(settings, "COMPARE_DEVICES_MODEL", None) or "gemini-3.5-flash"
    fallback = getattr(settings, "COMPARE_DEVICES_FALLBACK_MODEL", None) or "gemini-2.5-flash"

    try:
        grounded = await call_gemini(
            primary_model=primary,
            fallback_model=fallback,
            system=_COMPARE_SYSTEM,
            user_prompt=prompt,
            use_search=False,
            response_json=True,
            # 8-10 groups × ~5 rows × evidence + a multi-paragraph summary can
            # exceed 8k tokens; 16k leaves headroom for cross-category mixes
            # plus the 3.x thinking pass.
            max_output_tokens=16384,
            temperature=0.3,
            top_p=0.95,
            timeout_seconds=150.0,
            thinking_level="low",
        )
    except GeminiAuthError as auth_err:
        logger.error("Compare-devices auth error: %s", auth_err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(auth_err),
        ) from auth_err
    except Exception as exc:
        logger.error("Compare-devices model call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate comparison: {exc}",
        ) from exc

    if grounded.parsed is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Comparison model did not return parseable JSON.",
        )

    normalized = _normalize_payload(grounded.parsed)
    if not normalized["groups"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Comparison model returned no usable rows.",
        )

    if grounded.sources:
        logger.info(
            "Compare-devices -> grounded with %d sources (model=%s)",
            len(grounded.sources), grounded.model_used,
        )

    return CompareDevicesResponse(
        **normalized,
        model_used=grounded.model_used or "unknown",
        grounding_sources=[GroundingSource(**s) for s in grounded.sources],
        grounded=bool(grounded.sources),
    )
