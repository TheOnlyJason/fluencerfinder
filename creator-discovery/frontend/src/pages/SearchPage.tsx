import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Account,
  AccountFacets,
  AccountFilters,
  apiErrorMessage,
  checkApiHealth,
  describeParsedSearch,
  exportCsvUrl,
  exportJsonUrl,
  formatFollowerCount,
  formatFollowerShort,
  getAccountFacets,
  listAccounts,
  parseFollowerInput,
  searchCreators,
} from "../api";
import type { ParsedSearchCriteria } from "../api";
import {
  computeFacets,
  filterAccounts,
  formatSnapshotAge,
  loadInfluencerSnapshot,
  mergeAccounts,
  sortAccounts,
} from "../localCatalog";

function accountHandle(account: Account): string {
  return account.display_handle || account.handle;
}

function showChannelType(account: Account): boolean {
  if (!account.channel_type || account.channel_type === "mixed" || account.channel_type === "unknown") {
    return false;
  }
  if (account.niche && account.channel_type.toLowerCase() === account.niche.toLowerCase()) {
    return false;
  }
  return true;
}

function showCreatorLink(account: Account, creatorName?: string | null): boolean {
  if (!creatorName || !account.creator_id) return false;
  const name = account.display_name?.trim().toLowerCase();
  const creator = creatorName.trim().toLowerCase();
  return Boolean(creator && creator !== name);
}

const EMPTY_FILTERS = {
  q: "",
  platform: "",
  niche: "",
  location: "",
  channel_type: "",
  min_followers: "",
  max_followers: "",
};

type FilterForm = typeof EMPTY_FILTERS;

function buildAccountFilters(form: FilterForm): AccountFilters {
  const cleaned: AccountFilters = {};
  if (form.q) cleaned.q = form.q;
  if (form.platform) cleaned.platform = form.platform;
  if (form.niche) cleaned.niche = form.niche;
  if (form.location) cleaned.location = form.location;
  if (form.channel_type) cleaned.channel_type = form.channel_type;
  const minFollowers = parseFollowerInput(form.min_followers);
  const maxFollowers = parseFollowerInput(form.max_followers);
  if (minFollowers != null) cleaned.min_followers = minFollowers;
  if (maxFollowers != null) cleaned.max_followers = maxFollowers;
  return cleaned;
}

function formFromParsed(parsed: ParsedSearchCriteria): FilterForm {
  return {
    ...EMPTY_FILTERS,
    niche: parsed.topic || "",
    location: parsed.location || "",
    min_followers:
      parsed.min_followers != null ? formatFollowerShort(parsed.min_followers) : "",
    max_followers:
      parsed.max_followers != null ? formatFollowerShort(parsed.max_followers) : "",
  };
}

function formatAddedAt(iso: string | undefined): string | null {
  if (!iso) return null;
  const added = new Date(iso);
  if (Number.isNaN(added.getTime())) return null;

  const diffMs = Date.now() - added.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "Added just now";
  if (diffMin < 60) return `Added ${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `Added ${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay === 1) return "Added yesterday";
  if (diffDay < 7) return `Added ${diffDay}d ago`;
  return `Added ${added.toLocaleDateString()}`;
}

function isRecentlyAdded(iso: string | undefined, withinHours = 24): boolean {
  if (!iso) return false;
  const added = new Date(iso);
  if (Number.isNaN(added.getTime())) return false;
  return Date.now() - added.getTime() < withinHours * 60 * 60 * 1000;
}

