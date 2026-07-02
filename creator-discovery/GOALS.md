# Creator Discovery — Goals & Roadmap

The long-term vision is a single app where you can **find creators, organize them into
groups, reach out to them, and manage every reply in one dashboard** — starting with
email and expanding to social DMs where the platforms allow it.

---

## Current state (shipped)

- **Database** — browse the local catalog of creators with multi-select filters
  (tier, platform, niche, location), pagination, and a tier-band display.
- **Search** — auth-gated creator search with **hybrid semantic + keyword matching**
  and **LLM natural-language query parsing** (see "Search quality" below). Optional
  opt-in web discovery for net-new creators.
- **Groups** — signed-in users create groups, add creators (selection mode), and
  manage members. Groups appear nested under the Groups tab in the sidebar.
- **Auth** — Supabase email/password; Search and Groups are locked behind sign-in.
- **Email composer** — pops out a composer for a group: editable recipients (each
  gets their own separate email), From, Subject, and a body with a `{name}` token
  that personalizes per recipient. "Email all" opens one draft per recipient via the
  mail client (mailto), plus per-member email links. Send step is isolated for an
  easy swap to a real send API later.

---

## Search quality

Improving how creators are found, ranked, and discovered.

- [x] **#1 Semantic (vector) search.** Every creator profile is embedded with OpenAI
  `text-embedding-3-small` (1536-dim) and stored in a `pgvector` column (HNSW cosine
  index) in Supabase. All ~2.2k creators are backfilled
  (`scripts/embed_accounts.py`); new discoveries are embedded on ingest.
- [x] **#2 Hybrid search.** Keyword/FTS results (precision) are fused with vector
  results (semantic recall) via Reciprocal Rank Fusion. Hard filters (platform,
  location, follower range) still apply; the topic keyword filter is relaxed for
  semantic-only hits. Falls back to keyword-only when embeddings/pgvector aren't
  available (e.g. SQLite).
- [x] **#3 LLM query parsing.** Free text → structured filters (topic, location,
  follower range, platforms) + a cleaned semantic query. Understands follower
  shorthand (`10k`/`1m`), size words (nano/micro/mid/macro/mega), tier 1–5, and
  platform hints ("youtubers" → YouTube). Regex parser remains the fallback.
- [ ] **#4 Real influencer-data provider.** For accurate follower/engagement/audience
  metrics and net-new discovery at scale — e.g. Modash, HypeAuditor, Phyllo, or the
  official YouTube/TikTok APIs. Solves the unreliable scraped-follower-count problem.
  (Paid; ties into the data-provider open decision below.)
- [ ] **#5 Location & proximity search.** Find creators *physically near a place* (a
  store/venue) for in-person/promotional collabs — see "Location & proximity" below.
- [ ] **#6 Multimodal (video) matching.** Match brands to creators by their actual
  video content, not just text — see "Multimodal phase" below.

---

## Location & proximity (in-person / promotional outreach)

A core use case: we want to invite creators to **come to a physical store and make
promotional content**, so they must be **geographically close** to that location.
Today `location_text` is free text — good for "in Los Angeles" string matching, but it
can't answer "creators within 25 miles of this store."

**Plan:**
- **Geocode creators** — resolve each creator's `location_text` (and bio hints) to
  `latitude`/`longitude` once, via a geocoder (Nominatim/OpenStreetMap free tier, a
  bundled city→coords dataset, or Google Geocoding if budget allows). Store coords on
  the account; backfill existing rows with a script (like `embed_accounts.py`).
- **Proximity query** — add a radius filter: given a store address (geocoded to a
  point) and a radius (e.g. 25 mi), return creators within it, sorted by distance.
  Implement in Postgres with the `earthdistance`/`cube` extensions (`earth_distance` +
  GiST index) or **PostGIS** (`geography` + `ST_DWithin`) on Supabase.
- **Query understanding** — extend the LLM parser (#3) to extract "near {place} within
  {N} miles" into `{ near: point, radius_mi }`.
- **UI** — a location + radius control on Search/Database, and a distance badge on
  cards ("12 mi away").

**Caveats:** many creators don't list a precise location (city-level at best), so
proximity is approximate; missing-location creators are excluded from radius results.
Accurate per-creator location is also something a data provider (#4) can supply.

---

## Architecture influences

Reference projects guiding the design:

- **Infrastructure — pgvector** ([neondatabase/pgvector](https://github.com/neondatabase/pgvector)).
  Confirms our approach: keep **all vectors in Postgres** (Supabase) with HNSW + cosine,
  rather than adding a separate vector DB. One database, one backup story, RLS-friendly;
  we can add more embedding columns/tables (text now, video later) without new infra.
- **Product architecture — rightfluencer**
  ([manojkarthick/rightfluencer](https://github.com/manojkarthick/rightfluencer)).
  Multi-platform data pipeline (collect → aggregate → clean → analyze → serve), an
  **influencer score** per product/category, and YouTube-caption topic analysis for
  expertise. We already borrowed the pipeline mindset; next is a formal enrichment
  pipeline + a per-creator/per-category relevance score.
- **Semantic / multimodal — mrnkim + Twelve Labs**
  ([mrnkim/creator-discovery](https://github.com/mrnkim/creator-discovery)).
  Embeds **actual video content** (Twelve Labs Embed API) for creator↔brand matching,
  semantic search across brand/creator indices, and brand-mention detection. Our text
  embeddings are the v1 of this; the multimodal phase below is the upgrade.

### Multimodal phase (later)
Add a **video-content embedding layer**: ingest a creator's top videos, embed them
(Twelve Labs), store those vectors in **pgvector alongside the text vectors**, and offer
"match this brand/product to creators by content" + brand-mention detection. Highest
effort/cost (Twelve Labs is paid + needs a video-ingestion pipeline), highest
differentiation. Decision: stay on **pgvector** rather than Pinecone unless scale forces
otherwise.

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

(Search-quality items #4–#6 — data provider, location/proximity, multimodal — are
tracked in the "Search quality" section above and run in parallel with the outreach
phases.)

---

## Open decisions

- Personal Gmail OAuth vs. domain ESP as the default send path (or offer both).
- Whether to pursue Google restricted-scope verification (needed for public Gmail launch).
- Budget appetite for X DM API.
- Whether to add a paid influencer-data provider (#4) for accurate metrics + discovery.
- Geocoding source for location/proximity (#5): free Nominatim / bundled city dataset
  vs. paid Google Geocoding; and `earthdistance` vs. PostGIS for the radius query.
- Whether/when to invest in Twelve Labs multimodal video matching (#6) — paid + needs
  a video-ingestion pipeline. Stay on pgvector (not Pinecone) for the vector store.
- Hosting: production currently proxies to a **local API via ngrok** (depends on the
  dev machine). Move the backend to an always-on host (Render) to decouple it.
