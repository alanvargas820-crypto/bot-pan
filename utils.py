"""
Small helpers shared across modules.
"""

from telegram import Chat


def message_link(chat: Chat, message_id: int) -> str:
    if chat.username:
        return f"https://t.me/{chat.username}/{message_id}"
    cid = str(chat.id).replace("-100", "")
    return f"https://t.me/c/{cid}/{message_id}"


def truncate(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
