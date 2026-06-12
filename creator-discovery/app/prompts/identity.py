IDENTITY_SYSTEM_PROMPT = """You help determine if two social media accounts belong to the same creator.

Rules:
- Base judgments ONLY on provided profile data.
- Do NOT assume facts not present in the profiles.
- Return low identity_confidence when evidence is weak.
- same_creator_as should be the creator_id of the best match, or null if no match."""

IDENTITY_USER_TEMPLATE = """Does this new account likely belong to an existing creator?

NEW ACCOUNT:
Platform: {platform}
Handle: {handle}
Display name: {display_name}
Bio: {bio_text}
Location: {location_text}
External links: {external_links}

EXISTING CREATORS (candidates):
{candidates_json}

Return JSON with: same_creator_as (creator_id or null), identity_confidence (0-1), reasoning (brief)."""
