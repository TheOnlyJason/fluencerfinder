import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useGroups } from "../groupsContext";
import { listGroupMembers, removeMember, type GroupMember } from "../groups";
import { tierLabel } from "../api";
import EmailComposer, { type EmailRecipient } from "../components/EmailComposer";

export default function GroupsPage() {
  const { groups, loading, error: groupsError, create, rename, remove, adjustMemberCount } =
    useGroups();
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();

  const [members, setMembers] = useState<GroupMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const [composeTo, setComposeTo] = useState<EmailRecipient[] | null>(null);

  // The active group comes from the URL. Fall back to the first group.
  const activeId = groupId ?? groups[0]?.id ?? null;
  const activeGroup = groups.find((g) => g.id === activeId) ?? null;

  // Keep the URL in sync: if no group is selected but groups exist, redirect to the first.
  useEffect(() => {
    if (!groupId && groups.length > 0) {
      navigate(`/groups/${groups[0].id}`, { replace: true });
    }
  }, [groupId, groups, navigate]);

  useEffect(() => {
    if (!activeId) {
      setMembers([]);
      return;
    }
    setLoadingMembers(true);
    listGroupMembers(activeId)
      .then(setMembers)
      .catch((e) => setError(e.message || "Could not load members"))
      .finally(() => setLoadingMembers(false));
  }, [activeId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const g = await create(newName.trim());
      setNewName("");
      navigate(`/groups/${g.id}`);
    } catch (e: any) {
      setError(e.message || "Could not create group");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this group? This can't be undone.")) return;
    await remove(id);
    navigate("/groups", { replace: true });
  }

  async function handleRename(id: string, current: string) {
    const name = prompt("Rename group", current);
    if (!name || !name.trim() || name === current) return;
    await rename(id, name.trim());
  }

  async function handleRemoveMember(memberId: string) {
    await removeMember(memberId);
    setMembers((prev) => prev.filter((m) => m.id !== memberId));
    if (activeId) adjustMemberCount(activeId, -1);
  }

  function memberName(m: GroupMember): string {
    return m.display_name || m.handle || m.account_id;
  }

  function toRecipient(m: GroupMember): EmailRecipient | null {
    if (!m.contact_email || !m.contact_email.includes("@")) return null;
    return { id: m.id, name: memberName(m), email: m.contact_email };
  }

  const recipients = members
    .map(toRecipient)
    .filter((r): r is EmailRecipient => r !== null);

  return (
    <div>
      <section className="page-intro">
        <h1>Groups</h1>
        <p>Organize creators into groups. Select creators on the Database or Search pages to add them.</p>
      </section>

      {(error || groupsError) && <div className="error">{error || groupsError}</div>}

      <form className="create-group-row" onSubmit={handleCreate} style={{ marginBottom: "1.25rem" }}>
        <input
          className="search-input"
          placeholder="New group name…"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={!newName.trim()}>
          Create group
        </button>
      </form>

      <div className="groups-layout">
        <aside className="groups-list">
          {loading ? (
            <p style={{ color: "var(--text-muted)" }}>Loading…</p>
          ) : groups.length === 0 ? (
            <p style={{ color: "var(--text-muted)" }}>No groups yet.</p>
          ) : (
            groups.map((g) => (
              <button
                key={g.id}
                type="button"
                className={`group-row${g.id === activeId ? " is-active" : ""}`}
                onClick={() => navigate(`/groups/${g.id}`)}
              >
                <span className="group-row-name">{g.name}</span>
                <span className="group-pick-count">{g.member_count}</span>
              </button>
            ))
          )}
        </aside>

        <div className="groups-detail">
          {!activeGroup ? (
            <p style={{ color: "var(--text-muted)" }}>Select a group to view its members.</p>
          ) : (
            <>
              <div className="groups-detail-header">
                <h2>{activeGroup.name}</h2>
                <div className="filter-panel-actions">
                  {recipients.length > 0 && (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => setComposeTo(recipients)}
                    >
                      ✉ Email all ({recipients.length})
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleRename(activeGroup.id, activeGroup.name)}
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleDelete(activeGroup.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>

              {loadingMembers ? (
                <p style={{ color: "var(--text-muted)" }}>Loading members…</p>
              ) : members.length === 0 ? (
                <p style={{ color: "var(--text-muted)" }}>
                  No creators in this group yet. Add some from the Database or Search pages.
                </p>
              ) : (
                <div className="results-grid">
                  {members.map((m) => (
                    <div key={m.id} className="result-card">
                      <div className="result-header">
                        <div>
                          <div className="result-handle">
                            @{m.handle || m.account_id}
                            {m.profile_url && (
                              <a
                                href={m.profile_url}
                                target="_blank"
                                rel="noreferrer"
                                style={{ marginLeft: 8, fontSize: "0.85rem" }}
                              >
                                ↗
                              </a>
                            )}
                          </div>
                          {m.display_name && (
                            <div style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                              {m.display_name}
                            </div>
                          )}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                          {m.platform && <span className="platform-badge">{m.platform}</span>}
                          {m.tier && (
                            <span className="tier-badge" title={tierLabel(m.tier) ?? undefined}>
                              {`Tier ${m.tier}`}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="result-tags">
                        {m.niche && m.niche !== "unknown" && (
                          <span className="tag tag-niche">{m.niche}</span>
                        )}
                        {(() => {
                          const r = toRecipient(m);
                          return r ? (
                            <button
                              type="button"
                              className="tag tag-email"
                              onClick={() => setComposeTo([r])}
                            >
                              ✉ {m.contact_email}
                            </button>
                          ) : (
                            <span className="tag tag-muted">No email on file</span>
                          );
                        })()}
                        <button
                          type="button"
                          className="tag tag-remove"
                          onClick={() => handleRemoveMember(m.id)}
                        >
                          ✕ Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {composeTo && (
        <EmailComposer
          recipients={composeTo}
          groupName={activeGroup?.name}
          onClose={() => setComposeTo(null)}
        />
      )}
    </div>
  );
}
