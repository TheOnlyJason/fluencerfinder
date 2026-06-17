#!/usr/bin/env bash
# Cloudflare Pages build (run from repo root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/creator-discovery/frontend"

# No VITE_API_URL: the frontend calls same-origin relative paths (e.g. /search),
# which the Cloudflare Worker (worker.js) proxies to Render. Same-origin avoids
# CORS and ad-blocker (ERR_BLOCKED_BY_CLIENT) issues.

npm ci
npm run build

echo "Build complete. Output: creator-discovery/frontend/dist"
