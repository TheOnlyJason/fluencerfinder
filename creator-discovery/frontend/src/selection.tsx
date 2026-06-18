import { createContext, useCallback, useContext, useMemo, useState, ReactNode } from "react";
import type { Account } from "./api";

interface SelectionState {
  selected: Account[];
  count: number;
  isSelected: (id: string) => boolean;
  toggle: (account: Account) => void;
  clear: () => void;
}

const SelectionContext = createContext<SelectionState | undefined>(undefined);

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [map, setMap] = useState<Record<string, Account>>({});

  const toggle = useCallback((account: Account) => {
    setMap((prev) => {
      const next = { ...prev };
      if (next[account.account_id]) delete next[account.account_id];
      else next[account.account_id] = account;
      return next;
    });
  }, []);

  const clear = useCallback(() => setMap({}), []);

  const value = useMemo<SelectionState>(() => {
    const selected = Object.values(map);
    return {
      selected,
      count: selected.length,
      isSelected: (id: string) => Boolean(map[id]),
      toggle,
      clear,
    };
  }, [map, toggle, clear]);

  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>;
}

export function useSelection(): SelectionState {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used within SelectionProvider");
  return ctx;
}
