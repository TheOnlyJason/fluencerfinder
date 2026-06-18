import { useMemo, useState } from "react";
import { useAuth } from "../auth";

export interface EmailRecipient {
  id: string;
  name: string;
  email: string;
}

/** Replace {name} (and {email}) tokens with this recipient's details. */
function personalize(template: string, r: EmailRecipient): string {
  return template
    .replace(/\{name\}/gi, r.name || "there")
    .replace(/\{email\}/gi, r.email);
}

function buildMailto(to: string, subject: string, body: string, from?: string): string {
  const params: string[] = [];
  if (subject) params.push(`subject=${encodeURIComponent(subject)}`);
  if (body) params.push(`body=${encodeURIComponent(body)}`);
  // mailto can't set the sender, but Reply-To is honored by most clients so a
  // recipient replies to the address you typed in "From".
  if (from) params.push(`reply-to=${encodeURIComponent(from)}`);
  return `mailto:${encodeURIComponent(to)}?${params.join("&")}`;
}

function openDraft(url: string) {
  const a = document.createElement("a");
  a.href = url;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export default function EmailComposer({
  recipients,
  groupName,
  onClose,
}: {
  recipients: EmailRecipient[];
  groupName?: string;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const [from, setFrom] = useState(user?.email ?? "");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("Hi {name},\n\n\n\nBest,\n");
  const [excluded, setExcluded] = useState<Set<string>>(new Set());

  const active = useMemo(
    () => recipients.filter((r) => !excluded.has(r.id)),
    [recipients, excluded]
  );

  const preview = active[0] ?? recipients[0] ?? null;

  function toggle(id: string) {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function openAll() {
    // Each draft is addressed to a single person so the recipient never sees the
    // others. The body is the same template, with {name} swapped per person.
    active.forEach((r, i) => {
      const url = buildMailto(r.email, personalize(subject, r), personalize(body, r), from);
      // Small stagger helps the OS mail client open multiple drafts reliably.
      setTimeout(() => openDraft(url), i * 350);
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Compose email{groupName ? ` — ${groupName}` : ""}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="modal-body email-composer">
          <div className="email-field">
            <label>To ({active.length})</label>
            <div className="email-recipients">
              {recipients.length === 0 ? (
                <span style={{ color: "var(--text-muted)" }}>No recipients with an email.</span>
              ) : (
                recipients.map((r) => {
                  const off = excluded.has(r.id);
                  return (
                    <button
                      key={r.id}
                      type="button"
                      className={`email-chip${off ? " is-off" : ""}`}
                      onClick={() => toggle(r.id)}
                      title={off ? "Click to include" : "Click to exclude"}
                    >
                      <span className="email-chip-name">{r.name}</span>
                      <span className="email-chip-email">{r.email}</span>
                    </button>
                  );
                })
              )}
            </div>
            <p className="email-hint">
              Each person gets their own separate email — they won't see the others.
            </p>
          </div>

          <div className="email-field">
            <label htmlFor="email-from">From</label>
            <input
              id="email-from"
              className="search-input"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              placeholder="you@example.com"
            />
          </div>

          <div className="email-field">
            <label htmlFor="email-subject">Subject</label>
            <input
              id="email-subject"
              className="search-input"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Collaboration opportunity"
            />
          </div>

          <div className="email-field">
            <label htmlFor="email-body">Message</label>
            <textarea
              id="email-body"
              className="search-input email-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
            />
            <p className="email-hint">
              Use <code>{"{name}"}</code> to personalize — it becomes each recipient's name. The
              rest of the message stays the same for everyone.
            </p>
          </div>

          {preview && (
            <div className="email-preview">
              <div className="email-preview-label">Preview for {preview.name}</div>
              <div className="email-preview-subject">{personalize(subject, preview) || "(no subject)"}</div>
              <pre className="email-preview-body">{personalize(body, preview)}</pre>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={openAll}
            disabled={active.length === 0}
          >
            Open {active.length} draft{active.length === 1 ? "" : "s"}
          </button>
        </div>
      </div>
    </div>
  );
}
