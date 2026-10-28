# Techno Track 🚀

Techno Track is an AI-powered product analysis and price-tracking platform for consumer electronics, built on a multi-agent FastAPI backend and a React frontend.

It helps users make smarter shopping decisions by identifying products from photos, scraping and analyzing store listings, comparing devices spec-by-spec, estimating price history, and answering follow-up questions through a context-aware chat assistant. All AI features run on Google's **Gemini** models (plus **Imagen 3** for image generation).

> **Note:** This is a demo project. The product catalog contains **6 sample products** (`src/data/products.js`), not every product is included, user data in the UI (favorites, tracked products, orders) is not persisted, and some agents are simulated. See [Current Limitations](#current-limitations) before relying on any output.

---

## ✨ Key Features

- 🔍 **Visual Product Recognition:** Upload a photo or use the camera; the Vision Agent identifies the brand, model, color and visible specs, then the result is matched against the catalog. If no confident match is found, you can pick from suggested models of the detected brand.
- 📊 **In-Depth Product Analysis:** Scrapes the product's pages on Turkish marketplaces (Vatan, Trendyol, Hepsiburada, MediaMarkt) for price, rating, reviews and specs, then Gemini (grounded with Google Search) produces a BUY / WAIT / AVOID verdict, a review trust report, chronic issues, blind spots, honest pros/cons and the lowest price. Results are cached for 7 days.
- ⚖️ **Device Compare:** Compares **two** catalog devices head-to-head: grouped spec tables with per-row winners, scores, pros/cons, "best for" guidance and a summary article.
- 📈 **Price Graphic:** Estimates the last 12 months of monthly prices in Turkey using Gemini with Google Search grounding and renders them as a chart, with the sources used.
- 🔔 **Tracked Products:** Track a product with a target price for a chosen duration (or until an end date). While the app is open, store prices are re-scraped periodically (no AI call); when a store hits the target you get a toast and a notification, and optionally a *simulated* auto-buy that adds an order to the Orders page.
- 🏷️ **Campaigns:** Live, Google-Search-grounded tech news for the Turkish market plus coupon cards for your linked store accounts (coupons are sample data).
- 💬 **Smart Chat Assistant:** A chat widget that receives the current product, price chart, device comparison or campaigns as context. Questions about *when to buy* (or prices without a chart) are answered with Google Search grounding.
- 🎨 **Modern UI:** Light theme with glassmorphism effects and Framer Motion animations.

---

## 🤖 Architecture

The frontend calls a dedicated backend endpoint for each feature. The backend is a FastAPI app; every route is mounted under `/api/v1`.

| UI feature | Endpoint | Backend module | Default model(s) |
|---|---|---|---|
| Visual search | `POST /vision/analyze-image` | `agents/vision_agent.py` | Cascade: `gemini-3-flash-preview` → `gemini-2.5-flash` → `gemini-3-flash-lite-preview` → `gemini-2.5-flash-lite` → `gemini-3-pro-preview` → `gemini-2.5-pro` (stops early once confidence ≥ 0.55) |
| Product analysis | `POST /analyze/compare` | `agents/compare_agent.py` | `ANALYST_MODEL` (`gemini-2.5-flash`, grounded) → `ANALYST_FALLBACK_MODEL` (`gemini-2.5-flash-lite`) → local fallback report |
| Device Compare | `POST /compare-devices` | `routes/compare_devices.py` | `COMPARE_DEVICES_MODEL` (`gemini-3.5-flash`, ungrounded) → `gemini-2.5-flash` |
| Price Graphic | `POST /price-history` | `routes/price_history.py` | `PRICE_HISTORY_MODEL` (`gemini-2.5-flash`, grounded) → `gemini-2.5-flash-lite` |
| Campaigns | `POST /campaigns` | `routes/campaigns.py` | News: grounded cascade starting at `gemini-3-flash-preview`; coupons: static sample data |
| Chat widget | `POST /chat` | `services/gemini_proxy.py` | `CHAT_MODEL` (`gemini-2.5-flash`) → `CHAT_FALLBACK_MODEL` → `FLASH_MODEL` → lite tiers → `PRO_MODEL` |
| Tracked products | `POST /tracking/check-prices` | `routes/tracking.py` | No AI call (reuses the Compare Agent's scraper) |

> Product analysis, Price Graphic and grounded chat default to the Gemini **2.5** family because the `google_search` tool has no free-tier quota on Gemini 3.x models. The Campaigns news cascade starts with 3.x models and falls through to 2.5 when they are rate-limited.

### Agents (`backend/agents/`)

1. **👀 Vision Agent** (`vision_agent.py`): Identifies the exact product in an image (brand, category, model, color, visible specs) with a calibrated confidence score, cascading through the models above. *Used by the UI.*
2. **⚖️ Compare Agent** (`compare_agent.py`): Scrapes several store pages **of the same product** in parallel (JSON-LD / meta tags, Brotli-aware), rejects price outliers, and asks Gemini for a grounded deep analysis: verdict, trust report (organic vs. suspicious reviews), chronic issues, blind spots, honest pros/cons and per-site summaries. If every site blocks scraping, Gemini looks up the prices via Google Search; if Gemini is unavailable, a local report is built from the scraped data. Successful results are cached in `backend/.cache/compare_analysis.json` (7-day TTL). *Used by the UI.*
3. **🧠 Analyst Agent** (`analyst_agent.py`): Turns a list of reviews plus a price history into a BUY / WAIT / AVOID / UNCERTAIN strategy with fake-review percentage, chronic issues, sentiment map and red flags (`PRO_MODEL`, ungrounded). *API-only:* available via `POST /analyze/reviews` and the Orchestrator.
4. **🕵️‍♂️ Detective Agent** (`detective_agent.py`): **Simulated.** Demonstrates agentic retry logic (shortens the search query and retries when nothing is found), but the search itself is a mock: it returns random prices from placeholder stores and a fixed set of sample reviews.
5. **🎨 Visualizer Agent** (`visualizer_agent.py`): Uses **Imagen 3** (`imagen-3.0-generate-002`) to generate an outfit photo for `fashion` products or a room-placement photo for `furniture` products, and uploads it to Supabase Storage (falls back to Base64). *API-only:* available via `POST /generate-style` and the Orchestrator; the electronics catalog does not use it.
6. **🎼 Orchestrator** (`orchestrator.py`): Runs the pipeline Vision → Detective → Analyst (→ Visualizer for fashion/furniture), streams agent logs over SSE (`GET /stream/pipeline/{session_id}`) and WebSocket (`/orchestrate/ws/{session_id}`), and saves the result to Supabase. *API-only:* available via `POST /orchestrate`; the current UI does not call it.

> Device comparison is implemented as a route (`routes/compare_devices.py`), not as a separate agent file.

---

## 📁 Project Structure

```
e_commerce-agents/
├── backend/                      # FastAPI backend (Python package — run from the repo root)
│   ├── main.py                   # App entry point: CORS, timing middleware, router registration, /health
│   ├── config.py                 # Loads backend/.env, model defaults (env-overridable)
│   ├── requirements.txt
│   ├── supabase_migration.sql    # Tables, storage bucket and RLS policies
│   ├── .env                      # Your secrets (git-ignored, create it yourself)
│   ├── .cache/                   # Compare Agent analysis cache (compare_analysis.json)
│   ├── agents/                   # vision, compare, analyst, detective, visualizer, orchestrator
│   ├── routes/                   # One router per endpoint group (see API Reference)
│   ├── services/
│   │   ├── gemini_client.py      # SDK setup, API-key hot reload, auth/quota error helpers
│   │   ├── gemini_grounded.py    # Shared async Gemini REST caller (Google Search grounding, JSON repair, fallbacks)
│   │   └── gemini_proxy.py       # Chat assistant logic
│   ├── db/supabase_client.py     # Supabase client + table/storage helpers
│   └── models/                   # Pydantic request/response models
├── src/                          # React frontend
│   ├── main.jsx, App.jsx         # App shell, routing between pages, vision flow, price tracker
│   ├── index.css
│   ├── components/               # Pages and widgets (Landing, ProductAnalysis, DeviceCompare, PriceGraphic,
│   │                             #   Campaigns, ChatWidget, Profile, Orders, TrackModal, ...)
│   ├── services/api.js           # All backend calls (fetch + SSE helper)
│   ├── data/
│   │   ├── products.js           # Sample catalog (6 products) + brand model lists
│   │   ├── ecommerceAccounts.js  # Demo linked store accounts (used by Profile and Campaigns)
│   │   └── generate_products.js  # Legacy generator — do NOT run (see Current Limitations)
│   ├── utils/                    # Search, filtering, vision-to-catalog matching, variants, images
│   └── lib/supabaseClient.js     # Unused (see Current Limitations)
├── index.html
├── vite.config.js                # Dev server; proxies /api → http://127.0.0.1:8000
├── tailwind.config.js, postcss.config.js
├── package.json
└── dist/                         # Production build output (npm run build)
```

---

## 🛠️ Technologies Used

**Frontend:**
- **React 18 & Vite 8** (with `@vitejs/plugin-react-oxc`)
- **Tailwind CSS 3** + `@tailwindcss/typography`
- **Framer Motion:** animations and page transitions
- **Lucide React:** icons
- **react-markdown:** renders AI-generated text
- **react-hot-toast:** notifications

**Backend:**
- **Python & FastAPI**, **Uvicorn** (ASGI server)
- **Pydantic v2:** request/response validation
- **Google Generative AI SDK** (`google-generativeai`): Vision, Chat and Imagen calls
- **Gemini REST API via `httpx`:** Google Search–grounded calls (the SDK version used does not support the `google_search` tool)
- **httpx + brotli:** marketplace scraping; **tenacity:** retries

**Database & Storage:**
- **Supabase:** used by the chat route (`recent_searches`), the favorites/alerts endpoints, the Orchestrator (`analysis_results`) and the Visualizer (`technotrack-images` bucket).

---

## 🚀 Installation and Setup

### 1. Prerequisites
- **Node.js 20.19+ or 22.12+** (required by Vite 8)
- **Python 3.10+**
- A [Google Gemini API key](https://aistudio.google.com/)
- A [Supabase](https://supabase.com/) project (the backend refuses to start without `SUPABASE_URL` and `SUPABASE_KEY`)

### 2. Supabase Setup

Open your project's **Supabase Dashboard → SQL Editor** and run the contents of `backend/supabase_migration.sql`. It creates the `analysis_results`, `favorites`, `price_alerts` and `recent_searches` tables and the public `technotrack-images` storage bucket.

> The included RLS policies allow full access (`USING (true)`) for easy local development. Tighten them before any production use.

### 3. Backend Setup

```bash
# From the project root
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Windows (CMD):        .venv\Scripts\activate.bat
# Mac/Linux:            source .venv/bin/activate

# Install required libraries
pip install -r requirements.txt
```

Create **`backend/.env`** (this exact location; it is loaded by `backend/config.py`):

```env
# Required
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key   # backend-only, never expose it to the frontend

# Optional
PORT=8000            # only used by `python -m backend.main`
APP_ENV=development  # "development" enables auto-reload with `python -m backend.main`
LOG_LEVEL=INFO
```

Start the backend **from the project root**, not from inside `backend/` (the backend is a Python package that uses relative imports, so `uvicorn main:app` inside `backend/` fails with `ImportError: attempted relative import with no known parent package`):

```bash
# Go back to the project root (keep the virtual environment active)
cd ..

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Alternative: uses PORT / APP_ENV from backend/.env and checks that the port is free
# python -m backend.main
```

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

> The Vite dev server proxies `/api` to `http://127.0.0.1:8000` (`vite.config.js`). If you run the backend on a different port, update the proxy target too.

### 4. Frontend Setup

Open a new terminal in the project root:

```bash
# Install dependencies
npm install

# Start the development server
npm run dev
```

Open `http://localhost:5173` (or the port printed by Vite) in your browser. 🎉

No frontend `.env` is required. Optionally set `VITE_API_URL` to call a backend at a different URL instead of the `/api/v1` dev proxy.

Other scripts: `npm run build` (outputs to `dist/`) and `npm run preview`.

> `npm run lint` is defined in `package.json`, but the repository has no ESLint configuration file yet, so it currently fails with "ESLint couldn't find a configuration file".

### Optional: Model Overrides

Every default model can be overridden in `backend/.env`:

| Variable | Default | Used by |
|---|---|---|
| `ANALYST_MODEL` / `ANALYST_FALLBACK_MODEL` | `gemini-2.5-flash` / `gemini-2.5-flash-lite` | Compare Agent (product analysis) |
| `COMPARE_MODEL` / `COMPARE_FALLBACK_MODEL` | `gemini-2.5-flash` / `gemini-2.5-flash-lite` | Compare Agent, only if the `ANALYST_*` values are empty |
| `COMPARE_DEVICES_MODEL` / `COMPARE_DEVICES_FALLBACK_MODEL` | `gemini-3.5-flash` / `gemini-2.5-flash` | Device Compare |
| `PRICE_HISTORY_MODEL` / `PRICE_HISTORY_FALLBACK_MODEL` | `gemini-2.5-flash` / `gemini-2.5-flash-lite` | Price Graphic |
| `CHAT_MODEL` / `CHAT_FALLBACK_MODEL` | `gemini-2.5-flash` / `gemini-2.5-flash-lite` | Chat |
| `FLASH_MODEL` | `gemini-3.5-flash` | Chat (extra fallback) |
| `PRO_MODEL` / `PRO_FALLBACK_MODEL` | `gemini-3.5-flash` / `gemini-2.5-flash` | Analyst Agent; `PRO_MODEL` is also Chat's last fallback |
| `IMAGE_MODEL` | `imagen-3.0-generate-002` | Visualizer Agent |

> `VISION_MODEL` / `VISION_FALLBACK_MODEL` exist in `config.py` but are **not read** by the Vision Agent, whose model cascade is defined in `agents/vision_agent.py`. The Campaigns news cascade is likewise defined in `routes/campaigns.py`.

---

## 📡 API Reference

All routes are prefixed with `/api/v1`.

| Method | Path | Description | Used by UI |
|---|---|---|---|
| POST | `/vision/analyze-image` | Identify a product from a Base64 image | ✅ |
| POST | `/analyze/compare` | Multi-store scrape + grounded deep analysis | ✅ |
| POST | `/compare-devices` | Two-device head-to-head comparison | ✅ |
| POST | `/price-history` | Estimated 12-month price history | ✅ |
| POST | `/campaigns` | Tech news + sample coupons for linked accounts | ✅ |
| POST | `/chat` | Context-aware chat assistant | ✅ |
| POST | `/tracking/check-prices` | Scrape current store prices (no AI) | ✅ |
| POST | `/tracking/` | Register a price-tracking target (stub, not persisted) | — |
| POST | `/analyze/reviews` | Analyst Agent on given reviews + price history | — |
| POST | `/generate-style` | Visualizer Agent (fashion / furniture only) | — |
| POST | `/orchestrate` | Full agent pipeline | — |
| GET | `/stream/pipeline/{session_id}` | SSE log stream for an orchestration run | — |
| WS | `/orchestrate/ws/{session_id}` | WebSocket log stream (legacy) | — |
| GET / POST | `/user/favorites` | List / add favorites (Supabase) | — |
| DELETE | `/user/favorites/{favorite_id}` | Remove a favorite | — |
| GET / POST | `/user/alerts` | List / create price alerts (Supabase) | — |
| DELETE | `/user/alerts/{alert_id}` | Deactivate a price alert | — |

`GET /health` (no prefix) returns the service status.

---

## Current Limitations

- **Sample data:** The catalog has 6 sample products. Their real store links mostly point to Vatan, with one each on Trendyol, Hepsiburada and MediaMarkt; store entries with a placeholder `#` link cannot be scraped or tracked.
- **Auto-buy is simulated:** It only creates an entry on the Orders page; no real purchase is made.
- **Simulated Detective Agent:** Its search is a mock (random prices, placeholder stores, fixed reviews), so `/orchestrate` results based on it are not real data.
- **API-only agents:** The Orchestrator, Analyst Agent, Detective Agent and Visualizer Agent are not used by the current UI. `src/components/AgentTerminal.jsx` (an SSE log viewer) exists but is not mounted.
- **No persistence in the UI:** Favorites, tracked products and notifications live in React state and reset on page refresh. Orders, the profile and the linked store accounts are demo data. The Supabase-backed `/user/favorites` and `/user/alerts` endpoints are not wired to the UI yet, and `POST /tracking/` does not save anything.
- **Price tracking runs in the browser:** While the app is open, every 3 minutes one tracked product (the one checked longest ago) is re-scraped via `/tracking/check-prices`. There is no server-side background job.
- **Price history is an estimate:** The Price Graphic shows AI-estimated monthly prices based on web search, not recorded price data.
- **Coupons are samples:** Campaign coupons come from a static list (`is_sample: true`). Only the news section is live.
- **Scraping can be blocked:** Some marketplaces (e.g. Trendyol, Hepsiburada) may block the scraper. The Compare Agent then relies on Google Search grounding; if Gemini also fails, a local fallback report is returned (`model_used: "local-fallback"`) and it is not cached.
- **Analysis cache:** Successful product analyses are reused for 7 days. Delete `backend/.cache/compare_analysis.json` to force a fresh analysis.
- **No authentication:** The frontend sends a fixed `X-User-Id: mock-user-001` header.
- **Settings are UI-only:** The theme and currency selectors on the Profile page are not functional; there is no dark mode.
- **`src/data/generate_products.js` is outdated:** Running it **overwrites** `src/data/products.js` with an older 5-product catalog. Do not run it.
- **`src/lib/supabaseClient.js` is unused:** It imports `@supabase/supabase-js`, which is not listed in `package.json`; importing it would break the build.

---

## 🤝 Contributing

1. Fork this repository.
2. Create a new feature branch: `git checkout -b feature/new-awesome-feature`
3. Commit your changes: `git commit -m 'Add some awesome feature'`
4. Push to the branch: `git push origin feature/new-awesome-feature`
5. Open a Pull Request.

*If you encounter any issues during development, please feel free to report them in the Issues tab.*

## 📄 License

This project is licensed under the [MIT License](LICENSE).
