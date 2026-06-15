const API_PREFIXES = [
  "/health",
  "/search",
  "/accounts",
  "/creators",
  "/exports",
  "/imports",
  "/identity",
  "/openapi.json",
  "/docs",
  "/redoc",
];

function isApiPath(pathname: string): boolean {
  return API_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export const onRequest: PagesFunction<{ API_ORIGIN?: string }> = async (context) => {
  const { request, env, next } = context;
  const url = new URL(request.url);

  if (!isApiPath(url.pathname)) {
    return next();
  }

  const origin = env.API_ORIGIN?.replace(/\/$/, "");
  if (!origin) {
    return Response.json(
      {
        error:
          "API not configured. Set API_ORIGIN in Cloudflare Pages environment variables to your backend URL.",
      },
      { status: 503 }
    );
  }

  const target = `${origin}${url.pathname}${url.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");

  return fetch(target, {
    method: request.method,
    headers,
    body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
    redirect: "manual",
  });
};
