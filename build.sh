#!/usr/bin/env bash
# Cloudflare Pages build (run from repo root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/creator-discovery/frontend"

# Bake Render API URL into the frontend (avoids Cloudflare 30s proxy timeout on /search).
export VITE_API_URL="${VITE_API_URL:-https://fluencerfinder.onrender.com}"

npm ci
npm run build

echo "Build complete. Output: creator-discovery/frontend/dist"
echo "VITE_API_URL=${VITE_API_URL}"
