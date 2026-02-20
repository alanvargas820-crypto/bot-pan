"""
Centralised configuration — reads environment variables.
"""

import os


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    LOG_GROUP_ID: int = int(os.getenv("LOG_GROUP_ID", "0"))
    DEFAULT_BOT_NAME: str = os.getenv("DEFAULT_BOT_NAME", "🤖 AnonBot")
    ANTIFAKE_DEFAULT_DAYS: int = int(os.getenv("ANTIFAKE_DEFAULT_DAYS", "7"))
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    PANEL_IMAGE_URL: str = (
        "https://encrypted-tbn0.gstatic.com/images?"
        "q=tbn:ANd9GcQxLIKNEYBTIL7B-s5da5EdOa1P6U16flhSKpKw9nk1FEfpDMPkvGcSzbA&s=10"
    )
    SPAM_FLOOD_LIMIT: int = int(os.getenv("SPAM_FLOOD_LIMIT", "5"))
    SPAM_FLOOD_WINDOW: int = int(os.getenv("SPAM_FLOOD_WINDOW", "10"))
    SPAM_MUTE_SECONDS: int = int(os.getenv("SPAM_MUTE_SECONDS", "300"))