function AccountCard({
  account,
  creatorName,
  showAddedAt = false,
  isNew = false,
}: {
  account: Account;
  creatorName?: string | null;
  showAddedAt?: boolean;
  isNew?: boolean;
}) {
  const followers = formatFollowerCount(account.follower_count, account.platform);
  const addedLabel = showAddedAt ? formatAddedAt(account.created_at) : null;

  return (
    <div className={`result-card${isNew ? " result-card-new" : ""}`}>
      <div className="result-header">
        <div>
          <div className="result-handle">
            @{accountHandle(account)}
            {account.profile_url && (
              <a
                href={account.profile_url}
                target="_blank"
                rel="noreferrer"
                style={{ marginLeft: 8, fontSize: "0.85rem" }}
              >
                ↗
              </a>
            )}
          </div>
          {account.display_name && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              {account.display_name}
            </div>
          )}
          {followers && (
            <div className="follower-count">{followers}</div>
          )}
        </div>
        <span className="platform-badge">{account.platform}</span>
      </div>
      {addedLabel && <div className="added-at">{addedLabel}</div>}
      {account.bio_text && <p className="result-bio">{account.bio_text}</p>}
      <div className="result-tags">
        {account.niche && account.niche !== "unknown" && (
          <span className="tag tag-niche">{account.niche}</span>
        )}
        {showChannelType(account) && (
          <span className="tag">{account.channel_type}</span>
        )}
        {account.location_text && (
          <span className="tag">📍 {account.location_text}</span>
        )}
        {account.contact_email && (
          <a href={`mailto:${account.contact_email}`} className="tag tag-email">
            ✉ {account.contact_email}
          </a>
        )}
        {account.hobbies && <span className="tag">{account.hobbies}</span>}
        {showCreatorLink(account, creatorName) && (
          <Link
            to={`/creators/${account.creator_id}`}
            className="tag"
            style={{ color: "var(--accent)" }}
          >
            👤 {creatorName}
          </Link>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  const [discoverQuery, setDiscoverQuery] = useState("Los Angeles fitness creators");
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS });
  const [sort, setSort] = useState<"followers" | "new" | "recent" | "handle">("followers");
  const [debouncedFilters, setDebouncedFilters] = useState({ ...EMPTY_FILTERS });
  const [catalog, setCatalog] = useState<Account[] | null>(null);
  const [snapshotExportedAt, setSnapshotExportedAt] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [total, setTotal] = useState(0);
  const [totalInDatabase, setTotalInDatabase] = useState(0);
  const [facets, setFacets] = useState<AccountFacets | null>(null);
  const [lastSearch, setLastSearch] = useState<{
    query: string;
    fromProviders: number;
    matchedInDatabase: number;
    parsedSummary?: string;
  } | null>(null);
  const [newAccountIds, setNewAccountIds] = useState<Set<string>>(new Set());
  const [discovering, setDiscovering] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState("");
  const [apiStatus, setApiStatus] = useState<string | null>(null);

  const hasActiveFilters = useMemo(
    () => Object.values(filters).some((v) => Boolean(v)),
    [filters]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedFilters(filters), 300);
    return () => window.clearTimeout(timer);
  }, [filters]);

  const loadFacets = useCallback(async () => {
    if (catalog) {
      setFacets(computeFacets(catalog));
      return;
    }
    try {
      const data = await getAccountFacets();
      setFacets(data);
    } catch (err) {
      console.error(err);
    }
  }, [catalog]);

  const applyLocalCatalog = useCallback((
    source: Account[],
    sortOverride?: typeof sort,
    formOverride?: FilterForm,
  ) => {
    const cleaned = buildAccountFilters(formOverride ?? debouncedFilters);
    const filtered = filterAccounts(source, cleaned);
    const sorted = sortAccounts(filtered, sortOverride ?? sort);
    setAccounts(sorted);
    setTotal(sorted.length);
    setTotalInDatabase(source.length);
    setFacets(computeFacets(source));
    setLoadingList(false);
  }, [debouncedFilters, sort]);

  const loadAccounts = useCallback(async (
    sortOverride?: typeof sort,
    formOverride?: FilterForm,
  ) => {
    if (catalog) {
      applyLocalCatalog(catalog, sortOverride, formOverride);
      return;
    }
    setLoadingList(true);
    setError("");
    try {
      const cleaned = buildAccountFilters(formOverride ?? debouncedFilters);
      const data = await listAccounts(cleaned, 500, sortOverride ?? sort);
      setAccounts(data.items);
      setTotal(data.total);
      setTotalInDatabase(data.total_in_database);
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage("load"));
    } finally {
      setLoadingList(false);
    }
  }, [applyLocalCatalog, catalog, debouncedFilters, sort]);

  useEffect(() => {
    if (!import.meta.env.PROD) return;
    checkApiHealth().then((health) => {
      if (health.ok) {
        setApiStatus(null);
        return;
      }
      if (health.status === 503) {
        setApiStatus(
          "Discover is offline: set API_ORIGIN in Cloudflare (Settings → Variables) to your Render API URL, then redeploy."
        );
      } else if (health.status === 404) {
        setApiStatus(
          "Discover is offline: API routes are not deployed. Redeploy with Pages Functions (see docs/CLOUDFLARE.md)."
        );
      } else {
        setApiStatus(
          `Discover is offline: deploy the API on Render and set API_ORIGIN on Cloudflare. (/health → ${health.detail})`
        );
      }
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const snapshot = await loadInfluencerSnapshot();
      if (cancelled) return;
      if (snapshot?.accounts?.length) {
        setCatalog(snapshot.accounts);
        setSnapshotExportedAt(snapshot.exported_at);
        applyLocalCatalog(snapshot.accounts);
        return;
      }
      try {
        const data = await getAccountFacets();
        if (!cancelled) setFacets(data);
      } catch (err) {
        console.error(err);
      }
      if (!cancelled) {
        await loadAccounts();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!catalog) return;
    applyLocalCatalog(catalog);
  }, [catalog, debouncedFilters, sort, applyLocalCatalog]);

  function updateFilter(key: keyof typeof EMPTY_FILTERS, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function clearFilters() {
    setFilters({ ...EMPTY_FILTERS });
    setSort("followers");
  }

  async function handleDiscover(e?: React.FormEvent) {
    e?.preventDefault();
    setDiscovering(true);
    setError("");
    try {
      const data = await searchCreators(discoverQuery);
      const syncedFilters = data.parsed ? formFromParsed(data.parsed) : filters;
      setFilters(syncedFilters);
      setDebouncedFilters(syncedFilters);
      setLastSearch({
        query: data.query,
        fromProviders: data.from_providers,
        matchedInDatabase: data.matched_in_database ?? data.total,
        parsedSummary: data.parsed ? describeParsedSearch(data.parsed) : undefined,
      });
      const addedIds = data.results
        .filter((r) => r.source === "provider")
        .map((r) => r.account.account_id);
      setNewAccountIds(new Set(addedIds));
      if (data.from_providers > 0 || data.parsed?.topic || data.parsed?.location) {
        setSort("new");
      }
      const discoveredAccounts = data.results.map((r) => ({
        ...r.account,
        creator_name: r.creator_name ?? r.account.creator_name,
      }));
      if (catalog) {
        const merged = mergeAccounts(catalog, discoveredAccounts);
        setCatalog(merged);
        applyLocalCatalog(merged, data.from_providers > 0 ? "new" : sort, syncedFilters);
      } else {
        setAccounts(discoveredAccounts);
        setTotal(discoveredAccounts.length);
        await loadFacets();
        await loadAccounts(data.from_providers > 0 ? "new" : undefined, syncedFilters);
      }
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "";
      setError(message && !message.startsWith("Discovery failed") ? `${apiErrorMessage("discover")} (${message})` : apiErrorMessage("discover"));
    } finally {
      setDiscovering(false);
    }
  }

  function isNewAccount(account: Account): boolean {
    if (newAccountIds.has(account.account_id)) return true;
    if (sort === "new" || sort === "recent") {
      return isRecentlyAdded(account.created_at);
    }
    return false;
  }

  return (
    <div>
      <section className="search-hero">
        <h1>Discover Creators</h1>
        <p>
          Find new creators by niche, topic, hobby, or location. Results are
          classified and saved to your database automatically.
        </p>
        <form className="search-form" onSubmit={handleDiscover}>
          <input
            className="search-input"
            value={discoverQuery}
            onChange={(e) => setDiscoverQuery(e.target.value)}
            placeholder='e.g. "gamer in Los Angeles with 10K–100K followers"'
          />
          <button type="submit" className="btn btn-primary" disabled={discovering}>
            {discovering ? "Discovering (may take ~60s)..." : "Discover new"}
          </button>
        </form>
      </section>

      <section className="filter-panel">
        <div className="filter-panel-header">
          <h2>Filter your database</h2>
          <div className="filter-panel-actions">
            {snapshotExportedAt && (
              <span className="snapshot-note" title="Loaded instantly from local JSON cache">
                Local snapshot · {formatSnapshotAge(snapshotExportedAt)}
              </span>
            )}
            {hasActiveFilters && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={clearFilters}>
                Clear filters
              </button>
            )}
          </div>
        </div>

        <div className="filters">
          <input
            className="search-input filter-grow"
            placeholder="Search handle, name, bio..."
            value={filters.q}
            onChange={(e) => updateFilter("q", e.target.value)}
          />
          <select
            value={filters.platform}
            onChange={(e) => updateFilter("platform", e.target.value)}
          >
            <option value="">All platforms</option>
            {(facets?.platforms ?? ["Instagram", "TikTok", "X", "YouTube"]).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <select
            value={filters.niche}
            onChange={(e) => updateFilter("niche", e.target.value)}
            aria-label="Filter by niche"
          >
            <option value="">All niches</option>
            {(facets?.niches ?? []).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <select
            value={filters.location}
            onChange={(e) => updateFilter("location", e.target.value)}
            aria-label="Filter by location"
          >
            <option value="">All locations</option>
            {(facets?.locations ?? []).map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <select
            value={filters.channel_type}
            onChange={(e) => updateFilter("channel_type", e.target.value)}
            aria-label="Filter by channel type"
          >
            <option value="">All channel types</option>
            {(facets?.channel_types ?? []).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            className="search-input filter-followers"
            type="text"
            inputMode="numeric"
            placeholder="Min followers (e.g. 10K)"
            value={filters.min_followers}
            onChange={(e) => updateFilter("min_followers", e.target.value)}
            aria-label="Minimum followers"
          />
          <input
            className="search-input filter-followers"
            type="text"
            inputMode="numeric"
            placeholder="Max followers (e.g. 100K)"
            value={filters.max_followers}
            onChange={(e) => updateFilter("max_followers", e.target.value)}
            aria-label="Maximum followers"
          />
          <select
            value={sort}
            onChange={(e) =>
              setSort(e.target.value as "followers" | "new" | "recent" | "handle")
            }
            aria-label="Sort accounts"
          >
            <option value="followers">Sort: Followers (high → low)</option>
            <option value="new">Sort: Newest added</option>
            <option value="handle">Sort: Handle (A → Z)</option>
          </select>
          <a
            href={exportJsonUrl()}
            className="btn btn-secondary"
            download="influencers.json"
          >
            Export JSON
          </a>
          <a
            href={exportCsvUrl(
              filters.platform || undefined,
              filters.niche || undefined,
              filters.location || undefined,
              filters.channel_type || undefined
            )}
            className="btn btn-secondary"
            download
          >
            Export CSV
          </a>
        </div>
      </section>

      {apiStatus && <div className="error">{apiStatus}</div>}
      {error && <div className="error">{error}</div>}

      {lastSearch && (
        <div className="results-meta">
          Last discovery: "{lastSearch.query}"
          {lastSearch.parsedSummary && (
            <> — understood as <strong>{lastSearch.parsedSummary}</strong></>
          )}
          {" "}— {lastSearch.matchedInDatabase} matching in database
          {lastSearch.fromProviders > 0
            ? `, ${lastSearch.fromProviders} new profiles saved`
            : ", no new profiles saved"}
          {lastSearch.matchedInDatabase <= 3 && (
            <span style={{ display: "block", marginTop: "0.35rem", opacity: 0.85 }}>
              Few matches is normal with strict filters (niche + city + follower range).
              Web search finds public profiles but can&apos;t verify every filter like a paid platform API.
              Try widening followers (e.g. 5K–500K) or removing location to see more.
            </span>
          )}
        </div>
      )}

      <div className="results-meta">
        {loadingList
          ? "Loading accounts..."
          : hasActiveFilters
            ? `Showing ${total} of ${totalInDatabase} accounts`
            : `${totalInDatabase} account${totalInDatabase === 1 ? "" : "s"} in database`}
      </div>

      {!loadingList && accounts.length === 0 && (
        <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          {hasActiveFilters
            ? "No accounts match these filters. Try clearing filters or broadening your search."
            : "No accounts yet. Use Discover new above to find and classify creators."}
        </p>
      )}

      {accounts.length > 0 && (
        <div className="results-grid">
          {accounts.map((account) => (
            <AccountCard
              key={account.account_id}
              account={account}
              creatorName={account.creator_name}
              showAddedAt={sort === "new" || sort === "recent"}
              isNew={isNewAccount(account)}
            />
          ))}
        </div>
      )}

    </div>
  );
}
