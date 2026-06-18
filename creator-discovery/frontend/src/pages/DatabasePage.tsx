import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Account,
  AccountFacets,
  AccountFilters,
  apiErrorMessage,
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

const EMPTY_FILTERS = {
  q: "",
  platform: [] as string[],
  niche: [] as string[],
  location: [] as string[],
  channel_type: "",
  tier: [] as string[],
};

type FilterForm = typeof EMPTY_FILTERS;
type SortKey = "followers" | "new" | "recent" | "handle";

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
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS });
  const [sort, setSort] = useState<SortKey>("followers");
  const [debouncedFilters, setDebouncedFilters] = useState({ ...EMPTY_FILTERS });
  const [catalog, setCatalog] = useState<Account[] | null>(null);
  const [snapshotExportedAt, setSnapshotExportedAt] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [totalInDatabase, setTotalInDatabase] = useState(0);
  const [facets, setFacets] = useState<AccountFacets | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(accounts.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pageAccounts = useMemo(
    () => accounts.slice(pageStart, pageStart + PAGE_SIZE),
    [accounts, pageStart]
  );

  useEffect(() => {
    setPage(1);
  }, [accounts]);

  const goToPage = useCallback((next: number) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const hasActiveFilters = useMemo(
    () => Object.values(filters).some((v) => (Array.isArray(v) ? v.length > 0 : Boolean(v))),
    [filters]
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
      setTotalInDatabase(source.length);
      setFacets(computeFacets(source));
      setLoadingList(false);
    },
    [debouncedFilters, sort]
  );

  const loadAccounts = useCallback(async () => {
    setLoadingList(true);
    setError("");
    try {
      const cleaned = buildAccountFilters(debouncedFilters);
      const data = await listAccounts(cleaned, 500, sort);
      setAccounts(data.items);
      setTotalInDatabase(data.total_in_database);
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage("load"));
    } finally {
      setLoadingList(false);
    }
  }, [debouncedFilters, sort]);

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
      if (!cancelled) await loadAccounts();
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!catalog) {
      loadAccounts();
      return;
    }
    applyLocalCatalog(catalog);
  }, [catalog, debouncedFilters, sort, applyLocalCatalog, loadAccounts]);

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
            <option value="followers">Sort: Followers (high → low)</option>
            <option value="new">Sort: Newest added</option>
            <option value="handle">Sort: Handle (A → Z)</option>
          </select>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <div className="results-meta">
        {loadingList
          ? "Loading accounts..."
          : accounts.length === 0
            ? hasActiveFilters
              ? `Showing 0 of ${totalInDatabase} accounts`
              : `${totalInDatabase} account${totalInDatabase === 1 ? "" : "s"} in database`
            : `Showing ${pageStart + 1}–${Math.min(pageStart + PAGE_SIZE, accounts.length)} of ${accounts.length}${
                hasActiveFilters ? ` (filtered from ${totalInDatabase})` : ""
              }`}
      </div>

      {!loadingList && accounts.length === 0 && (
        <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          {hasActiveFilters
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
              />
            ))}
          </div>
          <Pagination page={currentPage} totalPages={totalPages} onChange={goToPage} />
        </>
      )}
    </div>
  );
}
