"""
Anti-fake account detection.
"""

from telegram import User

RECENT_ID_THRESHOLD = 6_500_000_000


def estimate_account_age_days(user: User) -> int | None:
    if user.id >= RECENT_ID_THRESHOLD:
        return 0
    return None


def is_suspicious(user: User, min_days: int) -> tuple[bool, str]:
    if not user.first_name:
        return True, "Cuenta eliminada (sin nombre)"
    age = estimate_account_age_days(user)
    if age is not None and age < min_days:
        return True, f"ID muy reciente (>{RECENT_ID_THRESHOLD})"
    return False, ""
