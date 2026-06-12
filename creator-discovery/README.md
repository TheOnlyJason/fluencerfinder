# Creator Discovery MVP

Multi-platform creator discovery and classification engine. Search by niche, topic, hobby, or location and get back creator handles with LLM-generated classifications across Instagram, TikTok, X, and YouTube.

Inspired by [RightFluencer](https://github.com/manojkarthick/rightfluencer) architecture (multi-platform pipeline mindset) but modernized with FastAPI, SQLModel, database-first search, and structured LLM categorization.

## Quick Start (Local SQLite)

```bash
cd creator-discovery

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Seed sample data
python scripts/seed_data.py

# Run API
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and search for **"Los Angeles fitness creators"**.

No API keys required for basic discovery — web search uses DuckDuckGo by default. Set `OPENAI_API_KEY` for LLM categorization and `TAVILY_API_KEY` / `YOUTUBE_API_KEY` for higher-quality discovery.

## Docker (Postgres)

```bash
docker compose up --build
```

API runs at http://localhost:8000. Set `DATABASE_URL=postgresql://creator:creator@localhost:5432/creator_discovery` if running the API outside Docker.

## Supabase (recommended for production)

Your project URL and anon key go in `.env`. The **database password** is separate — find it under **Project Settings → Database** in the Supabase dashboard (or reset it there if you don't have it).

```bash
SUPABASE_URL=https://dugsdvoqlpqcagrhnyvc.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_DB_PASSWORD=your-database-password
# Required on most networks — direct db.* host is IPv6-only
SUPABASE_POOLER_HOST=aws-1-us-east-1.pooler.supabase.com
SUPABASE_POOLER_PORT=5432
```

Copy the **pooler host** from **Dashboard → Database → Connection string** (Session mode). It may be `aws-1-...` rather than `aws-0-...`.

```bash
python scripts/seed_data.py
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health   # should show "database": "supabase"
```

**Notes:**
- The **anon key** is for future frontend/Auth use; the FastAPI backend uses the **database password** for SQLModel.
- Never commit `.env` or share your database password / service role key.
- Search on Postgres uses ILIKE; add `tsvector` indexes via Supabase migrations later if needed.

## API Examples

```bash
# Search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Los Angeles fitness creators"}'

# Import CSV
curl -X POST http://localhost:8000/imports/csv -F "file=@data/sample_creators.csv"

# Export CSV
curl http://localhost:8000/exports/csv -o creators_export.csv

# Health check
curl http://localhost:8000/health
```

See [docs/API.md](docs/API.md) for full endpoint reference.  
See [docs/THINGS_WE_NEED.md](docs/THINGS_WE_NEED.md) for API keys, Supabase setup, and checklist.

## Tests

```bash
pytest
```

## Project Structure

```
creator-discovery/
  app/           # FastAPI backend
  frontend/      # Vite + React UI
  data/          # Sample CSV seed data
  tests/         # Pytest suite
  scripts/       # Seed and utility scripts
  docs/          # API documentation
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/creator_discovery.db` | SQLite, Postgres, or Supabase URI |
| `OPENAI_API_KEY` | (empty) | OpenAI API key; mock mode when empty |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for classification/identity |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |

## MVP Limitations

- **Discovery**: Automatic web search (DuckDuckGo / Tavily) + optional YouTube API — finds real public profiles; Instagram/TikTok depth depends on search index coverage
- **Search**: SQLite FTS5 locally; Postgres uses ILIKE fallback (no tsvector yet)
- **Identity resolution**: Deterministic scoring + optional LLM; no human review queue UI
- **Background jobs**: Synchronous/async in-request; no Celery worker
- **CSV import**: Optional supplement only — not required for normal use

## Definition of Success

Enter "Los Angeles fitness creators" → get handles with classifications. Discovered creators persist in the database and are reused on later searches without re-classification when profiles are unchanged.
