# Creator Discovery MVP Spec

## Product goal
Build a modern creator discovery MVP inspired by RightFluencer, but updated for current tools and a different end goal. RightFluencer was built as an archived multi-platform influencer dashboard that analyzed posts, images, and videos across Instagram, Facebook, YouTube, Twitter, and Klout using Flask, MongoDB, Spark, Plotly, and web scrapers.[cite:123]

This MVP should keep the useful idea of a multi-platform creator discovery system, but modernize the backend, add TikTok, remove legacy scoring concepts, and focus on outputting creator handles and classifications directly instead of requiring the user to manually search for handles first.[cite:123][cite:48]

## MVP outcome
The MVP should take a search intent such as a niche, topic, hobby, location, or creator profile type and return a list of likely creator accounts from supported platforms. For each result, the system should output the handle itself, platform, basic public profile data, and LLM-generated categorization fields such as niche, hobbies, location, and channel type.[cite:48]

The system should also persist discovered creators and accounts into the database so the same creators do not need to be searched, resolved, and classified from scratch every time. Search should first check the local database for matching creators and only call external discovery providers when the local results are insufficient or stale.[cite:48]

The MVP is not a full outreach CRM. It should not include brand fit scoring, outreach stages, last-contacted fields, or follow-up tracking in the first version.[cite:48]

## Product direction
The product should do four things well:

1. Discover creators from multiple platforms.
2. Store discovered creators and accounts in a reusable local database.
3. Resolve likely duplicate identities across platforms or across multiple accounts owned by the same person.
4. Categorize each account using an LLM.
5. Return creator handles directly so the user does not need to manually search them first.[cite:48]

This is different from the original RightFluencer flow, which emphasized influencer recommendations and content analysis around products and categories. The new system is a creator search and classification engine.[cite:123]

## What to keep from RightFluencer
RightFluencer is still a good architectural reference even though the repository is archived and read-only.[cite:123] The useful ideas to keep are:

- Multi-platform mindset, instead of designing around only one network.[cite:123]
- Pipeline-oriented project structure with clear stages like collection, preprocessing, analysis, aggregation, and web app layers.[cite:123]
- Search and dashboard experience for browsing discovered creators.[cite:123]
- Content-aware creator analysis rather than relying only on follower metrics.[cite:123]

## What to remove from RightFluencer
The following RightFluencer features or assumptions should be removed from the MVP because they do not match the new goal or are outdated:

- MongoDB as the default storage layer.[cite:123]
- Spark-era batch processing for MVP use.[cite:123]
- Klout integration, which is no longer relevant.[cite:123]
- Watson Personality Insights dependency.[cite:123]
- Product/category influencer score logic.[cite:123]
- Legacy scraping assumptions tied to old platform behavior.[cite:123][cite:52][cite:53]
- The requirement that the user already knows the handle before the system becomes useful.[cite:48]

## Supported platforms
The initial platform target should be:

- Instagram
- TikTok
- X
- YouTube (optional in MVP, but structure should allow it)

TikTok should be added as a first-class platform in the new architecture because the product goal is creator discovery across modern short-form ecosystems, not just older influencer sources.[cite:48]

## Core user flow
The user enters a discovery query such as:
- "Los Angeles fitness creators"
- "anime gaming creators in California"
- "matcha creators in SoCal"
- "small fashion creators in Tokyo"

The system should then:
1. Retrieve candidate creator accounts from supported ingestion sources.
2. Normalize handles and profile URLs.
3. Check whether the account or creator identity already exists.
4. Run identity resolution to link possible duplicate accounts.
5. Save newly discovered creators and accounts into the database.
6. Run LLM categorization only for new or materially changed records.
7. Return a structured results list including the handle itself.[cite:48]

## Creator and account model
The data model should separate the person from the account.

### Creator table
Represents a likely real person or entity across platforms and acts as the long-lived reusable record for future searches.

Recommended fields:
- `creator_id`
- `canonical_name`
- `primary_language`
- `home_region`
- `overall_topics`
- `identity_confidence`
- `created_at`
- `updated_at`

### Account table
Represents one platform-specific account or channel.

Recommended fields:
- `account_id`
- `creator_id`
- `platform`
- `handle`
- `display_name`
- `profile_url`
- `bio_text`
- `channel_type` (personal, fitness, gaming, beauty, food, etc.)
- `niche`
- `secondary_niches`
- `hobbies`
- `location_text`
- `language`
- `external_links`
- `classification_confidence`
- `is_active`
- `last_seen_at`

This model supports the case where one person has separate personal, gaming, and fitness channels while still belonging to the same underlying creator identity. It also supports caching discovered results so future searches can reuse prior creator and account records instead of rediscovering them from scratch.[cite:48]

## Identity resolution logic
The system should not reprocess creators it has already identified. It also should not treat slightly different handles on different platforms as automatically unrelated. The local database should be the first place checked before any new discovery call is made.[cite:48]

Identity resolution should use a blend of deterministic and probabilistic signals:
- exact handle match
- normalized handle similarity
- display-name similarity
- bio similarity
- shared location hints
- shared link-in-bio domains
- shared email or website
- LLM judgment on whether two accounts likely belong to the same creator

The output should be a confidence score plus a recommended action:
- attach to existing creator
- create new creator
- send to review queue

