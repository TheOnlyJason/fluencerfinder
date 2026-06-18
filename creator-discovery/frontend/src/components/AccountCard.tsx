import { Link } from "react-router-dom";
import { Account, followerTier, tierLabel, tierRange } from "../api";

function accountHandle(account: Account): string {
  return account.display_handle || account.handle;
}

function showChannelType(account: Account): boolean {
  if (!account.channel_type || account.channel_type === "mixed" || account.channel_type === "unknown") {
    return false;
  }
  if (account.niche && account.channel_type.toLowerCase() === account.niche.toLowerCase()) {
    return false;
  }
  return true;
}

function showCreatorLink(account: Account, creatorName?: string | null): boolean {
  if (!creatorName || !account.creator_id) return false;
  const name = account.display_name?.trim().toLowerCase();
  const creator = creatorName.trim().toLowerCase();
  return Boolean(creator && creator !== name);
}

function formatAddedAt(iso: string | undefined): string | null {
  if (!iso) return null;
  const added = new Date(iso);
  if (Number.isNaN(added.getTime())) return null;

  const diffMs = Date.now() - added.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "Added just now";
  if (diffMin < 60) return `Added ${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `Added ${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay === 1) return "Added yesterday";
  if (diffDay < 7) return `Added ${diffDay}d ago`;
  return `Added ${added.toLocaleDateString()}`;
}

export function isRecentlyAdded(iso: string | undefined, withinHours = 24): boolean {
  if (!iso) return false;
  const added = new Date(iso);
  if (Number.isNaN(added.getTime())) return false;
  return Date.now() - added.getTime() < withinHours * 60 * 60 * 1000;
}

export default function AccountCard({
  account,
  creatorName,
  showAddedAt = false,
  isNew = false,
}: {
  account: Account;
  creatorName?: string | null;
  showAddedAt?: boolean;
  isNew?: boolean;
}) {
  const addedLabel = showAddedAt ? formatAddedAt(account.created_at) : null;
  const tier = account.tier ?? followerTier(account.follower_count);
  const tierText = tierLabel(tier);
  // Follower counts in the catalog are unreliable, so we communicate audience
  // size via the tier band (a range) instead of a specific number.
  const range = tierRange(tier);
  const followerWord = account.platform === "YouTube" ? "subscribers" : "followers";

  return (
    <div className={`result-card${isNew ? " result-card-new" : ""}`}>
      <div className="result-header">
        <div>
          <div className="result-handle">
            @{accountHandle(account)}
            {account.profile_url && (
              <a
                href={account.profile_url}
                target="_blank"
                rel="noreferrer"
                style={{ marginLeft: 8, fontSize: "0.85rem" }}
              >
                ↗
              </a>
            )}
          </div>
          {account.display_name && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              {account.display_name}
            </div>
          )}
          {range && <div className="follower-count">{`${range} ${followerWord}`}</div>}
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
          <span className="platform-badge">{account.platform}</span>
          {tierText && <span className="tier-badge" title={tierText}>{`Tier ${tier}`}</span>}
        </div>
      </div>
      {addedLabel && <div className="added-at">{addedLabel}</div>}
      {account.bio_text && <p className="result-bio">{account.bio_text}</p>}
      <div className="result-tags">
        {account.niche && account.niche !== "unknown" && (
          <span className="tag tag-niche">{account.niche}</span>
        )}
        {showChannelType(account) && <span className="tag">{account.channel_type}</span>}
        {account.location_text && <span className="tag">📍 {account.location_text}</span>}
        {account.contact_email && (
          <a href={`mailto:${account.contact_email}`} className="tag tag-email">
            ✉ {account.contact_email}
          </a>
        )}
        {account.hobbies && <span className="tag">{account.hobbies}</span>}
        {showCreatorLink(account, creatorName) && (
          <Link
            to={`/creators/${account.creator_id}`}
            className="tag"
            style={{ color: "var(--accent)" }}
          >
            👤 {creatorName}
          </Link>
        )}
      </div>
    </div>
  );
}
