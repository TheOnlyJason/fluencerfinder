import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Account,
  AccountFacets,
  AccountFilters,
  apiErrorMessage,
  fetchGeoPlaces,
  getAccountFacets,
  listAccounts,
  TIER_OPTIONS,
} from "../api";
import {
  computeFacets,
  filterAccounts,
  formatSnapshotAge,
  loadInfluencerSnapshot,
  sortAccounts,
} from "../localCatalog";
import MultiSelect from "../components/MultiSelect";
import AccountCard, { isRecentlyAdded } from "../components/AccountCard";
import Pagination from "../components/Pagination";
import { useSelection } from "../selection";

const EMPTY_FILTERS = {
  q: "",
  platform: [] as string[],
  niche: [] as string[],
  location: [] as string[],
  channel_type: "",
  tier: [] as string[],
};

type FilterForm = typeof EMPTY_FILTERS;
type SortKey = "followers" | "new" | "recent" | "handle" | "distance";

const RADIUS_OPTIONS = [5, 10, 15, 25, 50];

const PAGE_SIZE = 20;

function buildAccountFilters(form: FilterForm): AccountFilters {
  const cleaned: AccountFilters = {};
  if (form.q) cleaned.q = form.q;
  if (form.platform.length) cleaned.platforms = form.platform;
  if (form.niche.length) cleaned.niches = form.niche;
  if (form.location.length) cleaned.locations = form.location;
  if (form.channel_type) cleaned.channel_type = form.channel_type;
  if (form.tier.length) cleaned.tiers = form.tier.map(Number);
  return cleaned;
}