## LLM responsibilities
The LLM should be used as a categorization and identity-assistance layer, not as the entire backend. Its jobs are:

- infer niche from raw bio text and profile metadata
- infer hobbies and interests
- infer likely location when publicly stated or strongly implied
- classify channel type such as personal, fitness, gaming, fashion, beauty, food, or mixed
- help determine whether two accounts likely belong to the same creator
- avoid re-running categorization if the account has already been processed and the content has not materially changed[cite:48]

The LLM should return structured JSON so the rest of the app can remain deterministic.

## Discovery layer
The new system should aim to output handles directly. That means the system needs a discovery layer that can accept a niche or search intent and return candidate creators rather than only enriching already-known handles.[cite:48]

That discovery layer should be database-first. The app should search existing stored creators and accounts before calling outside providers, then persist any newly found accounts back into the database for reuse in later searches.[cite:48]

For the MVP, discovery should be abstracted behind provider interfaces so the backend can evolve without rewriting the entire app. The system should support multiple provider types:
- compliant APIs where available
- creator discovery vendors
- imported CSVs
- manually saved public profile URLs
- modular adapters for future platform-specific integrations

Because Instagram and Meta restrict unauthorized automated data collection, the architecture should avoid depending on brittle unofficial scraping as the only way the product works.[cite:52][cite:53][cite:54]

## Recommended modern stack
A modern MVP stack should replace the legacy RightFluencer stack with:

- **Backend**: Python + FastAPI
- **Database**: PostgreSQL for production, SQLite for local MVP
- **ORM**: SQLModel or SQLAlchemy
- **Task queue**: Celery, Dramatiq, or a lightweight async job system
- **LLM layer**: OpenAI-compatible structured output calls
- **Search**: Postgres full-text search first, optional Typesense/Meilisearch later
- **Frontend**: Next.js or a minimal React client; alternatively keep a simple FastAPI server-rendered MVP
- **Data processing**: pandas for import/export and small batch transforms
- **Caching**: Redis if needed, otherwise keep MVP simple

This stack is easier to maintain than the archived Flask + MongoDB + Spark + Watson stack used by RightFluencer.[cite:123]

## MVP features
The first version should include only the essential features.

### Required features
- Search box for niche/topic/location queries
- Database-first creator retrieval before new provider lookups
- Multi-platform creator result list
- Direct output of handle and profile URL
- Persistent storage of discovered creators and accounts
- Account deduplication and creator grouping
- LLM categorization for niche, hobbies, location, and channel type
- Basic filters by platform, niche, and location
- Creator detail page showing linked accounts
- Import/export via CSV or JSON

### Deferred features
- Outreach workflow
- Brand fit scoring
- Messaging or campaign management
- Advanced analytics dashboards
- Image/video deep analysis
- Personality scoring
- Engagement prediction
- Team review workflows

## API design
Suggested MVP endpoints:

- `POST /search` — accepts discovery query, checks local database first, and returns candidate creators/accounts
- `POST /accounts/ingest` — ingest account records from provider or CSV and save them
- `POST /accounts/classify` — classify a new or changed account with LLM
- `POST /identity/resolve` — compare account against known creators
- `GET /creators` — list creators
- `GET /creators/{id}` — show creator with linked accounts
- `GET /accounts` — list accounts with filters
- `POST /imports/csv` — upload CSV input
- `GET /exports/csv` — export categorized results

## Suggested folder structure
```text
creator-discovery/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
      discovery/
      identity/
      classification/
      providers/
    workers/
    prompts/
    utils/
  tests/
  scripts/
  docs/
  data/
  frontend/
  docker-compose.yml
  README.md
```

## LLM prompt requirements
Cursor should build prompts that return structured output with fields such as:
- `channel_type`
- `primary_niche`
- `secondary_niches`
- `hobbies`
- `location`
- `language`
- `same_creator_as`
- `identity_confidence`
- `classification_confidence`

The prompts should emphasize that uncertainty is allowed. The model should not fabricate precise facts when a profile only provides weak clues.[cite:48]

## MVP constraints
The system should be optimized for creator discovery and categorization only. It should not attempt to become a full sales or outreach tool in version one.[cite:48]

The system should also be built so repeated classification is avoided. If an account has already been processed and no meaningful profile changes are detected, the previous result should be reused instead of calling the LLM again.[cite:48]

## Build order
Cursor should implement the MVP in this order:

1. Project setup with FastAPI, database, and models.
2. Creator/account schema and migrations.
3. CSV/manual ingestion flow.
4. Handle normalization utilities.
5. Identity resolution service.
6. LLM classification service with structured outputs.
7. Search endpoint and account results list.
8. Creator detail view showing grouped accounts.
9. Basic filters and CSV export.
10. Provider abstraction for future TikTok, Instagram, and X discovery connectors.
11. Database-first search reuse and stale-result refresh policy.

## Definition of success
The MVP is successful if a user can enter a creator search intent and receive back a list of creator accounts with handles, linked identities, and useful classifications without having to manually search for each handle one by one.[cite:48]

It is also successful if those discovered creators are stored in the database and reused on later searches so the system becomes faster, cheaper, and smarter over time instead of repeating the same discovery work.[cite:48]

It is also successful if the system reuses prior classifications, groups related accounts under one creator where confidence is high, and stays lightweight enough to be built quickly as a modern replacement for the old RightFluencer architecture.[cite:123][cite:48]
