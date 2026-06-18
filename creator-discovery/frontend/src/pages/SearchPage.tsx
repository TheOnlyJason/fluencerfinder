import { useEffect, useMemo, useState } from "react";
import {
  Account,
  apiErrorMessage,
  checkApiHealth,
  describeParsedSearch,
  searchCreators,
} from "../api";
import AccountCard from "../components/AccountCard";
import Pagination from "../components/Pagination";

const PAGE_SIZE = 20;

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [deepWeb, setDeepWeb] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [results, setResults] = useState<Account[]>([]);
  const [newAccountIds, setNewAccountIds] = useState<Set<string>>(new Set());
  const [lastSearch, setLastSearch] = useState<{
    query: string;
    fromProviders: number;
    matchedInDatabase: number;
    parsedSummary?: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [apiStatus, setApiStatus] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const pageResults = useMemo(
    () => results.slice(pageStart, pageStart + PAGE_SIZE),
    [results, pageStart]
  );

  useEffect(() => {
    setPage(1);
  }, [results]);

  useEffect(() => {
    if (!import.meta.env.PROD) return;
    checkApiHealth((attempt) => {
      if (attempt > 1) setApiStatus("Waking up the discovery server (free tier, ~30-60s)…");
    }).then((health) => {
      setApiStatus(
        health.ok
          ? null
          : "Search couldn't reach the backend (it may still be waking up on the free tier). Try again in a minute."
      );
    });
  }, []);

  async function handleDiscover(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim()) return;
    setDiscovering(true);
    setError("");
    try {
      const data = await searchCreators(query, {}, deepWeb);
      setHasSearched(true);
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
      setResults(
        data.results.map((r) => ({
          ...r.account,
          creator_name: r.creator_name ?? r.account.creator_name,
        }))
      );
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "";
      setError(
        message && !message.startsWith("Discovery failed")
          ? `${apiErrorMessage("discover")} (${message})`
          : apiErrorMessage("discover")
      );
    } finally {
      setDiscovering(false);
    }
  }

  return (
    <div>
      <section className="search-hero">
        <h1>Discover Creators</h1>
        <p>
          Find new creators by niche, topic, hobby, or location. Results are classified and saved
          to your database automatically.
        </p>
        <form className="search-form" onSubmit={handleDiscover}>
          <input
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "gamer in Los Angeles with 10K–100K followers"'
          />
          <button type="submit" className="btn btn-primary" disabled={discovering || !query.trim()}>
            {discovering
              ? deepWeb
                ? "Searching the web (~60s)..."
                : "Searching..."
              : deepWeb
                ? "Search the web"
                : "Search"}
          </button>
        </form>
        <label className="deep-web-toggle">
          <input
            type="checkbox"
            checked={deepWeb}
            onChange={(e) => setDeepWeb(e.target.checked)}
            disabled={discovering}
          />
          <span>
            Also search the web for new creators (slower, ~60s — finds and saves profiles not yet in
            your database)
          </span>
        </label>
      </section>

      {apiStatus && <div className="error">{apiStatus}</div>}
      {error && <div className="error">{error}</div>}

      {lastSearch && (
        <div className="results-meta">
          Results for "{lastSearch.query}"
          {lastSearch.parsedSummary && (
            <>
              {" "}
              — understood as <strong>{lastSearch.parsedSummary}</strong>
            </>
          )}{" "}
          — {lastSearch.matchedInDatabase} matching in database
          {lastSearch.fromProviders > 0
            ? `, ${lastSearch.fromProviders} new profiles saved`
            : ", no new profiles saved"}
        </div>
      )}

      {hasSearched && !discovering && results.length === 0 && (
        <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          No creators matched. Try a broader query, or enable “search the web” to find new profiles.
        </p>
      )}

      {results.length > 0 && (
        <>
          <div className="results-grid">
            {pageResults.map((account) => (
              <AccountCard
                key={account.account_id}
                account={account}
                creatorName={account.creator_name}
                isNew={newAccountIds.has(account.account_id)}
              />
            ))}
          </div>
          <Pagination page={currentPage} totalPages={totalPages} onChange={setPage} />
        </>
      )}
    </div>
  );
}
