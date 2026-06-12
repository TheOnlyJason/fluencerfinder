from enum import Enum


class Platform(str, Enum):
    INSTAGRAM = "Instagram"
    TIKTOK = "TikTok"
    X = "X"
    YOUTUBE = "YouTube"


class IdentityAction(str, Enum):
    ATTACH = "attach"
    CREATE = "create"
    REVIEW = "review"
