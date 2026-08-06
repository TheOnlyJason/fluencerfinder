// Always same-origin. In production the Cloudflare Worker (worker.js) proxies
// API paths (/search, /health, ...) to Render; in dev Vite proxies them to
// :8000. We intentionally ignore VITE_API_URL so a stale dashboard env var
// can't force direct cross-origin calls (which ad blockers / CORS break).
const API_BASE = "";

import { supabase } from "./supabase";

/** Authorization header carrying the current Supabase session token, for the
 *  backend's auth-gated endpoints (/search, admin routes). Empty when signed out. */
export async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function isApiConfigured(): boolean {
  return true;
}

export function apiErrorMessage(context: "discover" | "load"): string {
  if (import.meta.env.DEV) {
    return context === "discover"
      ? "Discovery failed. Start the API with: uvicorn app.main:app --reload --port 8000"
      : "Could not load accounts. Is the API running on port 8000?";
  }
  return context === "discover"
    ? "Discovery failed. The backend may be waking up (free tier, ~30-60s) — try again in a moment."
    : "Could not load accounts from the API.";
}

export interface Account {
  account_id: string;
  creator_id: string | null;
  platform: string;
  handle: string;
  display_handle?: string;
  display_name: string | null;
  profile_url: string | null;
  bio_text: string | null;
  channel_type: string | null;
  niche: string | null;
  secondary_niches: string | null;
  hobbies: string | null;
  location_text: string | null;
  contact_email: string | null;
  language: string | null;
  classification_confidence: number | null;
  follower_count: number | null;
  tier?: number | null;
  distance_miles?: number | null;
  is_active: boolean;
  created_at?: string;
  creator_name?: string | null;
}

export const TIER_OPTIONS: { value: number; label: string; range: string }[] = [
  { value: 1, label: "Tier 1 (1M+)", range: "1M+" },
  { value: 2, label: "Tier 2 (500K–1M)", range: "500K–1M" },
  { value: 3, label: "Tier 3 (200K–500K)", range: "200K–500K" },
  { value: 4, label: "Tier 4 (100K–200K)", range: "100K–200K" },
  { value: 5, label: "Tier 5 (<100K)", range: "<100K" },
];

/** Derive a creator's tier (1–5) from follower count, or null if unknown. */
export function followerTier(count: number | null | undefined): number | null {
  if (count == null || count < 0) return null;
  if (count >= 1_000_000) return 1;
  if (count >= 500_000) return 2;
  if (count >= 200_000) return 3;
  if (count >= 100_000) return 4;
  return 5;
}

export function tierLabel(tier: number | null | undefined): string | null {
  if (tier == null) return null;
  return TIER_OPTIONS.find((t) => t.value === tier)?.label ?? `Tier ${tier}`;
}

/** Just the follower-range portion of a tier (e.g. "1M+", "500K–1M"). */
export function tierRange(tier: number | null | undefined): string | null {
  if (tier == null) return null;
  return TIER_OPTIONS.find((t) => t.value === tier)?.range ?? null;
}

export interface AccountListResponse {
  items: Account[];
  total: number;
  total_in_database: number;
  approximate_nearby?: number;
  near_resolved?: string | null;
}

export interface AccountFacets {
  platforms: string[];
  niches: string[];
  channel_types: string[];
  locations: string[];
  total: number;
}

export interface AccountFilters {
  platforms?: string[];
  niches?: string[];
  locations?: string[];
  tiers?: number[];
  channel_type?: string;
  q?: string;
  min_followers?: number;
  max_followers?: number;
  near?: string;
  radius_miles?: number;
}

export interface SearchResult {
  account: Account;
  creator_name: string | null;
  source: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  sources: Record<string, number>;
  from_database: number;
  from_providers: number;
  matched_in_database?: number;
  parsed?: ParsedSearchCriteria | null;
}

export interface ParsedSearchCriteria {
  topic?: string | null;
  location?: string | null;
  min_followers?: number | null;
  max_followers?: number | null;
}

export interface Creator {
  creator_id: string;
  canonical_name: string;
  primary_language: string | null;
  home_region: string | null;
  overall_topics: string | null;
  identity_confidence: number;
  accounts: Account[];
}

export function formatFollowerCount(
  count: number | null | undefined,
  platform: string
): string | null {
  if (count == null || count <= 0) return null;
  const label = platform === "YouTube" ? "subscribers" : "followers";
  if (count >= 1_000_000) {
    const v = count / 1_000_000;
    return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}M ${label}`;
  }
  if (count >= 10_000) return `${Math.round(count / 1_000)}K ${label}`;
  if (count >= 1_000) {
    const v = count / 1_000;
    return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}K ${label}`;
  }
  return `${count.toLocaleString()} ${label}`;
}

export function formatFollowerShort(count: number): string {
  if (count >= 1_000_000) {
    const v = count / 1_000_000;
    return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}M`;
  }
  if (count >= 1_000) {
    const v = count / 1_000;
    return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}K`;
  }
  return String(count);
}

export function describeParsedSearch(parsed: ParsedSearchCriteria): string {
  const parts: string[] = [];
  if (parsed.topic) parts.push(parsed.topic);
  if (parsed.location) parts.push(`in ${parsed.location}`);
  if (parsed.min_followers != null && parsed.max_followers != null) {
    parts.push(`${formatFollowerShort(parsed.min_followers)}–${formatFollowerShort(parsed.max_followers)} followers`);
  } else if (parsed.min_followers != null) {
    parts.push(`>${formatFollowerShort(parsed.min_followers)} followers`);
  } else if (parsed.max_followers != null) {
    parts.push(`<${formatFollowerShort(parsed.max_followers)} followers`);
  }
  return parts.join(" · ");
}

