# Cloudflare deployment (Pages + Functions)

Frontend on **Cloudflare Pages**, API on **Render** (Docker), proxied through Pages Functions on the same domain.

## Cloudflare Workers Git setup (your screen)

If you see **"Set up your application"** with Build command / Deploy command:

| Field | Value |
|-------|--------|
| **Project name** | `fluencerfinder` |
| **Build command** | *(leave empty — build runs in deploy command)* |
| **Deploy command** | `cd creator-discovery/frontend && npm ci && npm run build && npm run pages:deploy` |
| **Builds for non-production branches** | ✓ checked |

Then click **Deploy**.

After deploy, go to **Settings → Variables** and add:

| Variable | Value |
|----------|--------|
| `API_ORIGIN` | `https://fluencerfinder-api.onrender.com` *(your Render API URL)* |

> **Note:** Use **Pages** (static site + functions), not a blank Worker script. The deploy command above uses `wrangler.toml` in `creator-discovery/frontend/` which deploys as Pages.

### Alternative: Cloudflare Pages (recommended UI)

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Select `TheOnlyJason/fluencerfinder`
3. Build settings:

| Setting | Value |
|---------|--------|
| **Root directory** | `creator-discovery/frontend` |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `dist` |

4. Add `API_ORIGIN` env var (same as above)

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

## 2. Deploy the frontend (Cloudflare)

See **Cloudflare Workers Git setup** at the top of this doc, or use **Pages → Connect to Git** with root directory `creator-discovery/frontend`.

Your site will be at `https://fluencerfinder.pages.dev` (or custom domain).

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

## Production troubleshooting (Discover failed)

Cloudflare only hosts the **frontend**. Discover calls `/search` → Cloudflare Function → **Render API**.

### Checklist

1. **Render API deployed?**  
   [render.com](https://render.com) → Blueprint from repo → service `fluencerfinder-api`  
   Put Supabase + OpenAI + Tavily keys on **Render** (not Cloudflare).

2. **Render health works?**  
   Open `https://fluencerfinder-api.onrender.com/health` → should return `{"status":"ok",...}`

3. **API_ORIGIN on Cloudflare?**  
   Cloudflare project → **Settings → Variables** → add:
   ```
   API_ORIGIN = https://fluencerfinder-api.onrender.com
   ```
   Redeploy after adding.

4. **CORS on Render?**  
   Render env `CORS_ORIGINS` must include your live Cloudflare URL, e.g.:
   ```
   https://fluencerfinder.pages.dev,https://YOUR-SUBDOMAIN.workers.dev
   ```

5. **Test on production**  
   Open `https://YOUR-SITE/health` in the browser:
   - **503** → `API_ORIGIN` not set on Cloudflare
   - **404** → Pages Functions not deployed (redeploy with `functions/_middleware.ts`)
   - **`status: ok`** → API connected; Discover should work

### Supabase secrets

| Where | What |
|-------|------|
| **Render** | `SUPABASE_URL`, `SUPABASE_DB_PASSWORD`, `SUPABASE_POOLER_HOST`, API keys |
| **Cloudflare** | Only `API_ORIGIN` (your Render URL) |

Supabase dashboard secrets alone do not power Discover on Cloudflare.

## CLI login

```bash
npx wrangler login
```
