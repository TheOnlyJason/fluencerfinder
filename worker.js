// Cloudflare Worker: serves the built SPA from [assets] and proxies API
// requests to the backend from the SAME origin. Same-origin proxying avoids
// CORS entirely and prevents ad blockers / privacy extensions from blocking
// cross-site requests (net::ERR_BLOCKED_BY_CLIENT).
//
// The backend URL comes from the API_ORIGIN environment variable (set in the
// Cloudflare dashboard / wrangler vars), so it can be repointed (Render, Cloud
// Run, a local ngrok tunnel, ...) without editing code. FALLBACK_ORIGIN is only
// used if API_ORIGIN is unset.
const FALLBACK_ORIGIN = "https://fluencerfinder-1007753976919.us-east1.run.app";
const API_PREFIXES = [
  "/health",
  "/search",
  "/accounts",
  "/creators",
  "/imports",
  "/exports",
  "/identity",
];

function resolveOrigin(env) {
  return (env.API_ORIGIN || FALLBACK_ORIGIN).replace(/\/$/, "");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const isApi = API_PREFIXES.some(
      (p) => url.pathname === p || url.pathname.startsWith(p + "/")
    );
    if (!isApi) {
      return env.ASSETS.fetch(request);
    }

    const target = resolveOrigin(env) + url.pathname + url.search;
    const headers = new Headers(request.headers);
    headers.delete("host");
    // Skip ngrok's free-tier browser interstitial so JSON passes through.
    headers.set("ngrok-skip-browser-warning", "true");

    // Buffer the body so the proxied request doesn't depend on request-stream
    // duplex support (which can hang POSTs in the Workers runtime).
    const hasBody = request.method !== "GET" && request.method !== "HEAD";
    const body = hasBody ? await request.arrayBuffer() : undefined;

    return fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });
  },

  // Cron keep-alive: ping the backend so a sleeping free tier doesn't spin down
  // (avoids cold starts on the first request). Scheduled via [triggers] in
  // wrangler.toml.
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(
      fetch(`${resolveOrigin(env)}/health`, { cf: { cacheTtl: 0 } }).catch(
        () => {}
      )
    );
  },
};
