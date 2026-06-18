function pageWindow(page: number, totalPages: number): (number | "…")[] {
  const items: (number | "…")[] = [];
  const add = (n: number) => items.push(n);
  const left = Math.max(2, page - 1);
  const right = Math.min(totalPages - 1, page + 1);
  add(1);
  if (left > 2) items.push("…");
  for (let i = left; i <= right; i++) add(i);
  if (right < totalPages - 1) items.push("…");
  if (totalPages > 1) add(totalPages);
  return items;
}

export default function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (next: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
      >
        ← Prev
      </button>
      {pageWindow(page, totalPages).map((item, idx) =>
        item === "…" ? (
          <span key={`gap-${idx}`} className="pagination-gap">
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            className={`pagination-page${item === page ? " is-active" : ""}`}
            onClick={() => onChange(item)}
            aria-current={item === page ? "page" : undefined}
          >
            {item}
          </button>
        )
      )}
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
      >
        Next →
      </button>
    </nav>
  );
}
