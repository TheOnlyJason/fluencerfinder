#!/usr/bin/env bash
# Deploy the FastAPI backend to Google Cloud Run from source.
# Reads creator-discovery/.env (gitignored) for env vars/secrets.
#
# Usage:
#   GCP_PROJECT=your-project-id ./deploy-cloudrun.sh
# Optional env: GCP_REGION (default us-east1), SERVICE_NAME (default fluencerfinder),
#               MIN_INSTANCES (default 0; set 1 to eliminate cold starts).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

REGION="${GCP_REGION:-us-east1}"
SERVICE="${SERVICE_NAME:-fluencerfinder}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"

if [ -z "${PROJECT:-}" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "ERROR: No GCP project. Run: gcloud config set project YOUR_PROJECT_ID" >&2
  echo "       or: GCP_PROJECT=YOUR_PROJECT_ID ./deploy-cloudrun.sh" >&2
  exit 1
fi
[ -f .env ] || { echo "ERROR: .env not found in $DIR" >&2; exit 1; }

# Build a Cloud Run env-vars YAML from .env (handles values with commas safely).
TMP_ENV="$(mktemp)"
trap 'rm -f "$TMP_ENV"' EXIT
python3 - "$TMP_ENV" <<'PY'
import sys
out = sys.argv[1]
pairs = {}
for ln in open(".env", encoding="utf-8").read().splitlines():
    s = ln.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    k, v = k.strip(), v.strip()
    if k == "DATABASE_URL" and v.startswith("sqlite"):
        continue  # never ship the local sqlite default
    pairs[k] = v
pairs["APP_ENV"] = "production"
with open(out, "w", encoding="utf-8") as f:
    for k, v in pairs.items():
        vv = v.replace("\\", "\\\\").replace('"', '\\"')
        f.write(f'{k}: "{vv}"\n')
PY

echo "Deploying '$SERVICE' to project=$PROJECT region=$REGION (min-instances=$MIN_INSTANCES)..."
gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances "$MIN_INSTANCES" \
  --max-instances 3 \
  --env-vars-file "$TMP_ENV"

echo
echo "Service URL:"
gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)'
echo
echo "Next: put that URL in worker.js (API_ORIGIN) and push."
