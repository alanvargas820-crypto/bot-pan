#!/usr/bin/env python3
"""Telegram SaaS Bot - Multi-Group Anonymous Bot. FLAT version."""
import sys, logging
from telegram import Update, ChatPermissions
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes)
from telegram.constants import ChatMemberStatus
from config import Config
from storage_json import get_group, register_group
from ui_panel import send_panel, handle_callback, handle_text_input, get_user_state, try_link_group
from anon_mode import handle_anonymous
from antispam import check_spam
from antifake import is_suspicious
from cleanup_deleted import kick_if_deleted, schedule_cleanup
from logs_bridge import log_join, log_leave, log_antifake
from roles import sync_admins_from_telegram
from error_handler import global_error_handler
logging.basicConfig(format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext._updater").setLevel(logging.WARNING)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private": return
    await send_panel(update, context)

async def private_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private": return
    if get_user_state(update.effective_user.id): await handle_text_input(update, context)

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.my_chat_member
    if not result: return
    old_s = result.old_chat_member.status; new_s = result.new_chat_member.status; chat = update.effective_chat
    if old_s in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED) and new_s in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
        title = chat.title or "Grupo"
        logger.info(f"Bot added to: {title} ({chat.id})")
        register_group(chat.id, title)
        await sync_admins_from_telegram(context, chat.id)
        try: await context.bot.send_message(chat_id=chat.id, text=f"Bot activado en <b>{title}</b>\nID: <code>{chat.id}</code>\nModo anonimo: ON\nUsa /start en privado para el panel.", parse_mode="HTML")
        except Exception as exc: logger.warning(f"Welcome failed: {exc}")
    elif old_s == ChatMemberStatus.MEMBER and new_s == ChatMemberStatus.ADMINISTRATOR:
        register_group(chat.id, chat.title or "Grupo")
    elif new_s in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
        logger.info(f"Bot removed from {chat.id}")

async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.chat_member
    if not result: return
    old = result.old_chat_member; new = result.new_chat_member; chat = update.effective_chat
    if chat.title: register_group(chat.id, chat.title)
    if old.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED) and new.status == ChatMemberStatus.MEMBER:
        user = new.user; logger.info(f"Join: {user.id} -> {chat.id}")
        await log_join(context, user, chat)
        gcfg = get_group(chat.id)
        if gcfg.get("antifake_enabled", False):
            sus, reason = is_suspicious(user, gcfg.get("antifake_days", 7))
            if sus: await log_antifake(context, user, chat, reason)
    elif old.status == ChatMemberStatus.MEMBER and new.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
        user = new.user; logger.info(f"Leave: {user.id} <- {chat.id}")
        await log_leave(context, user, chat)

async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.from_user: return
    chat = update.effective_chat; user = message.from_user
    register_group(chat.id, chat.title or "Grupo")
    if await try_link_group(update, context): return
    if await kick_if_deleted(context, chat.id, user): return
    gcfg = get_group(chat.id)
    if gcfg.get("antifake_enabled", False):
        sus, reason = is_suspicious(user, gcfg.get("antifake_days", 7))
        if sus:
            await log_antifake(context, user, chat, reason)
            try:
                await context.bot.restrict_chat_member(chat_id=chat.id, user_id=user.id, permissions=ChatPermissions(can_send_messages=False))
                await context.bot.send_message(chat_id=chat.id, text=f"Anti-Fake: <code>{user.id}</code> restringido ({reason}).", parse_mode="HTML")
            except Exception as exc: logger.warning(f"Restrict failed: {exc}")
            return
    if await check_spam(message, context): return
    await handle_anonymous(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private": return
    await handle_callback(update, context)

def main() -> None:
    token = Config.BOT_TOKEN
    if not token: logger.critical("BOT_TOKEN not set!"); sys.exit(1)
    logger.info("Starting bot...")
    app = ApplicationBuilder().token(token).concurrent_updates(True).read_timeout(30).write_timeout(30).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, private_text_handler))
    app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL, group_message_handler))
    app.add_error_handler(global_error_handler)
    schedule_cleanup(app)
    logger.info("Bot is running.")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message","callback_query","chat_member","my_chat_member"])

if __name__ == "__main__":
    main()
