"""
UI Panel - interactive SaaS dashboard.
Per-user group lists. Edit_message navigation. No commands for admin.
"""
import logging
from telegram import Update, InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB
from telegram.ext import ContextTypes
from config import Config
from storage_json import (
    get_group, update_group, all_groups, register_group,
    add_vip, remove_vip, get_vip_list, get_all_roles, set_role, remove_role,
    get_user_groups, link_user_group, unlink_user_group,
)
from roles import sync_admins_from_telegram
logger = logging.getLogger(__name__)
_user_state = {}
def set_user_state(uid, state):
    if state is None: _user_state.pop(uid, None)
    else: _user_state[uid] = state
def get_user_state(uid): return _user_state.get(uid)
def _back(t="home"): return Btn("< Volver", callback_data=f"p_{t}")
def _glabel(gid, cfg):
    t = cfg.get("group_title","")
    if not t or t == "Grupo": t = cfg.get("custom_bot_name", str(gid))
    return t[:28] if len(t) <= 28 else t[:25]+"..."
def _ugbtns(uid, pfx):
    gids = get_user_groups(uid); gs = all_groups(); btns = []
    for g in gids:
        c = gs.get(str(g), {})
        if c: btns.append([Btn(f"{_glabel(str(g),c)}", callback_data=f"{pfx}_{g}")])
    if not btns: btns.append([Btn("-- Sin grupos vinculados --", callback_data="p_home")])
    btns.append([_back()]); return btns