export default function DatabasePage() {
  const { isSelected, toggle } = useSelection();
  // Same initial reference for both so the mount-time debounce flush is an
  // Object.is no-op instead of a spurious identity change that would cancel
  // and re-issue the first fetch.
  const [filters, setFilters] = useState<FilterForm>(EMPTY_FILTERS);
  const [sort, setSort] = useState<SortKey>("followers");
  const [debouncedFilters, setDebouncedFilters] = useState<FilterForm>(EMPTY_FILTERS);
  const [catalog, setCatalog] = useState<Account[] | null>(null);
  const [snapshotChecked, setSnapshotChecked] = useState(false);
  const [snapshotExportedAt, setSnapshotExportedAt] = useState<string | null>(null);
  // Catalog (snapshot) mode: full filtered list, paginated client-side.
  // API mode: just the current page of results, paginated server-side.
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [totalFiltered, setTotalFiltered] = useState(0);
  const [totalInDatabase, setTotalInDatabase] = useState(0);
  const [facets, setFacets] = useState<AccountFacets | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  // Bumped by the Retry button so a failed fetch can be re-issued even though
  // none of the fetch effect's other deps (page, filters, sort) changed.
  const [fetchTick, setFetchTick] = useState(0);
  // Radius ("near") search state.
  const [near, setNear] = useState("");
  const [debouncedNear, setDebouncedNear] = useState("");
  const [radius, setRadius] = useState(25);
  const [geoPlaces, setGeoPlaces] = useState<string[]>([]);
  const [approximateNearby, setApproximateNearby] = useState(0);
  // The place name the backend actually resolved (null = not found).
  const [nearResolved, setNearResolved] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(totalFiltered / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pageAccounts = useMemo(
    () => (catalog ? accounts.slice(pageStart, pageStart + PAGE_SIZE) : accounts),
    [catalog, accounts, pageStart]
  );

  useEffect(() => {
    setPage(1);
  }, [debouncedFilters, sort, debouncedNear, radius]);

  // Debounce the free-text "Near" input so typing doesn't fire a fetch per key.
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedNear(near.trim()), 400);
    return () => window.clearTimeout(timer);
  }, [near]);

  // Keep the sort control honest: default to "Nearest" when a location becomes
  // active, and revert off "distance" when it clears (so the dropdown value
  // always matches the actual ordering). Only fires on near transitions, so an
  // explicit sort choice while searching is preserved.
  useEffect(() => {
    if (debouncedNear) {
      setSort((s) => (s === "followers" ? "distance" : s));
    } else {
      setSort((s) => (s === "distance" ? "followers" : s));
    }
  }, [debouncedNear]);

  // Load the place picker options once.
  useEffect(() => {
    fetchGeoPlaces().then(setGeoPlaces).catch(() => {});
  }, []);

  const goToPage = useCallback((next: number) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const hasActiveFilters = useMemo(
    () =>
      Boolean(near) ||
      Object.values(filters).some((v) => (Array.isArray(v) ? v.length > 0 : Boolean(v))),
    [filters, near]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedFilters(filters), 300);
    return () => window.clearTimeout(timer);
  }, [filters]);

  const applyLocalCatalog = useCallback(
    (source: Account[], sortOverride?: SortKey, formOverride?: FilterForm) => {
      const cleaned = buildAccountFilters(formOverride ?? debouncedFilters);
      const filtered = filterAccounts(source, cleaned);
      const sorted = sortAccounts(filtered, sortOverride ?? sort);
      setAccounts(sorted);
      setTotalFiltered(sorted.length);
      setTotalInDatabase(source.length);
      setFacets(computeFacets(source));
      setLoadingList(false);
    },
    [debouncedFilters, sort]
  );

  // On mount: prefer the local snapshot (instant, offline-friendly); otherwise
  // load facets and let the fetch effect below pull the first page from the API.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const snapshot = await loadInfluencerSnapshot();
      if (cancelled) return;
      if (snapshot?.accounts?.length) {
        setCatalog(snapshot.accounts);
        setSnapshotExportedAt(snapshot.exported_at);
      } else {
        try {
          const data = await getAccountFacets();
          if (!cancelled) setFacets(data);
        } catch (err) {
          console.error(err);
        }
      }
      if (!cancelled) setSnapshotChecked(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!snapshotChecked) return;
    // Radius search needs the API (the client-side snapshot has no coordinates),
    // so a "near" query forces API mode even if a snapshot is loaded.
    if (catalog && !debouncedNear) {
      applyLocalCatalog(catalog);
      return;
    }
    // Server-side pagination: fetch just the current page so the whole
    // database is browsable (the API caps a single request at 500 rows).
    let cancelled = false;
    (async () => {
      setLoadingList(true);
      setError("");
      try {
        const cleaned = buildAccountFilters(debouncedFilters);
        if (debouncedNear) {
          cleaned.near = debouncedNear;
          cleaned.radius_miles = radius;
        }
        // "distance" is only valid with a location; fall back otherwise.
        const effectiveSort: SortKey =
          sort === "distance" && !debouncedNear ? "followers" : sort;
        const data = await listAccounts(cleaned, PAGE_SIZE, effectiveSort, pageStart);
        if (cancelled) return;
        setAccounts(data.items);
        setTotalFiltered(data.total);
        setTotalInDatabase(data.total_in_database);
        setApproximateNearby(debouncedNear ? data.approximate_nearby ?? 0 : 0);
        setNearResolved(debouncedNear ? data.near_resolved ?? null : null);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          // Clear the previous page's rows so they aren't rendered under the
          // new page's "Showing X–Y" label; the error banner + Retry take over.
          setAccounts([]);
          setError(apiErrorMessage("load"));
        }
      } finally {
        if (!cancelled) setLoadingList(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [snapshotChecked, catalog, debouncedFilters, sort, debouncedNear, radius, pageStart, fetchTick, applyLocalCatalog]);

  function updateFilter(key: keyof FilterForm, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function updateMultiFilter(
    key: "platform" | "niche" | "location" | "tier",
    values: string[]
  ) {
    setFilters((prev) => ({ ...prev, [key]: values }));
  }

  function clearFilters() {
    setFilters({ ...EMPTY_FILTERS });
    setSort("followers");
    setNear("");
    setDebouncedNear("");
    setRadius(25);
  }

  function isNewAccount(account: Account): boolean {
    if (sort === "new" || sort === "recent") return isRecentlyAdded(account.created_at);
    return false;
  }

  return (
    <div>
      <section className="page-intro">
        <h1>Creator Database</h1>
        <p>Browse and filter every creator in your database.</p>
      </section>

      <section className="filter-panel">
        <div className="filter-panel-header">
          <h2>Filters</h2>
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
          <input
            className="search-input"
            list="geo-places"
            placeholder="📍 Near (city)…"
            value={near}
            onChange={(e) => setNear(e.target.value)}
            aria-label="Find creators near a location"
          />
          <datalist id="geo-places">
            {geoPlaces.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
          {near && (
            <select
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              aria-label="Search radius in miles"
            >
              {RADIUS_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  Within {r} mi
                </option>
              ))}
            </select>
          )}
          <MultiSelect
            label="Platforms"
            options={(facets?.platforms ?? ["Instagram", "TikTok", "X", "YouTube", "Twitch"]).map(
              (p) => ({ value: p, label: p })
            )}
            selected={filters.platform}
            onChange={(v) => updateMultiFilter("platform", v)}
          />
          <MultiSelect
            label="Niches"
            options={(facets?.niches ?? []).map((n) => ({ value: n, label: n }))}
            selected={filters.niche}
            onChange={(v) => updateMultiFilter("niche", v)}
          />
          <MultiSelect
            label="Locations"
            options={(facets?.locations ?? []).map((l) => ({ value: l, label: l }))}
            selected={filters.location}
            onChange={(v) => updateMultiFilter("location", v)}
          />
          <MultiSelect
            label="Tiers"
            options={TIER_OPTIONS.map((t) => ({ value: String(t.value), label: t.label }))}
            selected={filters.tier}
            onChange={(v) => updateMultiFilter("tier", v)}
          />
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
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label="Sort accounts"
          >
            {(near || sort === "distance") && <option value="distance">Sort: Nearest</option>}
            <option value="followers">Sort: Followers (high → low)</option>
            <option value="new">Sort: Newest added</option>
            <option value="handle">Sort: Handle (A → Z)</option>
          </select>
        </div>
      </section>

      {error && (
        <div className="error">
          {error}{" "}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setFetchTick((t) => t + 1)}
          >
            Retry
          </button>
        </div>
      )}

      <div className="results-meta">
        {loadingList
          ? "Loading accounts..."
          : error
            ? ""
            : totalFiltered === 0
              ? hasActiveFilters
                ? `Showing 0 of ${totalInDatabase} accounts`
                : `${totalInDatabase} account${totalInDatabase === 1 ? "" : "s"} in database`
              : `Showing ${pageStart + 1}–${pageStart + pageAccounts.length} of ${totalFiltered}${
                  hasActiveFilters ? ` (filtered from ${totalInDatabase})` : ""
                }`}
        {debouncedNear && !loadingList && !error && (
          <span className="snapshot-note" style={{ marginLeft: 8 }}>
            📍 within {radius} mi
            {approximateNearby > 0 &&
              ` · ${approximateNearby} more have only approximate (state-level) locations`}
          </span>
        )}
      </div>

      {!loadingList && !error && totalFiltered === 0 && (
        <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          {debouncedNear && nearResolved === null
            ? `We couldn't find a location matching “${debouncedNear}”. Try a nearby city (e.g. “Los Angeles, CA”).`
            : debouncedNear
              ? `No creators found within ${radius} mi of ${nearResolved}. Try a larger radius or a bigger metro — coverage is densest in major cities.`
              : hasActiveFilters
                ? "No accounts match these filters. Try clearing filters or broadening your search."
                : "No accounts yet. Use the Search page to find and classify creators."}
        </p>
      )}

      {accounts.length > 0 && (
        <>
          <div className="results-grid">
            {pageAccounts.map((account) => (
              <AccountCard
                key={account.account_id}
                account={account}
                creatorName={account.creator_name}
                showAddedAt={sort === "new" || sort === "recent"}
                isNew={isNewAccount(account)}
                selectable
                selected={isSelected(account.account_id)}
                onToggleSelect={toggle}
              />
            ))}
          </div>
          <Pagination page={currentPage} totalPages={totalPages} onChange={goToPage} />
        </>
      )}
    </div>
  );
}
