"""
Central XP rules — kept separate from models.py so tuning values
doesn't touch the schema, and so both dashboard and AI-adjustment
routes import from one source of truth.
"""

BASE_XP_BY_CATEGORY = {
    "sleep": 10,
    "movement": 15,
    "hydration": 5,
    "mental_wellbeing": 10,
}

DEFAULT_XP = 10

BONUS_XP = {
    "early_completion": 5,      # completed well before scheduled time
    "streak_bonus": 10,         # maintained streak another day
    "daily_challenge": 15,      # completed an optional daily challenge
    "full_day_complete": 20,    # completed every task in the day's plan
    "recovery_bonus": 15,       # first task completed after a missed day
}


def base_xp_for_category(category: str) -> int:
    return BASE_XP_BY_CATEGORY.get(category, DEFAULT_XP)