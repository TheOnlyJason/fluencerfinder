/** Client-side influencer catalog loaded from /influencers.json for fast browsing. */
import type { Account, AccountFacets, AccountFilters, AccountSort } from "./api";

export interface InfluencerSnapshot {
  exported_at: string;
  total: number;
  creators: Array<{
    creator_id: string;
    canonical_name: string;
    home_region: string | null;
    overall_topics: string | null;
    identity_confidence: number;
  }>;
  accounts: Account[];
}

const TOPIC_ALIASES: Record<string, string[]> = {
  gamer: ["gamer", "gaming", "game", "games", "esports", "twitch", "streamer", "videogame"],
  gaming: ["gaming", "gamer", "game", "games", "esports", "twitch", "streamer"],
  fitness: ["fitness", "gym", "workout", "trainer", "crossfit", "health"],
  beauty: ["beauty", "makeup", "skincare", "cosmetic", "glam"],
  food: ["food", "cooking", "chef", "recipe", "culinary"],
  fashion: ["fashion", "style", "ootd", "outfit"],
  tech: ["tech", "technology", "developer", "coding", "software"],
  travel: ["travel", "wanderlust", "adventure", "nomad"],
  music: ["music", "musician", "artist", "singer", "dj"],
  comedy: ["comedy", "comedian", "funny", "humor"],
  tft: ["tft", "teamfight", "tactics", "league", "lol"],
};

function expandTopicTerms(topic: string): string[] {
  const key = topic.trim().toLowerCase();
  if (TOPIC_ALIASES[key]) return [...new Set(TOPIC_ALIASES[key])];
  for (const [aliasKey, terms] of Object.entries(TOPIC_ALIASES)) {
    if (terms.includes(key) || aliasKey.includes(key) || key.includes(aliasKey)) {
      return [...new Set([key, ...terms])];
    }
  }
  return key.length >= 3 ? [key] : [];
}

function accountText(account: Account): string {
  return [
    account.handle,
    account.display_name,
    account.bio_text,
    account.niche,
    account.channel_type,
    account.hobbies,
    account.secondary_niches,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export async function loadInfluencerSnapshot(): Promise<InfluencerSnapshot | null> {
  try {
    const res = await fetch("/influencers.json");
    if (!res.ok) return null;
    const data = (await res.json()) as InfluencerSnapshot;
    if (!Array.isArray(data.accounts) || data.accounts.length === 0) return null;
    return data;
  } catch {
    return null;
  }
}

export function filterAccounts(accounts: Account[], filters: AccountFilters): Account[] {
  return accounts.filter((account) => {
    if (!account.is_active) return false;
    if (filters.platform && account.platform !== filters.platform) return false;

    if (filters.niche) {
      const terms = expandTopicTerms(filters.niche);
      const text = accountText(account);
      if (!terms.some((term) => text.includes(term))) return false;
    }

    if (filters.location) {
      const city = filters.location.split(",")[0].trim().toLowerCase();
      const loc = (account.location_text || "").toLowerCase();
      const bio = (account.bio_text || "").toLowerCase();
      if (!loc.includes(filters.location.toLowerCase()) && !loc.includes(city) && !bio.includes(city)) {
        return false;
      }
    }

    if (filters.channel_type) {
      const needle = filters.channel_type.toLowerCase();
      const hay = [account.channel_type, account.niche].filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(needle)) return false;
    }

    if (filters.q) {
      const needle = filters.q.toLowerCase();
      const hay = [
        account.handle,
        account.display_name,
        account.bio_text,
        account.niche,
        account.location_text,
        account.contact_email,
        account.channel_type,
        account.hobbies,
        account.creator_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!hay.includes(needle)) return false;
    }

    if (filters.min_followers != null) {
      if (account.follower_count == null || account.follower_count < filters.min_followers) return false;
    }
    if (filters.max_followers != null) {
      if (account.follower_count == null || account.follower_count > filters.max_followers) return false;
    }

    return true;
  });
}

export function sortAccounts(accounts: Account[], sort: AccountSort): Account[] {
  const copy = [...accounts];
  if (sort === "handle") {
    copy.sort((a, b) => a.handle.localeCompare(b.handle));
    return copy;
  }
  if (sort === "followers") {
    copy.sort((a, b) => (b.follower_count ?? 0) - (a.follower_count ?? 0));
    return copy;
  }
  copy.sort((a, b) => {
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
    return bTime - aTime;
  });
  return copy;
}

export function computeFacets(accounts: Account[]): AccountFacets {
  const unique = (values: Array<string | null | undefined>, skipUnknown = false): string[] => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const value of values) {
      if (!value) continue;
      if (skipUnknown && value.toLowerCase() === "unknown") continue;
      const key = value.trim();
      if (key && !seen.has(key)) {
        seen.add(key);
        out.push(key);
      }
    }
    return out.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  };

  return {
    platforms: unique(accounts.map((a) => a.platform)),
    niches: unique(accounts.map((a) => a.niche), true),
    channel_types: unique(accounts.map((a) => a.channel_type), true),
    locations: unique(accounts.map((a) => a.location_text)).slice(0, 40),
    total: accounts.length,
  };
}

export function mergeAccounts(existing: Account[], incoming: Account[]): Account[] {
  const byId = new Map(existing.map((a) => [a.account_id, a]));
  for (const account of incoming) {
    byId.set(account.account_id, account);
  }
  return [...byId.values()];
}

export function formatSnapshotAge(exportedAt: string): string {
  const date = new Date(exportedAt);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString();
}
