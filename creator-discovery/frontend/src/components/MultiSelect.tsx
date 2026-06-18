import { useEffect, useRef, useState } from "react";

export interface MultiSelectOption {
  value: string;
  label: string;
}

export default function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: MultiSelectOption[];
  selected: string[];
  onChange: (values: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const summary =
    selected.length === 0
      ? `All ${label.toLowerCase()}`
      : selected.length === 1
        ? options.find((o) => o.value === selected[0])?.label ?? selected[0]
        : `${selected.length} ${label.toLowerCase()}`;

  return (
    <div className={`multiselect${open ? " is-open" : ""}`} ref={ref}>
      <button
        type="button"
        className="multiselect-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={selected.length ? "" : "multiselect-placeholder"}>{summary}</span>
        <span className="multiselect-caret" aria-hidden>
          ▾
        </span>
      </button>
      {open && (
        <div className="multiselect-panel" role="listbox" aria-multiselectable="true">
          <div className="multiselect-panel-head">
            <span>{label}</span>
            {selected.length > 0 && (
              <button type="button" className="multiselect-clear" onClick={() => onChange([])}>
                Clear
              </button>
            )}
          </div>
          {options.length === 0 ? (
            <div className="multiselect-empty">No options</div>
          ) : (
            options.map((o) => (
              <label key={o.value} className="multiselect-option">
                <input
                  type="checkbox"
                  checked={selected.includes(o.value)}
                  onChange={() => toggle(o.value)}
                />
                <span>{o.label}</span>
              </label>
            ))
          )}
        </div>
      )}
    </div>
  );
}
