"""Smoke test for Gemini 3 Flash on a product image (no network image fetch).

Builds a tiny solid-color 'product' JPEG in-memory so we test the model call
itself without depending on a remote image host.
"""
import asyncio
import base64
import io
import importlib.util
import sys
import types
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Pre-load required modules so vision_agent's relative imports resolve.
import backend  # noqa: F401, E402
import backend.config  # noqa: F401, E402
import backend.models  # noqa: F401, E402
import backend.models.requests  # noqa: F401, E402
import backend.models.responses  # noqa: F401, E402
import backend.services  # noqa: F401, E402
import backend.services.gemini_client  # noqa: F401, E402

# Stub the agents package so backend.agents.__init__ isn't executed.
agents_pkg = types.ModuleType("backend.agents")
agents_pkg.__path__ = [str(ROOT / "backend" / "agents")]
sys.modules["backend.agents"] = agents_pkg

spec = importlib.util.spec_from_file_location(
    "backend.agents.vision_agent",
    str(ROOT / "backend" / "agents" / "vision_agent.py"),
)
vision_mod = importlib.util.module_from_spec(spec)
sys.modules["backend.agents.vision_agent"] = vision_mod
spec.loader.exec_module(vision_mod)

run_vision_agent = vision_mod.run_vision_agent
from backend.config import settings  # noqa: E402
from backend.models.requests import VisionRequest, ImageInputType  # noqa: E402


def _build_test_image_b64() -> str:
    """Render a simple white box with the text 'iPhone 15 Pro Max' on it."""
    img = Image.new("RGB", (512, 512), color=(245, 245, 247))
    draw = ImageDraw.Draw(img)
    # Draw a fake phone silhouette
    draw.rounded_rectangle((140, 60, 372, 452), radius=40, fill=(20, 20, 22))
    draw.rounded_rectangle((155, 95, 357, 420), radius=18, fill=(60, 60, 70))
    draw.text((180, 220), "iPhone 15\nPro Max", fill=(230, 230, 230))
    draw.text((150, 470), "Test product image", fill=(40, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


async def main() -> None:
    print(f"VISION_MODEL          = {settings.VISION_MODEL}")
    print(f"VISION_FALLBACK_MODEL = {settings.VISION_FALLBACK_MODEL}")
    print()

    image_b64 = _build_test_image_b64()
    req = VisionRequest(
        input_type=ImageInputType.BASE64,
        image_data=image_b64,
        locale="en",
    )
    import traceback
    import logging
    logging.basicConfig(level=logging.DEBUG)
    try:
        result = await run_vision_agent(req)
    except Exception as err:
        print(f"FAILED: {err!r}")
        traceback.print_exc()
        return

    print(f"status         : {result.status}")
    print(f"model_used     : {result.model_used}")
    print(f"product_name   : {result.product_name}")
    print(f"brand          : {result.brand}")
    print(f"category       : {result.category}")
    print(f"search_keywords: {result.search_keywords}")
    print(f"confidence     : {result.confidence}")
    print(f"specs          : {[(s.key, s.value) for s in (result.specs or [])]}")
    if result.error_detail:
        print(f"error_detail   : {result.error_detail}")


if __name__ == "__main__":
    asyncio.run(main())
