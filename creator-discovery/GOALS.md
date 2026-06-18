# Creator Discovery — Goals & Roadmap

The long-term vision is a single app where you can **find creators, organize them into
groups, reach out to them, and manage every reply in one dashboard** — starting with
email and expanding to social DMs where the platforms allow it.

---

## Current state (shipped)

- **Database** — browse the local catalog of creators with multi-select filters
  (tier, platform, niche, location), pagination, and a tier-band display.
- **Search** — web discovery of new creators (auth-gated).
- **Groups** — signed-in users create groups, add creators (selection mode), and
  manage members. Groups also appear nested under the Groups tab in the sidebar.
- **Auth** — Supabase email/password; Search and Groups are locked behind sign-in.
- **Email composer (mailto)** — compose a personalized message to a group. Each
  recipient gets their own separate email; `{name}` is swapped per person while the
  body stays the same.

---

## North-star goal

> Link my accounts (Google, and later social platforms), send outreach to creators,
> and **see their replies on the dashboard** — all without leaving the app.

---

## Outreach channels — feasibility

### Email (Gmail / ESP) — primary channel ✅ very feasible
- **Send:** Google OAuth → Gmail API (`gmail.send`) sends as you, threaded correctly.
- **Replies:** read scope + `threadId`/`In-Reply-To` headers to match replies to the
  outbound message; store in DB; render a conversation view.
- **Real-time:** Gmail watch + Google Pub/Sub push (or polling fallback).
- **Caveat:** Gmail send/read are "restricted" scopes — fine in testing mode (≤100
  users); public launch needs Google OAuth verification + CASA security assessment.
- **Alternative (often easier to scale):** transactional ESP (Resend / Postmark /
  SendGrid). Send from `you@yourdomain.com`, set
  `Reply-To: reply+<conversationId>@yourdomain.com`, parse inbound replies via webhook.
  Cleaner compliance and a unified inbox; emails come from your domain, not personal Gmail.

### Instagram DMs — partially feasible ⚠️
- Official Messaging API exists, but **only** for Business/Creator accounts linked to a
  Facebook Page, and you can only message someone **within 24h after they message you
  first**. Cold outreach via API is not allowed.

### X (Twitter) DMs — feasible but costly ⚠️
- DM API requires paid tiers (~$200/mo Basic, ~$5,000/mo Pro), with rate limits and
  recipient opt-in. Policies change frequently.

### TikTok DMs — not feasible ❌
- No public DM/messaging API for third parties.

### Unofficial automation — avoid ❌
- Headless-browser bots violate each platform's ToS and risk account bans.

**Takeaway:** email is the reliable, scalable channel. Treat social DMs as
"where allowed" — Instagram (reply-window) and X (paid) are the only realistic API
integrations; TikTok stays manual.

---

## Target architecture (channel-agnostic)

- **`conversations`** — creator + channel + status.
- **`messages`** — direction (outbound/inbound), body, external id, timestamps.
  One schema for *all* channels so the dashboard inbox is identical regardless of source.
- **Channel adapters** in the FastAPI backend: `GmailAdapter`, `EmailEspAdapter`,
  later `InstagramAdapter`, `XAdapter` — each implements `send()` and emits inbound messages.
- **Inbound ingestion:** Gmail Pub/Sub, ESP webhook, Meta webhook → all normalized into
  `messages`.
- **OAuth token vault:** encrypted per-user tokens (Supabase, RLS-protected).
- **Unified inbox UI:** reads `conversations`/`messages` regardless of channel.

> The current composer already isolates sending into a single `openAll()` step, so
> swapping mailto for `POST /api/outreach/send` later won't change the UI.

---

## Phased roadmap

- [x] **Phase 0 — mailto composer.** Personalized per-recipient drafts via the user's mail client.
- [ ] **Phase 1 — Reply dashboard (no paid services).**
  - `conversations` + `messages` schema in Supabase (RLS).
  - Backend `POST /api/outreach/send` endpoint + inbound webhook stub.
  - Unified inbox view in the dashboard.
  - Wire the existing composer to the backend.
- [ ] **Phase 2 — Real email send + reply sync.**
  - ESP integration (send from domain) **or** "Connect Gmail" OAuth (send-as-you).
  - Inbound parsing → threads appear in the inbox automatically.
- [ ] **Phase 3 — Social channels (where allowed).**
  - Instagram Messaging API (reply-window outreach).
  - X DMs (if budget allows).
  - TikTok: manual workflow / link-out only.
- [ ] **Phase 4 — CRM polish.**
  - Outreach status (sent / opened / replied / negotiating / booked).
  - Templates, follow-up reminders, per-creator history.

---

## Open decisions

- Personal Gmail OAuth vs. domain ESP as the default send path (or offer both).
- Whether to pursue Google restricted-scope verification (needed for public Gmail launch).
- Budget appetite for X DM API.
