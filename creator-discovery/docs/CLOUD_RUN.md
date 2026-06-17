# Deploy the backend to Google Cloud Run

Cloud Run runs the FastAPI backend as a container. Cold starts are ~1–3s (vs
30–60s on Render free), requests can run up to 60 min, and the always-free tier
covers light usage. The Cloudflare Worker proxies `/search`, `/health`, etc. to
this backend, so the frontend never changes — you only update `API_ORIGIN` in
`worker.js`.

## One-time setup

1. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install
2. Log in and pick/create a project (billing must be enabled — the free tier
   still requires a billing account, but light usage stays free):
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. Enable the required APIs:
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```

## Deploy

From the repo:
```bash
cd creator-discovery
chmod +x deploy-cloudrun.sh
GCP_PROJECT=YOUR_PROJECT_ID ./deploy-cloudrun.sh
```

The script:
- Builds the container from `creator-discovery/Dockerfile` (source deploy via Cloud Build).
- Reads `creator-discovery/.env` and sets the same env vars used on Render
  (Supabase creds, OpenAI/Tavily/YouTube keys). The local `sqlite` default is skipped.
- Deploys with `--allow-unauthenticated` (public API), `--port 8080`, `1Gi` memory,
  `--timeout 300`, `--min-instances 0`, `--max-instances 3`.
- Prints the service URL, e.g. `https://fluencerfinder-xxxxxxxxxx-ue.a.run.app`.

### Eliminate cold starts (optional)
Cold starts are short, but to remove them entirely keep one warm instance:
```bash
MIN_INSTANCES=1 GCP_PROJECT=YOUR_PROJECT_ID ./deploy-cloudrun.sh
```
(A warm instance costs a little; `min-instances 0` stays in the free tier.)

## Point the frontend at Cloud Run

1. Edit `worker.js` at the repo root and set:
   ```js
   const API_ORIGIN = "https://YOUR-CLOUD-RUN-URL";
   ```
2. Commit and push. Cloudflare redeploys the Worker; the proxy now targets Cloud Run.
3. With Cloud Run's fast cold starts (or `min-instances 1`), the cron keep-alive in
   `wrangler.toml` is optional — you can keep or remove it.

## Verify
```bash
curl https://YOUR-CLOUD-RUN-URL/health        # {"status":"ok",...}
curl https://fluencerfinder.death6030.workers.dev/health   # proxied, same response
```

## Updating later
Re-run `./deploy-cloudrun.sh` after code or env changes. To change a single env
var without a full `.env` sync:
```bash
gcloud run services update fluencerfinder --region us-east1 --update-env-vars KEY=value
```
