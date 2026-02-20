"""
Anti-spam engine: flood, repeated messages, suspicious links.
"""

import datetime
import logging
import re
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from telegram import Message, ChatPermissions
from telegram.ext import ContextTypes

from storage_json import get_group
from logs_bridge import log_antispam

logger = logging.getLogger(__name__)

_user_messages: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
_user_last_text: Dict[int, Dict[int, Tuple[str, int]]] = defaultdict(dict)

_LINK_PATTERN = re.compile(
    r"(https?://|t\.me/|bit\.ly/|goo\.gl/|tinyurl\.com/|www\.)", re.IGNORECASE
)


def _cleanup_ts(timestamps: List[float], window: int) -> List[float]:
    now = time.time()
    return [t for t in timestamps if now - t < window]


async def check_spam(message: Message, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not message.from_user:
        return False
    chat_id = message.chat.id
    user_id = message.from_user.id
    gcfg = get_group(chat_id)
    if not gcfg.get("antispam_enabled", False):
        return False

    flood_limit = gcfg.get("antispam_flood_limit", 5)
    flood_window = gcfg.get("antispam_flood_window", 10)
    mute_seconds = gcfg.get("antispam_mute_seconds", 300)
    block_links = gcfg.get("antispam_block_links", True)
    text = message.text or message.caption or ""

    if block_links and _LINK_PATTERN.search(text):
        try:
            await message.delete()
        except Exception:
            pass
        await log_antispam(context, message.from_user, message.chat, "Link sospechoso")
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"🚨 <b>Anti-Spam:</b> Link bloqueado de <code>{user_id}</code>.", parse_mode="HTML")
        except Exception:
            pass
        return True

    if text:
        prev = _user_last_text[chat_id].get(user_id)
        repeat_count = (prev[1] + 1) if (prev and prev[0] == text) else 1
        _user_last_text[chat_id][user_id] = (text, repeat_count)
        if repeat_count >= 3:
            try:
                await message.delete()
            except Exception:
                pass
            await log_antispam(context, message.from_user, message.chat, f"Repetido x{repeat_count}")
            if repeat_count >= 4:
                await _mute_user(context, chat_id, user_id, mute_seconds)
            return True

    now = time.time()
    _user_messages[chat_id][user_id].append(now)
    _user_messages[chat_id][user_id] = _cleanup_ts(_user_messages[chat_id][user_id], flood_window)
    if len(_user_messages[chat_id][user_id]) > flood_limit:
        try:
            await message.delete()
        except Exception:
            pass
        await log_antispam(context, message.from_user, message.chat, "Flood")
        await _mute_user(context, chat_id, user_id, mute_seconds)
        _user_messages[chat_id][user_id].clear()
        return True
    return False


async def _mute_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, seconds: int) -> None:
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    try:
        await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
        await context.bot.send_message(chat_id=chat_id, text=f"🚨 <b>Anti-Spam:</b> <code>{user_id}</code> silenciado {seconds // 60}min.", parse_mode="HTML")
    except Exception as exc:
        logger.warning(f"Mute failed {user_id}: {exc}")
