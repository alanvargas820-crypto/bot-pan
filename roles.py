"""
Roles & permissions: OWNER > ADMIN > MOD
"""

import logging
from telegram.ext import ContextTypes

from storage_json import get_role, set_role, ROLE_OWNER, ROLE_ADMIN, ROLE_MOD
from config import Config

logger = logging.getLogger(__name__)

ROLE_HIERARCHY = {ROLE_OWNER: 3, ROLE_ADMIN: 2, ROLE_MOD: 1}


def has_permission(group_id: int, user_id: int, min_role: str = ROLE_MOD) -> bool:
    if user_id == Config.OWNER_ID:
        return True
    role = get_role(group_id, user_id)
    if not role:
        return False
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(min_role, 0)


async def sync_admins_from_telegram(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> int:
    count = 0
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for member in admins:
            uid = member.user.id
            if member.user.is_bot:
                continue
            existing = get_role(chat_id, uid)
            if not existing:
                if member.status == "creator":
                    set_role(chat_id, uid, ROLE_OWNER)
                else:
                    set_role(chat_id, uid, ROLE_ADMIN)
                count += 1
    except Exception as exc:
        logger.warning(f"Admin sync failed {chat_id}: {exc}")
    return count
