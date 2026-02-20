"""
Thread-safe JSON persistence layer.
Files: groups.json, user_groups.json, bot_messages.json
"""

import json
import os
import threading
import time
from typing import Any, Dict, List

from config import Config

_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()

GROUPS_FILE = "groups.json"
USER_GROUPS_FILE = "user_groups.json"
BOT_MESSAGES_FILE = "bot_messages.json"


# ──────────────────────────────────────────────
# Core JSON I/O
# ──────────────────────────────────────────────

def _get_lock(filename: str) -> threading.Lock:
    with _global_lock:
        if filename not in _locks:
            _locks[filename] = threading.Lock()
        return _locks[filename]


def _filepath(filename: str) -> str:
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    return os.path.join(Config.DATA_DIR, filename)


def load_json(filename: str) -> Dict[str, Any]:
    lock = _get_lock(filename)
    with lock:
        path = _filepath(filename)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


def save_json(filename: str, data: Dict[str, Any]) -> None:
    lock = _get_lock(filename)
    with lock:
        path = _filepath(filename)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


# ──────────────────────────────────────────────
# Group config
# ──────────────────────────────────────────────

def _default_group(title: str = "") -> Dict[str, Any]:
    return {
        "group_title": title or "Grupo",
        "custom_bot_name": Config.DEFAULT_BOT_NAME,
        "anonymous_mode": True,
        "vip_users": [],
        "antifake_enabled": True,
        "antifake_days": Config.ANTIFAKE_DEFAULT_DAYS,
        "antispam_enabled": True,
        "antispam_flood_limit": 5,
        "antispam_flood_window": 10,
        "antispam_mute_seconds": 300,
        "antispam_block_links": True,
        "cleanup_enabled": True,
        "forward_group": Config.LOG_GROUP_ID,
        "forward_events": {
            "join": True,
            "leave": True,
            "antifake": True,
            "antispam": True,
        },
        "roles": {},
        "chat_topic_id": None,
        "autoclean_minutes": 0,
        "settings": {},
    }


def register_group(group_id: int, title: str = "") -> Dict[str, Any]:
    groups = load_json(GROUPS_FILE)
    key = str(group_id)
    if key not in groups:
        groups[key] = _default_group(title)
        save_json(GROUPS_FILE, groups)
    elif title and groups[key].get("group_title") != title:
        groups[key]["group_title"] = title
        save_json(GROUPS_FILE, groups)
    return groups[key]


def get_group(group_id: int) -> Dict[str, Any]:
    groups = load_json(GROUPS_FILE)
    key = str(group_id)
    if key not in groups:
        return register_group(group_id)
    return groups[key]


def update_group(group_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
    groups = load_json(GROUPS_FILE)
    key = str(group_id)
    if key not in groups:
        register_group(group_id)
        groups = load_json(GROUPS_FILE)
    groups[key].update(patch)
    save_json(GROUPS_FILE, groups)
    return groups[key]


def all_groups() -> Dict[str, Any]:
    return load_json(GROUPS_FILE)


# ──────────────────────────────────────────────
# Per-user group links (each user sees only THEIR groups)
# Format: {"user_id_str": [group_id_int, ...]}
# ──────────────────────────────────────────────

def get_user_groups(user_id: int) -> List[int]:
    data = load_json(USER_GROUPS_FILE)
    return data.get(str(user_id), [])


def link_user_group(user_id: int, group_id: int) -> bool:
    """Link a group to a user. Returns False if already linked."""
    data = load_json(USER_GROUPS_FILE)
    key = str(user_id)
    groups = data.get(key, [])
    if group_id in groups:
        return False
    groups.append(group_id)
    data[key] = groups
    save_json(USER_GROUPS_FILE, data)
    return True


def unlink_user_group(user_id: int, group_id: int) -> bool:
    """Unlink a group from a user. Returns False if not linked."""
    data = load_json(USER_GROUPS_FILE)
    key = str(user_id)
    groups = data.get(key, [])
    if group_id not in groups:
        return False
    groups.remove(group_id)
    data[key] = groups
    save_json(USER_GROUPS_FILE, data)
    return True


# ──────────────────────────────────────────────
# VIP
# ──────────────────────────────────────────────

def get_vip_list(group_id: int) -> List[int]:
    return get_group(group_id).get("vip_users", [])


def add_vip(group_id: int, user_id: int) -> None:
    gcfg = get_group(group_id)
    vips = gcfg.get("vip_users", [])
    if user_id not in vips:
        vips.append(user_id)
        update_group(group_id, {"vip_users": vips})


def remove_vip(group_id: int, user_id: int) -> bool:
    gcfg = get_group(group_id)
    vips = gcfg.get("vip_users", [])
    if user_id in vips:
        vips.remove(user_id)
        update_group(group_id, {"vip_users": vips})
        return True
    return False


# ──────────────────────────────────────────────
# Roles
# ──────────────────────────────────────────────

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MOD = "mod"
VALID_ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_MOD)


def get_role(group_id: int, user_id: int) -> str | None:
    return get_group(group_id).get("roles", {}).get(str(user_id))


def set_role(group_id: int, user_id: int, role: str) -> None:
    gcfg = get_group(group_id)
    roles = gcfg.get("roles", {})
    roles[str(user_id)] = role
    update_group(group_id, {"roles": roles})


def remove_role(group_id: int, user_id: int) -> None:
    gcfg = get_group(group_id)
    roles = gcfg.get("roles", {})
    roles.pop(str(user_id), None)
    update_group(group_id, {"roles": roles})


def get_all_roles(group_id: int) -> Dict[str, str]:
    return get_group(group_id).get("roles", {})


# ──────────────────────────────────────────────
# Bot messages tracking (for auto-cleanup)
# Format: {"chat_id_str": [{"msg_id": int, "ts": float}, ...]}
# ──────────────────────────────────────────────

def track_bot_message(chat_id: int, message_id: int) -> None:
    """Record a bot message for future auto-deletion."""
    data = load_json(BOT_MESSAGES_FILE)
    key = str(chat_id)
    entries = data.get(key, [])
    entries.append({"msg_id": message_id, "ts": time.time()})
    # Cap at 500 entries per group to avoid bloat
    if len(entries) > 500:
        entries = entries[-500:]
    data[key] = entries
    save_json(BOT_MESSAGES_FILE, data)


def get_expired_bot_messages(chat_id: int, max_age_minutes: int) -> List[int]:
    """Return message IDs older than max_age_minutes."""
    if max_age_minutes <= 0:
        return []
    data = load_json(BOT_MESSAGES_FILE)
    key = str(chat_id)
    entries = data.get(key, [])
    now = time.time()
    cutoff = now - (max_age_minutes * 60)
    expired = [e["msg_id"] for e in entries if e["ts"] < cutoff]
    return expired


def remove_tracked_messages(chat_id: int, msg_ids: List[int]) -> None:
    """Remove tracked messages after deletion."""
    if not msg_ids:
        return
    data = load_json(BOT_MESSAGES_FILE)
    key = str(chat_id)
    entries = data.get(key, [])
    id_set = set(msg_ids)
    entries = [e for e in entries if e["msg_id"] not in id_set]
    data[key] = entries
    save_json(BOT_MESSAGES_FILE, data)
