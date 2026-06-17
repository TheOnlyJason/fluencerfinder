#!/usr/bin/env bash
# Cloudflare Pages build (run from repo root).
set -euo pipefail
cd "$(dirname "$0")/creator-discovery/frontend"
npm ci
npm run build
