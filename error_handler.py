"""
Global error handler — keeps the bot alive.
"""

import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling update:")
    logger.error("".join(traceback.format_exception(None, context.error, context.error.__traceback__)))
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Error interno.")
        except Exception:
            pass
