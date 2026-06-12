import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Creator, formatFollowerCount, getCreator } from "../api";

export default function CreatorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [creator, setCreator] = useState<Creator | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getCreator(id)
      .then(setCreator)
      .catch(() => setError("Creator not found"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading">Loading...</div>;
  if (error || !creator) return <div className="error">{error || "Not found"}</div>;

  return (
    <div className="creator-detail">
      <Link to="/" className="back-link">← Back to search</Link>
      <h1>{creator.canonical_name}</h1>
      <div className="creator-meta">
        {creator.home_region && <span>📍 {creator.home_region} · </span>}
        {creator.overall_topics && <span>{creator.overall_topics} · </span>}
        Identity confidence: {(creator.identity_confidence * 100).toFixed(0)}%
      </div>

      <section className="accounts-list">
        <h2>Linked Accounts ({creator.accounts.length})</h2>
        <div className="results-grid">
          {creator.accounts.map((acc) => (
            <div key={acc.account_id} className="result-card">
              <div className="result-header">
                <div>
                  <div className="result-handle">
                    @{acc.display_handle || acc.handle}
                    {acc.profile_url && (
                      <a href={acc.profile_url} target="_blank" rel="noreferrer" style={{ marginLeft: 8, fontSize: "0.85rem" }}>
                        ↗
                      </a>
                    )}
                  </div>
                  {acc.display_name && (
                    <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>{acc.display_name}</div>
                  )}
                  {formatFollowerCount(acc.follower_count, acc.platform) && (
                    <div className="follower-count">
                      {formatFollowerCount(acc.follower_count, acc.platform)}
                    </div>
                  )}
                </div>
                <span className="platform-badge">{acc.platform}</span>
              </div>
              {acc.bio_text && <p className="result-bio">{acc.bio_text}</p>}
              <div className="result-tags">
                {acc.niche && acc.niche !== "unknown" && (
                  <span className="tag tag-niche">{acc.niche}</span>
                )}
                {acc.channel_type &&
                  acc.channel_type !== "mixed" &&
                  acc.channel_type !== "unknown" &&
                  (!acc.niche || acc.channel_type.toLowerCase() !== acc.niche.toLowerCase()) && (
                  <span className="tag">{acc.channel_type}</span>
                )}
                {acc.location_text && (
                  <span className="tag">📍 {acc.location_text}</span>
                )}
                {acc.contact_email && (
                  <a href={`mailto:${acc.contact_email}`} className="tag tag-email">
                    ✉ {acc.contact_email}
                  </a>
                )}
                {acc.classification_confidence != null && (
                  <span className="tag">{(acc.classification_confidence * 100).toFixed(0)}% conf.</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
