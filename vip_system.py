"""
VIP system — thin helper.
"""

from storage_json import get_vip_list


def is_vip(group_id: int, user_id: int) -> bool:
    return user_id in get_vip_list(group_id)
