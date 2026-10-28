# Techno Track 🚀

Techno Track is an AI-powered product analysis and price-tracking platform for consumer electronics, built on a multi-agent FastAPI backend and a React frontend.

It helps users make smarter shopping decisions by identifying products from photos, searching and scraping live Turkish marketplace listings, comparing devices spec-by-spec, estimating price history, and answering follow-up questions through a context-aware chat assistant. All AI features run on Google's **Gemini** models, defaulting to the strongest Flash models that have free-tier quota.

> **Note:** This is a demo project. The product catalog contains **6 sample products** (`src/data/products.js`), not every product is included, and user data in the UI (favorites, tracked products, orders) is not persisted. See [Current Limitations](#current-limitations) before relying on any output.

---

## ✨ Key Features

- 🔍 **Visual Product Recognition:** Upload a photo or use the camera; the Vision Agent identifies the brand, model, color and visible specs, then the result is matched against the catalog. If no confident match is found, you can pick from suggested models of the detected brand.
- 📊 **In-Depth Product Analysis:** Scrapes the product's pages on Turkish marketplaces (Vatan, Trendyol, Hepsiburada, MediaMarkt) for price, rating, reviews and specs, then Gemini produces a BUY / WAIT / AVOID verdict, a review trust report, chronic issues, blind spots, honest pros/cons and the lowest price. Prices come only from the scraped pages (or from Google Search when the key allows grounding). Results are cached for 7 days.
- ⚖️ **Device Compare:** Compares **two** catalog devices head-to-head: grouped spec tables with per-row winners, scores, pros/cons, "best for" guidance and a summary article.
- 📈 **Price Graphic:** Builds a 12-month price chart for Turkey. On the free tier the current month is today's **live** lowest store price (found by the Detective Agent) and earlier months are clearly marked AI estimates; with Google Search grounding the model researches each month itself.
- 🔔 **Tracked Products:** Track a product with a target price for a chosen duration (or until an end date). While the app is open, store prices are re-scraped periodically (no AI call); when a store hits the target you get a toast and a notification, and optionally a *simulated* auto-buy that adds an order to the Orders page.
- 🏷️ **Campaigns:** Tech news from this week's RSS feeds of Turkish tech sites (webtekno, shiftdelete, donanimhaber, chip, technopat), selected and summarised in Turkish by Gemini with the original links, plus coupon cards for your linked store accounts (coupons are sample data).
- 💬 **Smart Chat Assistant:** A chat widget that receives the current product, price chart, device comparison or campaigns as context. Price questions asked before a chart exists get today's live store prices injected into the context; with grounding available, *when to buy* questions also use Google Search.
- 🎨 **Modern UI:** Light theme with glassmorphism effects and Framer Motion animations.

---

## 🤖 Architecture

The frontend calls a dedicated backend endpoint for each feature. The backend is a FastAPI app; every route is mounted under `/api/v1`. Every Gemini call goes through one shared REST client (`services/gemini_grounded.py`).

### Model ladder

Each feature tries the strongest model first and falls down the ladder when a model is overloaded, out of quota or retired:

| Rung | Default model | Notes (free tier, verified 2026-10-28) |
|---|---|---|
| 1 | `gemini-3.8-flash` (`FLASH_MODEL`) | Strongest model with free quota: 20 requests/day (shared with `gemini-3.7-flash`), often 503 "high demand" |
| 2 | `gemini-3.6-flash` (`FLASH_FALLBACK_MODEL`) | 20 requests/day; `gemini-3.5-flash` is served by this model |
| 3 | `gemini-3-flash-preview` | 20 requests/day |
| 4–5 | `gemini-3.5-flash-lite`, `gemini-flash-lite-latest` | Lite models that carry the load once the daily counters above are spent |

The shared client parks a model for as long as Google says its quota is exhausted (or 45 s after a 503/timeout), so a spent counter costs no extra round-trip. Every rung except the last gets at most 60 s to answer.

**Not available on the free tier:** Pro models (`gemini-3.1-pro-preview`, `gemini-4-argon`), every image-generation model, and **Google Search grounding**. The 2.5 family returns 404 for new projects. When grounding is refused, the same model is called again without it, using prompts that forbid inventing prices, and grounding is re-checked every 30 minutes, so a billed key gets grounded answers automatically.

### Features

| UI feature | Endpoint | Backend module | Model / data source |
|---|---|---|---|
| Visual search | `POST /vision/analyze-image` | `agents/vision_agent.py` | `VISION_MODEL` ladder; stops early once confidence ≥ 0.55 |
| Product analysis | `POST /analyze/compare` | `agents/compare_agent.py` | `ANALYST_MODEL` ladder on scraped store data → local fallback report |
| Device Compare | `POST /compare-devices` | `routes/compare_devices.py` | `COMPARE_DEVICES_MODEL` ladder (ungrounded) |
| Price Graphic | `POST /price-history` | `routes/price_history.py` | `PRICE_HISTORY_MODEL` ladder + live prices from the Detective Agent |
| Campaigns | `POST /campaigns` | `routes/campaigns.py` | `NEWS_MODEL` ladder over live RSS articles; coupons: static sample data |
| Chat widget | `POST /chat` | `services/gemini_proxy.py` | `CHAT_MODEL` ladder (+ Detective live prices for price questions) |
| Tracked products | `POST /tracking/check-prices` | `routes/tracking.py` | No AI call (reuses the Compare Agent's scraper) |

### Agents (`backend/agents/`)

1. **👀 Vision Agent** (`vision_agent.py`): Identifies the exact product in an image (brand, category, model, color, visible specs) with a calibrated confidence score, walking down the model ladder. *Used by the UI.*
2. **⚖️ Compare Agent** (`compare_agent.py`): Scrapes several store pages **of the same product** in parallel (JSON-LD / meta tags, Brotli-aware), rejects price outliers, and asks Gemini for a deep analysis: verdict, trust report (organic vs. suspicious reviews), chronic issues, blind spots, honest pros/cons and per-site summaries. Without grounding, prices and reviews come only from the scraped pages and a site whose page is blocked gets a `null` price; with grounding, Gemini looks the missing prices up. If Gemini is unavailable, a local report is built from the scraped data. Successful results are cached in `backend/.cache/compare_analysis.json` (7-day TTL). *Used by the UI.*
3. **🧠 Analyst Agent** (`analyst_agent.py`): Turns a list of reviews plus a price history into a BUY / WAIT / AVOID / UNCERTAIN strategy with fake-review percentage, chronic issues, sentiment map and red flags (`ANALYST_MODEL` ladder). *API-only:* available via `POST /analyze/reviews` and the Orchestrator.
4. **🕵️‍♂️ Detective Agent** (`detective_agent.py`): Searches **Vatan** and **MediaMarkt** live (dropping trailing keywords per store when a search is empty), lets Gemini (`DETECTIVE_MODEL` ladder) keep only listings that are the product itself (not cases, chargers or other models), then opens the matched product pages to collect real ratings and customer reviews. If nothing matches, it shortens the keywords and retries. Used by the Orchestrator, the Price Graphic and the chat's price answers.
5. **🎨 Visualizer Agent** (`visualizer_agent.py`): Uses Gemini native image generation (`IMAGE_MODEL`, default `gemini-nano-banana-2.1` → `gemini-3.1-flash-image`) to create an outfit photo for `fashion` products or a room-placement photo for `furniture` products, and uploads it to Supabase Storage (falls back to Base64). **Requires a billed Gemini key**; on the free tier it returns a clear "billing required" error. *API-only:* available via `POST /generate-style` and the Orchestrator; the electronics catalog does not use it.
6. **🎼 Orchestrator** (`orchestrator.py`): Runs the pipeline Vision → Detective → Analyst (→ Visualizer for fashion/furniture), streams agent logs over SSE (`GET /stream/pipeline/{session_id}`) and WebSocket (`/orchestrate/ws/{session_id}`), and saves the result to Supabase. The Analyst step is skipped when the matched listings expose no reviews. *API-only:* available via `POST /orchestrate`; the current UI does not call it.

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
│   ├── .cache/                   # Compare Agent analysis cache (git-ignored, created at runtime)
│   ├── agents/                   # vision, compare, analyst, detective, visualizer, orchestrator
│   ├── routes/                   # One router per endpoint group (see API Reference)
│   ├── services/
│   │   ├── gemini_client.py      # Auth / quota error helpers
│   │   ├── gemini_grounded.py    # Shared Gemini REST client: model ladder, quota parking, optional grounding, JSON repair, key hot reload
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
└── dist/                         # Production build output (npm run build, git-ignored)
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
- **Gemini REST API via `httpx`:** every model call (text, vision, image generation, optional Google Search grounding) goes through `services/gemini_grounded.py`; no Gemini SDK is needed
- **httpx + brotli:** marketplace search and scraping (Vatan, MediaMarkt, …) and RSS news feeds

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
SUPABASE_URL=https://your-project.supabase.co   # Project URL only, without /rest/v1
SUPABASE_KEY=your_supabase_service_role_key   # legacy service_role key (eyJ...), backend-only

# Optional
PORT=8000            # only used by `python -m backend.main`
APP_ENV=development  # "development" enables auto-reload with `python -m backend.main`
LOG_LEVEL=INFO
```

> `supabase==2.7.4` only accepts JWT-format keys, so use the **legacy `service_role` key** (Supabase Dashboard → Project Settings → API Keys → Legacy API Keys). The newer `sb_secret_...` / `sb_publishable_...` keys fail with "Invalid API key". The Gemini key is re-read on every call, so a rotated `GEMINI_API_KEY` applies without a restart.

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

Every default model can be overridden in `backend/.env`. Changing `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` moves every feature at once; the per-feature variables override a single feature.

| Variable | Default | Used by |
|---|---|---|
| `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | `gemini-3.8-flash` / `gemini-3.6-flash` | Default primary / fallback for every feature below |
| `EXTRA_FALLBACK_MODELS` | `gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-flash-lite-latest` | Comma-separated rungs tried after the fallback |
| `VISION_MODEL` / `VISION_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Vision Agent |
| `ANALYST_MODEL` / `ANALYST_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Compare Agent (product analysis) and Analyst Agent |
| `DETECTIVE_MODEL` / `DETECTIVE_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Detective Agent (listing relevance check) |
| `COMPARE_DEVICES_MODEL` / `COMPARE_DEVICES_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Device Compare |
| `PRICE_HISTORY_MODEL` / `PRICE_HISTORY_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Price Graphic |
| `NEWS_MODEL` / `NEWS_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Campaigns news |
| `CHAT_MODEL` / `CHAT_FALLBACK_MODEL` | `FLASH_MODEL` / `FLASH_FALLBACK_MODEL` | Chat |
| `IMAGE_MODEL` / `IMAGE_FALLBACK_MODEL` | `gemini-nano-banana-2.1` / `gemini-3.1-flash-image` | Visualizer Agent (billed key only) |

---

## 📡 API Reference

All routes are prefixed with `/api/v1`.

| Method | Path | Description | Used by UI |
|---|---|---|---|
| POST | `/vision/analyze-image` | Identify a product from a Base64 image | ✅ |
| POST | `/analyze/compare` | Multi-store scrape + Gemini deep analysis | ✅ |
| POST | `/compare-devices` | Two-device head-to-head comparison | ✅ |
| POST | `/price-history` | 12-month price history (live current price + estimates on the free tier) | ✅ |
| POST | `/campaigns` | Live tech news + sample coupons for linked accounts | ✅ |
| POST | `/chat` | Context-aware chat assistant | ✅ |
| POST | `/tracking/check-prices` | Scrape current store prices (no AI) | ✅ |
| POST | `/tracking/` | Register a price-tracking target (stub, not persisted) | — |
| POST | `/analyze/reviews` | Analyst Agent on given reviews + price history | — |
| POST | `/generate-style` | Visualizer Agent (fashion / furniture only, billed key) | — |
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
- **Free-tier Gemini quota is small:** `gemini-3.8-flash`, `gemini-3.6-flash` and `gemini-3-flash-preview` allow 20 requests/day each, and the newest models often answer 503 "high demand". After about 60 calls a day the app keeps working on the lite models, with lower answer quality. Quotas reset at midnight Pacific time.
- **No Google Search on the free tier:** Prices then come only from scraped store pages, the Price Graphic's earlier months are estimates, and news comes from RSS feeds. A billed key enables grounding automatically.
- **Detective Agent coverage:** It searches only Vatan and MediaMarkt; Trendyol, Hepsiburada, n11, Teknosa, Akakçe, Cimri and Amazon.com.tr block automated requests. Reviews come from Vatan product pages (MediaMarkt pages expose none), so the Orchestrator's Analyst step is skipped when only MediaMarkt matches.
- **No image generation on the free tier:** The Visualizer Agent needs a billed key.
- **API-only agents:** The Orchestrator, Analyst Agent and Visualizer Agent are not used by the current UI; the Detective Agent is reached through the Price Graphic and chat. `src/components/AgentTerminal.jsx` (an SSE log viewer) exists but is not mounted.
- **No persistence in the UI:** Favorites, tracked products and notifications live in React state and reset on page refresh. Orders, the profile and the linked store accounts are demo data. The Supabase-backed `/user/favorites` and `/user/alerts` endpoints are not wired to the UI yet, and `POST /tracking/` does not save anything.
- **Price tracking runs in the browser:** While the app is open, every 3 minutes one tracked product (the one checked longest ago) is re-scraped via `/tracking/check-prices`. There is no server-side background job.
- **Price history is partly estimated:** Only the current month is a live price; earlier months are AI estimates (or web-search based with grounding), not recorded price data. The chart says so when `grounded` is false.
- **Coupons are samples:** Campaign coupons come from a static list (`is_sample: true`). Only the news section is live.
- **Scraping can be blocked:** Some marketplaces (e.g. Trendyol, Hepsiburada) block the scraper. Their price then stays empty (or comes from Google Search when grounding is available); if Gemini also fails, a local fallback report is returned (`model_used: "local-fallback"`) and it is not cached.
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