export function parseFollowerInput(value: string): number | undefined {
  const trimmed = value.trim().replace(/,/g, "");
  if (!trimmed) return undefined;
  const match = trimmed.match(/^(\d+(?:\.\d+)?)\s*([kKmM])?$/);
  if (!match) {
    const n = Number(trimmed);
    return Number.isFinite(n) && n >= 0 ? Math.round(n) : undefined;
  }
  let n = parseFloat(match[1]);
  const suffix = (match[2] || "").toUpperCase();
  if (suffix === "K") n *= 1_000;
  if (suffix === "M") n *= 1_000_000;
  return Math.round(n);
}

export type AccountSort = "followers" | "new" | "recent" | "handle" | "distance";

export async function listAccounts(
  filters: AccountFilters = {},
  limit = 500,
  sort: AccountSort = "followers",
  offset = 0
): Promise<AccountListResponse> {
  const params = new URLSearchParams({ limit: String(limit), sort, offset: String(offset) });
  for (const p of filters.platforms ?? []) params.append("platforms", p);
  for (const n of filters.niches ?? []) params.append("niches", n);
  for (const l of filters.locations ?? []) params.append("locations", l);
  for (const t of filters.tiers ?? []) params.append("tiers", String(t));
  if (filters.channel_type) params.set("channel_type", filters.channel_type);
  if (filters.q) params.set("q", filters.q);
  if (filters.min_followers != null) params.set("min_followers", String(filters.min_followers));
  if (filters.max_followers != null) params.set("max_followers", String(filters.max_followers));
  if (filters.near) params.set("near", filters.near);
  if (filters.radius_miles != null) params.set("radius_miles", String(filters.radius_miles));
  const res = await fetch(`${API_BASE}/accounts?${params}`);
  if (!res.ok) throw new Error("Failed to load accounts");
  return res.json();
}

/** Place names usable as a radius-search center (for the "Near" picker). */
export async function fetchGeoPlaces(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/accounts/geo/places`);
  if (!res.ok) return [];
  return (await res.json()).places ?? [];
}

export async function getAccountFacets(): Promise<AccountFacets> {
  const res = await fetch(`${API_BASE}/accounts/facets`);
  if (!res.ok) throw new Error("Failed to load filter options");
  return res.json();
}

export async function searchCreators(
  query: string,
  filters: AccountFilters = {},
  // Database-only by default (fast, reliable). When true, also runs slow
  // external web discovery (web search + scraping + LLM enrichment).
  deepWeb = false
): Promise<SearchResponse> {
  const minFollowers = filters.min_followers;
  const maxFollowers = filters.max_followers;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 120_000);
  try {
    const res = await fetch(`${API_BASE}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(await authHeader()) },
      body: JSON.stringify({
        query,
        platforms: filters.platforms?.length ? filters.platforms : undefined,
        niche: filters.niches?.[0] || undefined,
        location: filters.locations?.[0] || undefined,
        min_followers: minFollowers,
        max_followers: maxFollowers,
        limit: 100,
        use_external_providers: deepWeb,
      }),
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = "";
      try {
        const body = await res.json();
        detail = body.error || body.detail || "";
      } catch {
        detail = await res.text().catch(() => "");
      }
      throw new Error(detail || `Search failed (${res.status})`);
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Search timed out after 2 minutes. The backend may be busy — try a narrower query or try again.");
    }
    throw err;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function getCreator(id: string): Promise<Creator> {
  const res = await fetch(`${API_BASE}/creators/${id}`);
  if (!res.ok) throw new Error("Creator not found");
  return res.json();
}

export async function importCsv(file: File): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/imports/csv`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Import failed");
  return res.json();
}

export function exportCsvUrl(
  platform?: string,
  niche?: string,
  location?: string,
  channel_type?: string
): string {
  const params = new URLSearchParams();
  if (platform) params.set("platform", platform);
  if (niche) params.set("niche", niche);
  if (location) params.set("location", location);
  if (channel_type) params.set("channel_type", channel_type);
  const qs = params.toString();
  return `${API_BASE}/exports/csv${qs ? `?${qs}` : ""}`;
}

export function exportJsonUrl(): string {
  return `${API_BASE}/exports/json`;
}

async function pingHealthOnce(timeoutMs: number): Promise<{
  ok: boolean;
  status: number;
  detail: string;
}> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    if (res.ok) {
      return { ok: true, status: res.status, detail: "connected" };
    }
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.error || body.detail || detail;
    } catch {
      /* ignore */
    }
    return { ok: false, status: res.status, detail };
  } catch {
    return { ok: false, status: 0, detail: "Could not reach /health" };
  } finally {
    window.clearTimeout(timer);
  }
}

// Render's free tier sleeps after ~15 min idle and can take 30-60s to wake.
// Retry several times before declaring the API offline so a cold start is not
// mistaken for an outage. onAttempt lets the UI show a "waking up" message.
export async function checkApiHealth(onAttempt?: (attempt: number) => void): Promise<{
  ok: boolean;
  status: number;
  detail: string;
}> {
  const attempts = 4;
  let last = { ok: false, status: 0, detail: "Could not reach /health" };
  for (let i = 0; i < attempts; i++) {
    onAttempt?.(i + 1);
    last = await pingHealthOnce(30_000);
    if (last.ok) return last;
    // Retry on network errors / 502 / 503 (cold start), not on real 4xx.
    if (last.status !== 0 && last.status !== 502 && last.status !== 503) return last;
    if (i < attempts - 1) await new Promise((r) => window.setTimeout(r, 3_000));
  }
  return last;
}
