# fluencerfinder

Multi-platform **creator / influencer discovery and classification engine**. Search by niche,
topic, hobby, or location and get back creator handles with LLM-generated classifications across
Instagram, TikTok, X, and YouTube.

Inspired by [RightFluencer](https://github.com/manojkarthick/rightfluencer)'s multi-platform
pipeline approach, rebuilt with FastAPI, SQLModel, database-first search, and structured LLM
categorization.

## Repository layout

```
.
├── creator-discovery/     # The application (FastAPI backend + Vite/React frontend)
├── worker.js              # Cloudflare Worker: serves the SPA + same-origin API proxy
├── wrangler.toml          # Cloudflare Worker / Pages config
├── render.yaml            # Render blueprint for the FastAPI backend
└── Dockerfile             # Container image for the backend
```

The application lives in [`creator-discovery/`](creator-discovery/) — see its
[README](creator-discovery/README.md) for full setup, API reference, and deployment docs.

## Quick start

```bash
cd creator-discovery

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Seed the bundled sample dataset
python scripts/seed_data.py

# Run the API
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd creator-discovery/frontend
npm install
npm run dev
```

Open <http://localhost:5173> and search for **"Los Angeles fitness creators"**.

No API keys are required for basic discovery (web search falls back to DuckDuckGo). Set
`OPENAI_API_KEY` for LLM categorization and `TAVILY_API_KEY` / `YOUTUBE_API_KEY` for
higher-quality discovery. See [`.env.example`](creator-discovery/.env.example).

## Tech stack

- **Backend:** FastAPI, SQLModel, SQLite (dev) / Postgres / Supabase (prod)
- **Frontend:** React + Vite + TypeScript
- **Discovery:** DuckDuckGo / Tavily web search, YouTube Data API
- **Classification:** OpenAI-compatible LLM (structured output)
- **Deploy:** Cloudflare Workers/Pages (frontend + proxy), Render / Cloud Run / Docker (backend)

## Data & privacy

This repository ships with **synthetic sample data only**
([`creator-discovery/data/sample_creators.csv`](creator-discovery/data/sample_creators.csv)).

It does **not** include any real creator dataset. Files that may contain real contact
information — `*.xlsx` source workbooks and generated `influencers.json` snapshots — are
git-ignored and must never be committed. Populate your own database with the seed/import
scripts under [`creator-discovery/scripts/`](creator-discovery/scripts/).

If you use this tool to collect public profile data, make sure you comply with each
platform's Terms of Service and applicable privacy laws (GDPR/CCPA, etc.).

## Contributing

Issues and pull requests are welcome. Please:

1. Keep secrets out of commits — use `.env` (git-ignored), never hardcode API keys.
2. Never commit real creator/contact datasets.
3. Run `pytest` (in `creator-discovery/`) before opening a PR.

## License

[MIT](LICENSE) © 2026 TheOnlyJason
