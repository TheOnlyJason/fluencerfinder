import { useState } from "react";
import { Link } from "react-router-dom";
import { useSelection } from "../selection";
import { useAuth } from "../auth";
import { useGroups } from "../groupsContext";
import { addAccountsToGroup } from "../groups";

export default function SelectionBar() {
  const { selected, count, clear } = useSelection();
  const { user } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  if (count === 0) return null;

  return (
    <>
      <div className="selection-bar">
        <span className="selection-count">{count} selected</span>
        <div className="selection-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={clear}>
            Clear
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setModalOpen(true)}>
            Add to group
          </button>
        </div>
      </div>
      {modalOpen && (
        <AddToGroupModal
          authed={Boolean(user)}
          onClose={() => setModalOpen(false)}
          onAdded={() => {
            setModalOpen(false);
            clear();
          }}
          selectedCount={count}
          getSelected={() => selected}
        />
      )}
    </>
  );
}

function AddToGroupModal({
  authed,
  onClose,
  onAdded,
  selectedCount,
  getSelected,
}: {
  authed: boolean;
  onClose: () => void;
  onAdded: () => void;
  selectedCount: number;
  getSelected: () => ReturnType<typeof useSelection>["selected"];
}) {
  const { groups, loading, create, refresh } = useGroups();
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function addTo(groupId: string) {
    setBusy(true);
    setError("");
    try {
      await addAccountsToGroup(groupId, getSelected());
      await refresh();
      onAdded();
    } catch (e: any) {
      setError(e.message || "Failed to add to group");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setBusy(true);
    setError("");
    try {
      const group = await create(newName.trim());
      await addAccountsToGroup(group.id, getSelected());
      await refresh();
      onAdded();
    } catch (e: any) {
      setError(e.message || "Failed to create group");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Add {selectedCount} to a group</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {!authed ? (
          <div className="modal-body">
            <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
              Sign in to save creators to groups.
            </p>
            <Link to="/login" className="btn btn-primary" onClick={onClose}>
              Sign in
            </Link>
          </div>
        ) : (
          <div className="modal-body">
            {error && <div className="error" style={{ padding: "0.5rem 0" }}>{error}</div>}

            <form className="create-group-row" onSubmit={handleCreate}>
              <input
                className="search-input"
                placeholder="New group name…"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                disabled={busy}
              />
              <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !newName.trim()}>
                Create &amp; add
              </button>
            </form>

            <div className="group-pick-list">
              {loading ? (
                <p style={{ color: "var(--text-muted)" }}>Loading groups…</p>
              ) : groups.length === 0 ? (
                <p style={{ color: "var(--text-muted)" }}>No groups yet — create one above.</p>
              ) : (
                groups.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    className="group-pick"
                    disabled={busy}
                    onClick={() => addTo(g.id)}
                  >
                    <span>{g.name}</span>
                    <span className="group-pick-count">{g.member_count} members</span>
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