async def _edit(q, txt, kb):
    try: await q.edit_message_caption(caption=txt, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try: await q.edit_message_text(text=txt, parse_mode="HTML", reply_markup=kb)
        except Exception as e: logger.warning(f"Edit fail: {e}")
HOME = "<b>Panel Privado</b>\n\nBienvenido al centro de control.\nSelecciona una opcion:"
def _hkb():
    return KB([
        [Btn("Mis Grupos", callback_data="p_mygroups")],
        [Btn("Nombre del Bot", callback_data="p_botname_info")],
        [Btn("Modo Anonimo", callback_data="p_anon_info")],
        [Btn("Sistema VIP", callback_data="p_vip_info")],
        [Btn("Anti-Fake", callback_data="p_antifake_info")],
        [Btn("Anti-Spam", callback_data="p_antispam_info")],
        [Btn("Logs y Notificaciones", callback_data="p_logs_info")],
        [Btn("Limpieza", callback_data="p_cleanup_info")],
        [Btn("Topicos / Temas", callback_data="p_topic_info")],
        [Btn("Auto-Limpieza Msgs", callback_data="p_autoclean_info")],
        [Btn("Roles y Permisos", callback_data="p_roles_info")],
        [Btn("Refrescar", callback_data="p_refresh")],
    ])
async def send_panel(update, context):
    cid = update.effective_chat.id
    try: await context.bot.send_photo(chat_id=cid, photo=Config.PANEL_IMAGE_URL, caption=HOME, parse_mode="HTML", reply_markup=_hkb())
    except Exception: await context.bot.send_message(chat_id=cid, text=HOME, parse_mode="HTML", reply_markup=_hkb())
INFO = {
    "mygroups": "<b>MIS GRUPOS</b>\n\nQue es: Lista de grupos vinculados a TU panel. Cada usuario ve solo sus grupos.\n\nComo vincular:\n1. Toca Vincular grupo\n2. Ve al grupo y escribe cualquier mensaje\n3. El bot verifica que seas admin y lo vincula\n\nDesvincular: Quita un grupo de tu panel (no borra la config).",
    "anon": "<b>MODO ANONIMO</b>\n\nQue hace: Borra el mensaje original y lo reenvia mostrando solo el ID.\n\nEjemplo:\nUsuario Anonimo\nID: 123456789\nHola!",
    "vip": "<b>SISTEMA VIP</b>\n\nQue hace: Usuarios VIP no pasan por modo anonimo.\n\nComo: Agrega/quita por ID numerico.",
    "botname": "<b>NOMBRE DEL BOT</b>\n\nQue hace: Nombre visual en mensajes anonimos.\nTelegram no permite cambiar el @username real.",
    "antifake": "<b>ANTI-FAKE</b>\n\nQue hace: Detecta cuentas sospechosas y restringe.\nNota: Telegram no expone fecha de creacion.",
    "antispam": "<b>ANTI-SPAM</b>\n\nQue hace: Detecta flood, repeticion y links.\nAcciones: Borrar - Advertir - Mute temporal.",
    "logs": "<b>LOGS Y NOTIFICACIONES</b>\n\nQue hace: Reenvia eventos a un grupo de logs privado.\nEventos: Entradas, salidas, anti-fake, anti-spam.",
    "cleanup": "<b>LIMPIEZA</b>\n\nQue hace: Expulsa cuentas eliminadas automaticamente.",
    "topic": "<b>TOPICOS / TEMAS</b>\n\nQue hace: Fija un tema donde van los mensajes anonimos.\nSi no esta fijado: El bot responde en el mismo tema donde escribio el usuario.\nComo: Envia el ID numerico del tema. 0 = desactivar.",
    "autoclean": "<b>AUTO-LIMPIEZA MENSAJES</b>\n\nQue hace: Borra mensajes del bot despues de X tiempo.\nOpciones: 15min | 1h | 6h | 24h | OFF\nJob cada 5 min revisa y borra expirados.",
    "roles": "<b>ROLES Y PERMISOS</b>\n\nJerarquia: OWNER > ADMIN > MOD\nSync: Detecta admins de Telegram automaticamente.",
}
async def handle_callback(update, context):
    q = update.callback_query; await q.answer(); d = q.data or ""; uid = update.effective_user.id
    if d in ("p_home","p_refresh"): set_user_state(uid, None); await _edit(q, HOME, _hkb()); return
    if d == "p_mygroups": await _smg(q, uid); return
    if d == "p_link_group":
        set_user_state(uid, {"action":"link_group"})
        await _edit(q, "<b>Vincular grupo</b>\n\nVe al grupo donde el bot es admin y escribe cualquier mensaje.\nEl bot verificara que eres admin y lo vinculara.", KB([[Btn("Cancelar", callback_data="p_mygroups")]])); return
    if d.startswith("p_unlink_"):
        gid = int(d.split("_",2)[2]); unlink_user_group(uid, gid); await _smg(q, uid); return
    im = [("p_anon_info","anon","p_anon_sel"),("p_vip_info","vip","p_vip_sel"),("p_botname_info","botname","p_name_sel"),("p_antifake_info","antifake","p_af_sel"),("p_antispam_info","antispam","p_as_sel"),("p_logs_info","logs","p_log_sel"),("p_cleanup_info","cleanup","p_cl_sel"),("p_topic_info","topic","p_topic_sel"),("p_autoclean_info","autoclean","p_ac_sel"),("p_roles_info","roles","p_role_sel")]
    for cb, key, sel in im:
        if d == cb: await _edit(q, INFO[key], KB([[Btn("Configurar", callback_data=sel)],[_back()]])); return
    sels = {"p_anon_sel":("Modo Anonimo - Selecciona grupo:","anontg"),"p_vip_sel":("VIP - Selecciona grupo:","vipg"),"p_name_sel":("Nombre - Selecciona grupo:","nameg"),"p_af_sel":("Anti-Fake - Selecciona grupo:","afg"),"p_as_sel":("Anti-Spam - Selecciona grupo:","asg"),"p_log_sel":("Logs - Selecciona grupo:","logg"),"p_cl_sel":("Limpieza - Selecciona grupo:","clg"),"p_topic_sel":("Topicos - Selecciona grupo:","topicg"),"p_ac_sel":("Auto-Limpieza - Selecciona grupo:","acg"),"p_role_sel":("Roles - Selecciona grupo:","roleg")}
    if d in sels: tx, pf = sels[d]; await _edit(q, tx, KB(_ugbtns(uid, pf))); return
    # ANON
    if d.startswith("anontg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); c=gc.get("anonymous_mode",True); st="ON" if c else "OFF"
        await _edit(q, f"<b>Modo Anonimo</b>\n{gc.get('group_title',gid)}\nEstado: {st}", KB([[Btn("Desactivar" if c else "Activar", callback_data=f"anondo_{gid}")],[_back("anon_info")]])); return
    if d.startswith("anondo_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); update_group(gid,{"anonymous_mode":not gc.get("anonymous_mode",True)}); q.data=f"anontg_{gid}"; await handle_callback(update,context); return
    # VIP
    if d.startswith("vipg_"): gid=int(d.split("_",1)[1]); await _svip(q,gid); return
    if d.startswith("vipadd_"):
        gid=int(d.split("_",1)[1]); set_user_state(uid,{"action":"add_vip","group_id":gid})
        await _edit(q, "Envia el <b>ID del usuario</b>:", KB([[Btn("Cancelar", callback_data=f"vipg_{gid}")]])); return
    if d.startswith("viprm_"):
        gid=int(d.split("_",1)[1]); set_user_state(uid,{"action":"rm_vip","group_id":gid})
        await _edit(q, "Envia el <b>ID del usuario</b> a quitar:", KB([[Btn("Cancelar", callback_data=f"vipg_{gid}")]])); return
    # NAME
    if d.startswith("nameg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); set_user_state(uid,{"action":"set_name","group_id":gid})
        await _edit(q, f"Actual: <b>{gc.get('custom_bot_name','???')}</b>\n\nEnvia el <b>nuevo nombre</b>:", KB([[Btn("Cancelar", callback_data="p_botname_info")]])); return
    # ANTI-FAKE
    if d.startswith("afg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); c=gc.get("antifake_enabled",True); st="ON" if c else "OFF"
        await _edit(q, f"<b>Anti-Fake</b>\n{gc.get('group_title',gid)}\nEstado: {st}", KB([[Btn("Desactivar" if c else "Activar", callback_data=f"afdo_{gid}")],[_back("antifake_info")]])); return
    if d.startswith("afdo_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); update_group(gid,{"antifake_enabled":not gc.get("antifake_enabled",True)}); q.data=f"afg_{gid}"; await handle_callback(update,context); return
    # ANTI-SPAM
    if d.startswith("asg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); c=gc.get("antispam_enabled",True); lk=gc.get("antispam_block_links",True)
        st="ON" if c else "OFF"; ls="ON" if lk else "OFF"
        await _edit(q, f"<b>Anti-Spam</b>\n{gc.get('group_title',gid)}\nEstado: {st} | Links: {ls}", KB([[Btn("Desactivar" if c else "Activar", callback_data=f"asdo_{gid}")],[Btn(f"Links: {ls}", callback_data=f"aslinks_{gid}")],[_back("antispam_info")]])); return
    if d.startswith("asdo_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); update_group(gid,{"antispam_enabled":not gc.get("antispam_enabled",True)}); q.data=f"asg_{gid}"; await handle_callback(update,context); return
    if d.startswith("aslinks_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); update_group(gid,{"antispam_block_links":not gc.get("antispam_block_links",True)}); q.data=f"asg_{gid}"; await handle_callback(update,context); return
    # LOGS
    if d.startswith("logg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); dest=gc.get("forward_group",0); ev=gc.get("forward_events",{})
        j="ON" if ev.get("join",True) else "OFF"; le="ON" if ev.get("leave",True) else "OFF"
        af="ON" if ev.get("antifake",True) else "OFF"; sp="ON" if ev.get("antispam",True) else "OFF"
        await _edit(q, f"<b>Logs</b>\n{gc.get('group_title',gid)}\nDestino: <code>{dest or 'No config'}</code>", KB([
            [Btn(f"Entradas: {j}", callback_data=f"logevt_join_{gid}")],[Btn(f"Salidas: {le}", callback_data=f"logevt_leave_{gid}")],
            [Btn(f"Anti-Fake: {af}", callback_data=f"logevt_antifake_{gid}")],[Btn(f"Anti-Spam: {sp}", callback_data=f"logevt_antispam_{gid}")],
            [Btn("Cambiar destino", callback_data=f"logdest_{gid}")],[_back("logs_info")],
        ])); return
    if d.startswith("logevt_"):
        p=d.split("_"); ev=p[1]; gid=int("_".join(p[2:])); gc=get_group(gid); e=gc.get("forward_events",{}); e[ev]=not e.get(ev,True)
        update_group(gid,{"forward_events":e}); q.data=f"logg_{gid}"; await handle_callback(update,context); return
    if d.startswith("logdest_"):
        gid=int(d.split("_",1)[1]); set_user_state(uid,{"action":"set_log_dest","group_id":gid})
        await _edit(q, "Envia el <b>ID del grupo de logs</b>:", KB([[Btn("Cancelar", callback_data=f"logg_{gid}")]])); return
    # CLEANUP
    if d.startswith("clg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); c=gc.get("cleanup_enabled",True); st="ON" if c else "OFF"
        await _edit(q, f"<b>Limpieza</b>\n{gc.get('group_title',gid)}\nEstado: {st}", KB([[Btn("Desactivar" if c else "Activar", callback_data=f"cldo_{gid}")],[_back("cleanup_info")]])); return
    if d.startswith("cldo_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); update_group(gid,{"cleanup_enabled":not gc.get("cleanup_enabled",True)}); q.data=f"clg_{gid}"; await handle_callback(update,context); return
    # TOPICS
    if d.startswith("topicg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); ct=gc.get("chat_topic_id")
        ct_txt=f"<code>{ct}</code>" if ct else "No fijado"
        set_user_state(uid,{"action":"set_topic","group_id":gid})
        await _edit(q, f"<b>Topico fijo</b>\n{gc.get('group_title',gid)}\nActual: {ct_txt}\n\nEnvia el <b>ID del tema</b> (0=quitar):", KB([[Btn("Quitar tema", callback_data=f"topicrm_{gid}")],[Btn("Cancelar", callback_data="p_topic_info")]])); return
    if d.startswith("topicrm_"):
        gid=int(d.split("_",1)[1]); update_group(gid,{"chat_topic_id":None}); set_user_state(uid,None)
        q.data=f"topicg_{gid}"; await handle_callback(update,context); return
    # AUTOCLEAN
    if d.startswith("acg_"):
        gid=int(d.split("_",1)[1]); gc=get_group(gid); cur=gc.get("autoclean_minutes",0)
        labs = {0:"OFF",15:"15 min",60:"1 hora",360:"6 horas",1440:"24 horas"}
        ct = labs.get(cur, f"{cur}min")
        bs = []
        for v, l in labs.items():
            mark = " *" if v == cur else ""
            bs.append(Btn(f"{l}{mark}", callback_data=f"acset_{v}_{gid}"))
        await _edit(q, f"<b>Auto-Limpieza</b>\n{gc.get('group_title',gid)}\nActual: <b>{ct}</b>", KB([bs[:3],bs[3:],[_back("autoclean_info")]])); return
    if d.startswith("acset_"):
        p=d.split("_"); val=int(p[1]); gid=int("_".join(p[2:]))
        update_group(gid,{"autoclean_minutes":val}); q.data=f"acg_{gid}"; await handle_callback(update,context); return
    # ROLES
    if d.startswith("roleg_"): gid=int(d.split("_",1)[1]); await _sroles(q,gid); return
    if d.startswith("rolesync_"):
        gid=int(d.split("_",1)[1]); await sync_admins_from_telegram(context,gid); q.data=f"roleg_{gid}"; await handle_callback(update,context); return
    if d.startswith("roleadd_"):
        gid=int(d.split("_",1)[1]); set_user_state(uid,{"action":"add_role","group_id":gid})
        await _edit(q, "Envia: <code>USER_ID rol</code>\nRoles: owner, admin, mod", KB([[Btn("Cancelar", callback_data=f"roleg_{gid}")]])); return
    if d.startswith("rolerm_"):
        gid=int(d.split("_",1)[1]); set_user_state(uid,{"action":"rm_role","group_id":gid})
        await _edit(q, "Envia el <b>ID del usuario</b> a quitar:", KB([[Btn("Cancelar", callback_data=f"roleg_{gid}")]])); return

async def _smg(q, uid):
    gids = get_user_groups(uid); gs = all_groups()
    if not gids: txt = "<b>Mis Grupos</b>\n\nNo tienes grupos vinculados.\nToca + para vincular uno."
    else:
        lines = []
        for g in gids:
            c = gs.get(str(g),{})
            if not c: continue
            t=c.get("group_title","?"); an="ON" if c.get("anonymous_mode") else "OFF"; vi=len(c.get("vip_users",[]))
            lines.append(f"<b>{t}</b>\n  ID: <code>{g}</code> | Anon: {an} | VIPs: {vi}")
        txt = "<b>Mis Grupos</b>\n\n" + ("\n\n".join(lines) if lines else "Sin datos")
    btns = []
    for g in gids:
        c = gs.get(str(g),{})
        if c: btns.append([Btn(f"Desvincular: {_glabel(str(g),c)}", callback_data=f"p_unlink_{g}")])
    btns.append([Btn("+ Vincular grupo", callback_data="p_link_group")]); btns.append([_back()])
    await _edit(q, txt, KB(btns))

async def _svip(q, gid):
    gc=get_group(gid); vips=get_vip_list(gid)
    vt = "\n".join(f"  <code>{v}</code>" for v in vips) if vips else "  -- ninguno --"
    await _edit(q, f"<b>VIP</b>\n{gc.get('group_title',gid)}\n\n{vt}", KB([[Btn("Agregar", callback_data=f"vipadd_{gid}"),Btn("Quitar", callback_data=f"viprm_{gid}")],[_back("vip_info")]]))

async def _sroles(q, gid):
    gc=get_group(gid); roles=get_all_roles(gid)
    ic={"owner":"OWNER","admin":"ADMIN","mod":"MOD"}
    rt = "\n".join(f"  <code>{u}</code> = {ic.get(r,r)}" for u,r in roles.items()) if roles else "  -- ninguno --"
    await _edit(q, f"<b>Roles</b>\n{gc.get('group_title',gid)}\n\n{rt}", KB([[Btn("Sync admins TG", callback_data=f"rolesync_{gid}")],[Btn("Agregar", callback_data=f"roleadd_{gid}"),Btn("Quitar", callback_data=f"rolerm_{gid}")],[_back("roles_info")]]))

async def handle_text_input(update, context):
    user = update.effective_user; state = get_user_state(user.id)
    if not state: return
    text = update.effective_message.text.strip(); action = state.get("action"); gid = state.get("group_id")
    if action == "add_vip":
        try: vid=int(text)
        except ValueError: await update.effective_message.reply_text("ID invalido."); return
        add_vip(gid,vid); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"<code>{vid}</code> agregado VIP.", parse_mode="HTML"); return
    if action == "rm_vip":
        try: vid=int(text)
        except ValueError: await update.effective_message.reply_text("ID invalido."); return
        r=remove_vip(gid,vid); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"<code>{vid}</code> {'removido' if r else 'no estaba en lista'}.", parse_mode="HTML"); return
    if action == "set_name":
        update_group(gid,{"custom_bot_name":text[:64]}); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"Nombre: <b>{text[:64]}</b>", parse_mode="HTML"); return
    if action == "set_log_dest":
        try: dest=int(text)
        except ValueError: await update.effective_message.reply_text("ID invalido."); return
        update_group(gid,{"forward_group":dest}); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"Destino: <code>{dest}</code>", parse_mode="HTML"); return
    if action == "set_topic":
        try: tid=int(text)
        except ValueError: await update.effective_message.reply_text("Numero invalido."); return
        update_group(gid,{"chat_topic_id":tid if tid>0 else None}); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"Tema: <code>{tid if tid>0 else 'OFF'}</code>", parse_mode="HTML"); return
    if action == "add_role":
        parts=text.split()
        if len(parts)!=2: await update.effective_message.reply_text("Formato: USER_ID rol"); return
        try: rid=int(parts[0])
        except ValueError: await update.effective_message.reply_text("ID invalido."); return
        role=parts[1].lower()
        if role not in ("owner","admin","mod"): await update.effective_message.reply_text("Roles: owner, admin, mod"); return
        set_role(gid,rid,role); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"<b>{role}</b> asignado a <code>{rid}</code>.", parse_mode="HTML"); return
    if action == "rm_role":
        try: rid=int(text)
        except ValueError: await update.effective_message.reply_text("ID invalido."); return
        remove_role(gid,rid); set_user_state(user.id,None)
        await update.effective_message.reply_text(f"Rol removido de <code>{rid}</code>.", parse_mode="HTML"); return

async def try_link_group(update, context):
    user = update.effective_user
    if not user: return False
    state = get_user_state(user.id)
    if not state or state.get("action") != "link_group": return False
    chat = update.effective_chat
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator","creator"): return False
    except Exception: return False
    register_group(chat.id, chat.title or "Grupo")
    linked = link_user_group(user.id, chat.id)
    set_user_state(user.id, None)
    title = chat.title or "Grupo"
    try:
        if linked: await context.bot.send_message(chat_id=user.id, text=f"Grupo <b>{title}</b> (<code>{chat.id}</code>) vinculado.", parse_mode="HTML")
        else: await context.bot.send_message(chat_id=user.id, text=f"<b>{title}</b> ya estaba vinculado.", parse_mode="HTML")
    except Exception: logger.warning(f"Cant DM {user.id} for link confirm")
    return True
