import re
from typing import Optional

_EMAIL_PATTERN = re.compile(
    r"\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b"
)

_BLOCKED_EMAIL_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "example.com",
    "email.com",
    "domain.com",
    "sentry.io",
}


def parse_email(*texts: Optional[str]) -> Optional[str]:
    """Extract the first plausible public contact email from text."""
    for text in texts:
        if not text:
            continue
        for match in _EMAIL_PATTERN.finditer(text):
            email = match.group(1).lower().strip()
            domain = email.split("@")[-1]
            if domain in _BLOCKED_EMAIL_DOMAINS:
                continue
            if email.startswith("noreply") or email.startswith("no-reply"):
                continue
            return email
    return None


def parse_location(*texts: Optional[str]) -> Optional[str]:
    """Extract location hints from bios and search snippets."""
    from app.utils.location import infer_location

    return infer_location(*texts)
