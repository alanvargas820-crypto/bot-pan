"""
Anonymous mode — core logic.
Respects message_thread_id (topics/themes).
Tracks sent messages for auto-cleanup.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from storage_json import get_group, track_bot_message
from logs_bridge import log_message

logger = logging.getLogger(__name__)


def _build_header(bot_name: str, user_id: int) -> str:
    return (
        f"<b>{bot_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Usuario Anónimo</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━"
    )


def _get_thread_id(gcfg: dict, message) -> int | None:
    """
    1. Fixed chat_topic_id in config → use that
    2. Else message.message_thread_id → use same thread
    3. Else → None
    """
    fixed = gcfg.get("chat_topic_id")
    if fixed:
        return int(fixed)
    if message and message.message_thread_id:
        return message.message_thread_id
    return None


async def handle_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.effective_message
    if not message or not message.from_user:
        return False

    chat = update.effective_chat
    user = message.from_user
    gcfg = get_group(chat.id)

    if not gcfg.get("anonymous_mode", True):
        return False

    vips = gcfg.get("vip_users", [])
    if user.id in vips:
        return False

    bot_name = gcfg.get("custom_bot_name") or "🤖 AnonBot"
    header = _build_header(bot_name, user.id)
    thread_id = _get_thread_id(gcfg, message)
    sent = None

    base = {"chat_id": chat.id, "parse_mode": "HTML"}
    if thread_id:
        base["message_thread_id"] = thread_id

    try:
        if message.text:
            sent = await context.bot.send_message(**base, text=f"{header}\n\n{message.text}")

        elif message.photo:
            sent = await context.bot.send_photo(**base, photo=message.photo[-1].file_id, caption=f"{header}\n\n{message.caption or ''}")

        elif message.video:
            sent = await context.bot.send_video(**base, video=message.video.file_id, caption=f"{header}\n\n{message.caption or ''}")

        elif message.document:
            sent = await context.bot.send_document(**base, document=message.document.file_id, caption=f"{header}\n\n{message.caption or ''}")

        elif message.voice:
            sent = await context.bot.send_voice(**base, voice=message.voice.file_id, caption=header)

        elif message.audio:
            sent = await context.bot.send_audio(**base, audio=message.audio.file_id, caption=f"{header}\n\n{message.caption or ''}")

        elif message.sticker:
            h = await context.bot.send_message(**base, text=header)
            track_bot_message(chat.id, h.message_id)
            skw = {"chat_id": chat.id, "sticker": message.sticker.file_id}
            if thread_id:
                skw["message_thread_id"] = thread_id
            sent = await context.bot.send_sticker(**skw)

        elif message.animation:
            sent = await context.bot.send_animation(**base, animation=message.animation.file_id, caption=f"{header}\n\n{message.caption or ''}")

        elif message.video_note:
            h = await context.bot.send_message(**base, text=header)
            track_bot_message(chat.id, h.message_id)
            vkw = {"chat_id": chat.id, "video_note": message.video_note.file_id}
            if thread_id:
                vkw["message_thread_id"] = thread_id
            sent = await context.bot.send_video_note(**vkw)

        elif message.location:
            h = await context.bot.send_message(**base, text=header)
            track_bot_message(chat.id, h.message_id)
            lkw = {"chat_id": chat.id, "latitude": message.location.latitude, "longitude": message.location.longitude}
            if thread_id:
                lkw["message_thread_id"] = thread_id
            sent = await context.bot.send_location(**lkw)

        elif message.contact:
            h = await context.bot.send_message(**base, text=header)
            track_bot_message(chat.id, h.message_id)
            ckw = {"chat_id": chat.id, "phone_number": message.contact.phone_number, "first_name": message.contact.first_name or "Anónimo"}
            if thread_id:
                ckw["message_thread_id"] = thread_id
            sent = await context.bot.send_contact(**ckw)

        else:
            sent = await context.bot.send_message(**base, text=f"{header}\n\n[Contenido no soportado]")

        if sent:
            track_bot_message(chat.id, sent.message_id)

        try:
            await message.delete()
        except Exception as exc:
            logger.warning(f"Could not delete original: {exc}")

        await log_message(context, user, chat, sent)
        return True

    except Exception as exc:
        logger.error(f"Anon repost failed: {exc}")
        return False
