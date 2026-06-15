const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export function isApiConfigured(): boolean {
  return Boolean(API_BASE) || import.meta.env.DEV;
}

export function apiErrorMessage(context: "discover" | "load"): string {
  if (import.meta.env.DEV) {
    return context === "discover"
      ? "Discovery failed. Start the API with: uvicorn app.main:app --reload --port 8000"
      : "Could not load accounts. Is the API running on port 8000?";
  }
  if (!API_BASE) {
    return (
      "Discovery needs a deployed backend API. On Cloudflare Pages, set API_ORIGIN to your backend URL " +
      "(Render/Railway). Browsing still works from influencers.json without the API."
    );
  }
  return context === "discover"
    ? `Discovery failed. Could not reach the API at ${API_BASE}. Check that the backend is running and CORS allows this site.`
    : `Could not load accounts from ${API_BASE}.`;
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
  is_active: boolean;
  created_at?: string;
  creator_name?: string | null;
}

export interface AccountListResponse {
  items: Account[];
  total: number;
  total_in_database: number;
}

export interface AccountFacets {
  platforms: string[];
  niches: string[];
  channel_types: string[];
  locations: string[];
  total: number;
}

export interface AccountFilters {
  platform?: string;
  niche?: string;
  location?: string;
  channel_type?: string;
  q?: string;
  min_followers?: number;
  max_followers?: number;
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

export type AccountSort = "followers" | "new" | "recent" | "handle";

export async function listAccounts(
  filters: AccountFilters = {},
  limit = 500,
  sort: AccountSort = "followers"
): Promise<AccountListResponse> {
  const params = new URLSearchParams({ limit: String(limit), sort });
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.niche) params.set("niche", filters.niche);
  if (filters.location) params.set("location", filters.location);
  if (filters.channel_type) params.set("channel_type", filters.channel_type);
  if (filters.q) params.set("q", filters.q);
  if (filters.min_followers != null) params.set("min_followers", String(filters.min_followers));
  if (filters.max_followers != null) params.set("max_followers", String(filters.max_followers));
  const res = await fetch(`${API_BASE}/accounts?${params}`);
  if (!res.ok) throw new Error("Failed to load accounts");
  return res.json();
}

export async function getAccountFacets(): Promise<AccountFacets> {
  const res = await fetch(`${API_BASE}/accounts/facets`);
  if (!res.ok) throw new Error("Failed to load filter options");
  return res.json();
}

export async function searchCreators(
  query: string,
  filters: AccountFilters = {}
): Promise<SearchResponse> {
  const minFollowers = filters.min_followers;
  const maxFollowers = filters.max_followers;
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      platforms: filters.platform ? [filters.platform] : undefined,
      niche: filters.niche || undefined,
      location: filters.location || undefined,
      min_followers: minFollowers,
      max_followers: maxFollowers,
      limit: 100,
    }),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
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
