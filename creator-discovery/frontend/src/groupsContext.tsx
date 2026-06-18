import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import {
  createGroup as apiCreateGroup,
  deleteGroup as apiDeleteGroup,
  listGroups,
  renameGroup as apiRenameGroup,
  type Group,
} from "./groups";
import { useAuth } from "./auth";

interface GroupsState {
  groups: Group[];
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  create: (name: string) => Promise<Group>;
  rename: (id: string, name: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  adjustMemberCount: (id: string, delta: number) => void;
}

const GroupsContext = createContext<GroupsState | undefined>(undefined);

export function GroupsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!user) {
      setGroups([]);
      return;
    }
    setLoading(true);
    try {
      setGroups(await listGroups());
      setError("");
    } catch (e: any) {
      setError(e.message || "Could not load groups");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(
    async (name: string) => {
      const g = await apiCreateGroup(name);
      setGroups((prev) => [g, ...prev]);
      return g;
    },
    []
  );

  const rename = useCallback(async (id: string, name: string) => {
    await apiRenameGroup(id, name);
    setGroups((prev) => prev.map((g) => (g.id === id ? { ...g, name } : g)));
  }, []);

  const remove = useCallback(async (id: string) => {
    await apiDeleteGroup(id);
    setGroups((prev) => prev.filter((g) => g.id !== id));
  }, []);

  const adjustMemberCount = useCallback((id: string, delta: number) => {
    setGroups((prev) =>
      prev.map((g) =>
        g.id === id ? { ...g, member_count: Math.max(0, (g.member_count ?? 0) + delta) } : g
      )
    );
  }, []);

  return (
    <GroupsContext.Provider
      value={{ groups, loading, error, refresh, create, rename, remove, adjustMemberCount }}
    >
      {children}
    </GroupsContext.Provider>
  );
}

export function useGroups(): GroupsState {
  const ctx = useContext(GroupsContext);
  if (!ctx) throw new Error("useGroups must be used within GroupsProvider");
  return ctx;
}
