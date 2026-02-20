"""
Logs bridge — sends structured logs to a configured destination group.
"""

import logging
from telegram import User, Chat, Message
from telegram.ext import ContextTypes

from storage_json import get_group
from utils import message_link

logger = logging.getLogger(__name__)


async def _send_log(context: ContextTypes.DEFAULT_TYPE, group_id: int, text: str) -> None:
    gcfg = get_group(group_id)
    dest = gcfg.get("forward_group", 0)
    if not dest:
        return
    try:
        await context.bot.send_message(
            chat_id=dest, text=text, parse_mode="HTML", disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.warning(f"Log send failed → {dest}: {exc}")


async def log_join(context: ContextTypes.DEFAULT_TYPE, user: User, chat: Chat) -> None:
    gcfg = get_group(chat.id)
    if not gcfg.get("forward_events", {}).get("join", True):
        return
    name = user.full_name or "Sin nombre"
    link = f'<a href="tg://user?id={user.id}">{name}</a>'
    await _send_log(context, chat.id, (
        f"➕ <b>#ENTRADA_USUARIO</b>\n"
        f"• De: {link} [<code>{user.id}</code>]\n"
        f"• Grupo: {chat.title or 'N/A'} [<code>{chat.id}</code>]\n"
        f"#id{user.id}"
    ))


async def log_leave(context: ContextTypes.DEFAULT_TYPE, user: User, chat: Chat) -> None:
    gcfg = get_group(chat.id)
    if not gcfg.get("forward_events", {}).get("leave", True):
        return
    name = user.full_name or "Sin nombre"
    await _send_log(context, chat.id, (
        f"➖ <b>#SALIDA_USUARIO</b>\n"
        f"• De: {name} [<code>{user.id}</code>]\n"
        f"• Grupo: {chat.title or 'N/A'} [<code>{chat.id}</code>]\n"
        f"#id{user.id}"
    ))


async def log_antifake(context: ContextTypes.DEFAULT_TYPE, user: User, chat: Chat, reason: str) -> None:
    gcfg = get_group(chat.id)
    if not gcfg.get("forward_events", {}).get("antifake", True):
        return
    name = user.full_name or "Sin nombre"
    await _send_log(context, chat.id, (
        f"🛡️ <b>#ANTIFAKE_ALERTA</b>\n"
        f"• Usuario: {name} [<code>{user.id}</code>]\n"
        f"• Grupo: {chat.title or 'N/A'} [<code>{chat.id}</code>]\n"
        f"• Razón: {reason}\n#id{user.id}"
    ))


async def log_antispam(context: ContextTypes.DEFAULT_TYPE, user: User, chat: Chat, reason: str) -> None:
    gcfg = get_group(chat.id)
    if not gcfg.get("forward_events", {}).get("antispam", True):
        return
    name = user.full_name or "Sin nombre"
    await _send_log(context, chat.id, (
        f"🚨 <b>#ANTISPAM_ALERTA</b>\n"
        f"• Usuario: {name} [<code>{user.id}</code>]\n"
        f"• Grupo: {chat.title or 'N/A'} [<code>{chat.id}</code>]\n"
        f"• Razón: {reason}\n#id{user.id}"
    ))


async def log_message(context: ContextTypes.DEFAULT_TYPE, user: User, chat: Chat, msg: Message | None = None) -> None:
    gcfg = get_group(chat.id)
    if not gcfg.get("forward_group", 0):
        return
    name = user.full_name or "Sin nombre"
    link_part = ""
    if msg:
        link_part = f'\n• 👀 <a href="{message_link(chat, msg.message_id)}">Ir al mensaje</a>'
    await _send_log(context, chat.id, (
        f"💬 <b>#MENSAJE</b>\n"
        f"• De: {name} [<code>{user.id}</code>]\n"
        f"• Grupo: {chat.title or 'N/A'} [<code>{chat.id}</code>]{link_part}\n"
        f"#id{user.id}"
    ))
