from typing import List, Optional

from app.models.enums import Platform
from app.services.providers.base import DiscoveredAccount, DiscoveryProvider, DiscoveryResult

MOCK_CATALOG = [
    {
        "platform": Platform.INSTAGRAM,
        "handle": "la_fitness_jess",
        "display_name": "Jess | LA Fitness",
        "bio_text": "Certified personal trainer 💪 Los Angeles | Workouts & nutrition tips",
        "location_text": "Los Angeles, CA",
        "niche_terms": ["fitness", "los angeles", "trainer", "workout"],
    },
    {
        "platform": Platform.TIKTOK,
        "handle": "lafitjess",
        "display_name": "Jess LA Fit",
        "bio_text": "LA fitness creator | gym vlogs & meal prep",
        "location_text": "Los Angeles, CA",
        "niche_terms": ["fitness", "los angeles", "gym"],
    },
    {
        "platform": Platform.INSTAGRAM,
        "handle": "socal_yoga_mia",
        "display_name": "Mia | SoCal Yoga",
        "bio_text": "Yoga instructor 🧘‍♀️ Southern California | mindfulness & wellness",
        "location_text": "Southern California",
        "niche_terms": ["yoga", "fitness", "socal", "wellness"],
    },
    {
        "platform": Platform.X,
        "handle": "tokyo_fashion_aya",
        "display_name": "Aya | Tokyo Fashion",
        "bio_text": "Small fashion creator in Tokyo 👗 street style & thrift finds",
        "location_text": "Tokyo, Japan",
        "niche_terms": ["fashion", "tokyo", "style"],
    },
    {
        "platform": Platform.TIKTOK,
        "handle": "anime_gamer_kai",
        "display_name": "Kai | Anime Gaming",
        "bio_text": "Anime & gaming content 🎮 California based | reviews & streams",
        "location_text": "California",
        "niche_terms": ["anime", "gaming", "california", "gamer"],
    },
    {
        "platform": Platform.INSTAGRAM,
        "handle": "matcha_maven_socal",
        "display_name": "Matcha Maven",
        "bio_text": "Matcha obsessed ☕️ SoCal cafe reviews & latte art",
        "location_text": "SoCal",
        "niche_terms": ["matcha", "food", "socal", "cafe"],
    },
    {
        "platform": Platform.YOUTUBE,
        "handle": "LAStrengthCoach",
        "display_name": "LA Strength Coach",
        "bio_text": "Strength training tutorials for beginners | Los Angeles gym tours",
        "location_text": "Los Angeles, CA",
        "niche_terms": ["fitness", "strength", "los angeles", "gym"],
    },
    {
        "platform": Platform.TIKTOK,
        "handle": "beauty_by_nina_la",
        "display_name": "Nina | LA Beauty",
        "bio_text": "LA beauty & skincare routines ✨ honest reviews",
        "location_text": "Los Angeles, CA",
        "niche_terms": ["beauty", "los angeles", "skincare"],
    },
]


class MockDiscoveryProvider(DiscoveryProvider):
    name = "mock"

    async def discover(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        limit: int = 20,
    ) -> DiscoveryResult:
        terms = query.lower().split()
        results: List[DiscoveredAccount] = []

        for entry in MOCK_CATALOG:
            if platforms and entry["platform"] not in platforms:
                continue
            searchable = " ".join([
                entry["handle"],
                entry["display_name"],
                entry["bio_text"],
                entry["location_text"],
                " ".join(entry["niche_terms"]),
            ]).lower()
            score = sum(1 for t in terms if t in searchable)
            if score > 0:
                from app.utils.handles import build_profile_url
                results.append(DiscoveredAccount(
                    platform=entry["platform"],
                    handle=entry["handle"],
                    display_name=entry["display_name"],
                    profile_url=build_profile_url(entry["platform"], entry["handle"]),
                    bio_text=entry["bio_text"],
                    location_text=entry["location_text"],
                    source=self.name,
                ))

        # Sort by relevance (simple term count) and limit
        def relevance(acc: DiscoveredAccount) -> int:
            text = f"{acc.handle} {acc.display_name} {acc.bio_text} {acc.location_text}".lower()
            return sum(1 for t in terms if t in text)

        results.sort(key=relevance, reverse=True)
        return DiscoveryResult(
            accounts=results[:limit],
            provider_name=self.name,
            query=query,
        )
