# Cloudflare Pages deployment

Frontend on **Cloudflare Pages**, API on **Render** (Docker), proxied through Pages Functions on the same domain.

## 1. Deploy the API (Render)

1. Go to [render.com](https://render.com) → **New Blueprint** → connect `fluencerfinder` repo
2. Uses root `render.yaml` — creates `fluencerfinder-api` web service
3. Add env vars from your `creator-discovery/.env`:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_DB_PASSWORD`
   - `SUPABASE_POOLER_HOST`, `SUPABASE_POOLER_PORT`
   - `OPENAI_API_KEY`, `TAVILY_API_KEY`, `YOUTUBE_API_KEY`
   - `CORS_ORIGINS` — include your Cloudflare URL (see below)
4. After deploy, note the URL: `https://fluencerfinder-api.onrender.com`
5. Verify: `https://fluencerfinder-api.onrender.com/health`

## 2. Deploy the frontend (Cloudflare Pages)

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Select `TheOnlyJason/fluencerfinder`
3. Build settings:

| Setting | Value |
|---------|--------|
| **Root directory** | `creator-discovery/frontend` |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `dist` |

4. **Environment variables** (Production):

| Variable | Value |
|----------|--------|
| `API_ORIGIN` | `https://fluencerfinder-api.onrender.com` |

5. Deploy. Your site will be at `https://fluencerfinder.pages.dev` (or custom domain).

## 3. Update CORS on Render

After you know your Cloudflare URL, update Render env:

```
CORS_ORIGINS=https://fluencerfinder.pages.dev,https://your-custom-domain.com,http://localhost:5175
```

Redeploy the Render service.

## 4. Custom domain (optional)

Cloudflare Pages → **Custom domains** → add your domain.

## Local CLI deploy

```bash
cd creator-discovery/frontend
npm install
npm run build
npx wrangler pages deploy dist --project-name=fluencerfinder
```

## What works without API

- Browse/filter/sort from `influencers.json` (instant, no backend)

## What needs API_ORIGIN + Render

- **Discover new** creators
- Live DB export, CSV import, classification

## CLI login

```bash
npx wrangler login
```
