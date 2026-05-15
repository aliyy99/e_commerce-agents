"""
Minimal model-wiring test for CompareAgent.

Two modes:
  python test_compare_models.py dry   # no API call; mocks Gemini, checks model names
  python test_compare_models.py live  # ONE real API call; verifies end-to-end

The 'dry' run is free and proves the new env vars are wired correctly.
The 'live' run uses a single product URL whose data is served by the existing
mock_data_fallback in compare_agent, so HTTP scraping is offline and exactly
one Gemini call is made on success (or two if primary fails and fallback kicks in).
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import patch, MagicMock

import backend.main  # noqa: F401  load full app so route/agent import cycle is resolved
from backend.config import settings  # noqa: E402
from backend.models.requests import CompareRequest, CompareSiteData  # noqa: E402
from backend.agents import compare_agent  # noqa: E402


SAMPLE_URL = "https://www.hepsiburada.com/p-HBCV00007MIDSU"  # hits mock fallback


def _build_request() -> CompareRequest:
    return CompareRequest(
        products=[CompareSiteData(url=SAMPLE_URL, site="Hepsiburada")],
        locale="tr",
    )


async def _dry_run() -> None:
    """Mock genai.GenerativeModel so no API call is made; assert model name."""
    captured_models: list[str] = []

    class FakeResponse:
        text = "# Dummy Report\n\nMocked."

    def fake_model_ctor(model_name: str, system_instruction: str | None = None):
        captured_models.append(model_name)
        fake = MagicMock()
        fake.generate_content.return_value = FakeResponse()
        return fake

    with patch.object(compare_agent.genai, "GenerativeModel", side_effect=fake_model_ctor):
        with patch.object(compare_agent, "configure_gemini_client", return_value="dummy-key"):
            result = await compare_agent.run_compare_agent(_build_request())

    print("Config:")
    print(f"  COMPARE_MODEL          = {settings.COMPARE_MODEL}")
    print(f"  COMPARE_FALLBACK_MODEL = {settings.COMPARE_FALLBACK_MODEL}")
    print(f"Models invoked (in order): {captured_models}")
    assert captured_models, "Gemini model was never constructed."
    assert captured_models[0] == settings.COMPARE_MODEL, (
        f"Expected primary model {settings.COMPARE_MODEL!r}, "
        f"got {captured_models[0]!r}"
    )
    assert len(captured_models) == 1, (
        f"Primary succeeded yet fallback was also called ({captured_models}). "
        "That would burn quota in production."
    )
    assert result.get("markdown_report"), "markdown_report was empty"
    print("\nDRY RUN OK — primary model is wired and fallback stays cold on success.")


async def _live_run() -> None:
    """One real API call against COMPARE_MODEL. Falls back to fallback model on error."""
    print(f"Calling Gemini live with primary = {settings.COMPARE_MODEL}")
    print(f"             fallback (only on error) = {settings.COMPARE_FALLBACK_MODEL}")
    result = await compare_agent.run_compare_agent(_build_request())
    report = result.get("markdown_report") or ""
    print("\n--- REPORT (first 500 chars) ---")
    print(report[:500])
    print(f"\nReport length: {len(report)} chars")
    print(f"Lowest price: {result.get('lowest_price')} ({result.get('lowest_price_site')})")
    print("\nLIVE RUN OK.")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    if mode == "dry":
        asyncio.run(_dry_run())
    elif mode == "live":
        asyncio.run(_live_run())
    else:
        sys.exit(f"Unknown mode: {mode!r}. Use 'dry' or 'live'.")


if __name__ == "__main__":
    main()
