"""
Cleanup: deleted accounts + auto-delete bot messages.
"""

import logging
from telegram import User
from telegram.ext import Application, ContextTypes

from storage_json import all_groups, get_group, get_expired_bot_messages, remove_tracked_messages

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL = 6 * 3600
AUTOCLEAN_INTERVAL = 5 * 60


async def kick_if_deleted(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user: User) -> bool:
    gcfg = get_group(chat_id)
    if not gcfg.get("cleanup_enabled", True):
        return False
    if not user.first_name:
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            await context.bot.unban_chat_member(chat_id, user.id)
            logger.info(f"Kicked deleted {user.id} from {chat_id}")
            return True
        except Exception as exc:
            logger.warning(f"Kick deleted failed: {exc}")
    return False


async def _cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    groups = all_groups()
    for gid_str in groups:
        try:
            gid = int(gid_str)
            admins = await context.bot.get_chat_administrators(gid)
            logger.info(f"Cleanup heartbeat {gid}: {len(admins)} admins")
        except Exception as exc:
            logger.warning(f"Cleanup skip {gid_str}: {exc}")


async def _autoclean_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    groups = all_groups()
    for gid_str, gcfg in groups.items():
        minutes = gcfg.get("autoclean_minutes", 0)
        if minutes <= 0:
            continue
        gid = int(gid_str)
        expired = get_expired_bot_messages(gid, minutes)
        if not expired:
            continue
        deleted = []
        for msg_id in expired:
            try:
                await context.bot.delete_message(chat_id=gid, message_id=msg_id)
            except Exception:
                pass
            deleted.append(msg_id)
        if deleted:
            remove_tracked_messages(gid, deleted)
            logger.info(f"Autoclean {gid}: {len(deleted)} msgs")


def schedule_cleanup(app: Application) -> None:
    app.job_queue.run_repeating(_cleanup_job, interval=CLEANUP_INTERVAL, first=60, name="cleanup_deleted")
    app.job_queue.run_repeating(_autoclean_job, interval=AUTOCLEAN_INTERVAL, first=30, name="autoclean_bot_msgs")
    logger.info("🧹 Cleanup + Autoclean scheduled.")
