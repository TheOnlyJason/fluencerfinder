# Creator Discovery — Setup Checklist

Everything needed to run and get good results from the app. Copy `.env.example` → `.env` and fill in the sections below.

---

## Required (local dev)

| Item | Status | Notes |
|------|--------|-------|
| Python 3.11+ | ☐ | Backend |
| Node.js 18+ | ☐ | Frontend (`frontend/`) |
| `.env` file | ☐ | `cp .env.example .env` |
| Backend running | ☐ | `uvicorn app.main:app --reload --port 8000` |
| Frontend running | ☐ | `cd frontend && npm run dev` → **http://localhost:5175** |

Verify:

```bash
curl http://localhost:8000/health
```

---

## Database (pick one)

### Option A — SQLite (easiest, local only)

```env
DATABASE_URL=sqlite:///./data/creator_discovery.db
```

No extra signup. Good for testing. Data stays on your machine.

### Option B — Supabase (recommended, what we use now)

| Variable | Where to get it |
|----------|-----------------|
| `SUPABASE_URL` | Dashboard → Project Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Dashboard → Project Settings → API → anon public key |
| `SUPABASE_DB_PASSWORD` | Dashboard → Project Settings → Database → password (reset if unknown) |
| `SUPABASE_POOLER_HOST` | Dashboard → Database → Connection string → **Session mode** host (e.g. `aws-1-us-east-1.pooler.supabase.com`) |
| `SUPABASE_POOLER_PORT` | Usually `5432` |

```bash
curl http://localhost:8000/health   # expect "database": "supabase"
```

**Important:** Use the **pooler** host on most networks. The direct `db.*.supabase.co` host is often IPv6-only and fails locally.

Never commit `.env` or share database passwords / service role keys.

---

## API keys

### OpenAI — classification & niche tagging

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `OPENAI_API_KEY` | **Strongly recommended** | Classifies creators (niche, channel type, hobbies). Without it, mock keyword rules are used. |
| `OPENAI_MODEL` | Optional | Default `gpt-4o-mini` |
| `OPENAI_BASE_URL` | Optional | Default OpenAI; change for compatible providers |

Get key: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

---

### Tavily — better creator discovery search

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `TAVILY_API_KEY` | **Recommended** | Higher-quality web search for finding Instagram/TikTok/X/YouTube profiles. Without it, DuckDuckGo is used (works but noisier). |

Get key: [tavily.com](https://tavily.com) → sign up → API keys

After adding to `.env`, **restart the backend** so uvicorn picks it up.

---

### YouTube Data API — YouTube channel discovery

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `YOUTUBE_API_KEY` | **Recommended for YouTube** | Finds real YouTube channels with subscriber counts from the official API. |

Get key:

1. [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable **YouTube Data API v3**
4. Credentials → Create API key
5. Restrict key to YouTube Data API v3 (recommended)

Without this key, YouTube discovery still runs via web search only (less reliable subscriber counts).

---

## Optional / tuning

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_MOCK_DISCOVERY` | `false` | Set `true` only for offline demo fake accounts |
| `CORS_ORIGINS` | `localhost:5173,3000` | Add `http://localhost:5175` if the frontend runs on 5175 |
| `APP_ENV` | `development` | Environment label |

---

## What each key unlocks

| Capability | No keys | + OpenAI | + Tavily | + YouTube |
|------------|---------|----------|----------|-----------|
| Search UI & filters | ✅ | ✅ | ✅ | ✅ |
| Save creators to DB | ✅ | ✅ | ✅ | ✅ |
| Web discovery (DDG) | ✅ | ✅ | — | — |
| Better web discovery | — | — | ✅ | — |
| LLM niche/location classify | mock | ✅ | ✅ | ✅ |
| YouTube API channel lookup | — | — | — | ✅ |
| YouTube caption niche enrichment | — | — | — | ✅ (needs YT key + captions on videos) |
| Follower enrichment | partial | partial | better | best for YT |

---

## One-time / maintenance scripts

```bash
source .venv/bin/activate

# Seed sample data (SQLite or fresh DB)
python scripts/seed_data.py

# Backfill follower counts for existing accounts
python scripts/backfill_followers.py

# Backfill location & email (no LLM)
python scripts/backfill_profiles.py

# Import RightFluencer seed data (~90 creators from archived MongoDB dumps)
# Requires clone of https://github.com/manojkarthick/rightfluencer at ../rightfluencer
python scripts/import_rightfluencer.py

# Export JSON snapshot for fast frontend loading (data/ + frontend/public/)
python scripts/export_influencers_json.py

# Enrich YouTube accounts with recent video caption text for niche tagging
python scripts/backfill_youtube_captions.py
```

---

## Natural language search examples

The discover bar understands combined queries:

```
gamer in Los Angeles with 10K–100K followers
fitness creators in Miami between 5K and 50K followers
tft content creator
```

Parsed into niche, location, and follower filters automatically.

**Note:** Strict filters (niche + city + follower range) return fewer results than paid influencer platforms — we use public web search, not Instagram/TikTok internal APIs.

---

## Still on the wishlist (not built yet)

These would improve results but are **not required** today:

| Item | Why it would help |
|------|-------------------|
| Instagram / TikTok official API or scraper | Exact followers, location, bio at scale |
| Paid influencer DB (Modash, HypeAuditor, etc.) | Pre-filtered creator lists by niche + geo + size |
| `TAVILY_API_KEY` + higher search limits | Already added — should improve discovery |
| Background job queue (Celery / cron) | Auto-enrich followers/location overnight |
| Postgres full-text search (`tsvector`) | Faster text search on large databases |
| Human review queue for identity merges | Safer duplicate creator linking |

---

## Quick restart after updating `.env`

```bash
# Terminal 1 — backend (Ctrl+C then)
cd creator-discovery && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd creator-discovery/frontend && npm run dev
```

Then hard-refresh the browser on **http://localhost:5175**.

---

## Security reminders

- Do **not** commit `.env`
- Rotate any keys that were pasted into chat or shared publicly
- Use Supabase **anon** key in frontend only; backend uses **database password**
- Never expose the Supabase **service role** key in the frontend
