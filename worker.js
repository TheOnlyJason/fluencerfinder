// Cloudflare Worker: serves the built SPA from [assets] and proxies API
// requests to the Render backend from the SAME origin. Same-origin proxying
// avoids CORS entirely and prevents ad blockers / privacy extensions from
// blocking cross-site requests (net::ERR_BLOCKED_BY_CLIENT).
const API_ORIGIN = "https://fluencerfinder.onrender.com";
const API_PREFIXES = [
  "/health",
  "/search",
  "/accounts",
  "/creators",
  "/imports",
  "/exports",
  "/identity",
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const isApi = API_PREFIXES.some(
      (p) => url.pathname === p || url.pathname.startsWith(p + "/")
    );
    if (isApi) {
      const target = API_ORIGIN + url.pathname + url.search;
      // Reusing `request` preserves method, headers, and body.
      return fetch(new Request(target, request));
    }
    return env.ASSETS.fetch(request);
  },

  // Cron keep-alive: ping the backend so Render's free tier doesn't spin down
  // (avoids 30-60s cold starts on the first Discover). Scheduled via the
  // [triggers] crons entry in wrangler.toml.
  async scheduled(_event, _env, ctx) {
    ctx.waitUntil(
      fetch(`${API_ORIGIN}/health`, { cf: { cacheTtl: 0 } }).catch(() => {})
    );
  },
};
