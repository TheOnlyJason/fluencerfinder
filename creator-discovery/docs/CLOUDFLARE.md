# Cloudflare Pages — production checklist

## Pages build settings (repo root)

| Setting | Value |
|---------|--------|
| **Build command** | `bash build.sh` |
| **Build output directory** | `creator-discovery/frontend/dist` |

## Environment variables (Cloudflare Pages)

| Variable | Value | Required? |
|----------|--------|-----------|
| `VITE_API_URL` | `https://fluencerfinder.onrender.com` | Optional — `build.sh` sets this by default |
| `API_ORIGIN` | `https://fluencerfinder.onrender.com` | Optional — for `/health` proxy via Functions |

## Render (`fluencerfinder` service — NOT `fluencerfinder-api`)

| Variable | Value |
|----------|--------|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_DB_PASSWORD` | from `.env` |
| `SUPABASE_POOLER_HOST`, `SUPABASE_POOLER_PORT` | from `.env` |
| `OPENAI_API_KEY`, `TAVILY_API_KEY`, `YOUTUBE_API_KEY` | from `.env` |
| `CORS_ORIGINS` | `https://fluencerfinder.onrender.com,http://localhost:5175` |

CORS also allows any `*.pages.dev` and `*.workers.dev` origin automatically.

## Verify

1. `https://fluencerfinder.onrender.com/health` → `{"status":"ok",...}`
2. Cloudflare site loads and shows influencer cards
3. **Discover new** — first request may take 30–90s (Render free tier cold start)

## Architecture

- **Browse/filter** → `influencers.json` (instant, no API)
- **Discover** → browser calls Render directly (`VITE_API_URL` baked at build time)
- **Health proxy** → `functions/_middleware.ts` at repo root (for same-origin `/health`)
