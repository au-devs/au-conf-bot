import logging
import os

from db.database import get_civil_war_chance_override


logger = logging.getLogger(__name__)

DEFAULT_SUCCESS_CHANCE = 0.0666
DEFAULT_RARE_SUCCESS_CHANCE = 0.00666
DEFAULT_RARE_LOSS_CHANCE = 0.0133
DEFAULT_MAFIA_EVENT_CHANCE = 0.0888
DEFAULT_RAT_EVENT_CHANCE = 0.015

GLOBAL_SUCCESS_KEY = "global_success"
GLOBAL_RARE_KEY = "global_rare"
GLOBAL_RARE_LOSS_KEY = "global_rare_loss"
GLOBAL_MAFIA_EVENT_KEY = "global_mafia_event"
GLOBAL_RAT_EVENT_KEY = "global_rat_event"


def normalize_chance(value: float) -> float:
    if value > 1:
        value = value / 100
    return min(max(value, 0), 1)


def parse_chance(value: str) -> float:
    normalized = value.strip().replace(",", ".")
    if normalized.endswith("%"):
        normalized = normalized[:-1].strip()
        return normalize_chance(float(normalized) / 100)
    return normalize_chance(float(normalized))


def format_chance(chance: float) -> str:
    return f"{chance * 100:.3f}%"


def get_env_chance(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return parse_chance(value)
    except ValueError:
        logger.warning(f"Invalid {name}={value!r}, using default {default}")
        return default


def get_global_success_chance(db_path: str) -> float:
    override = get_civil_war_chance_override(db_path, GLOBAL_SUCCESS_KEY)
    if override is not None:
        return normalize_chance(override)
    return get_env_chance("CIVIL_WAR_SUCCESS_CHANCE", DEFAULT_SUCCESS_CHANCE)


def get_global_rare_chance(db_path: str) -> float:
    override = get_civil_war_chance_override(db_path, GLOBAL_RARE_KEY)
    if override is not None:
        return normalize_chance(override)
    return get_env_chance("CIVIL_WAR_RARE_SUCCESS_CHANCE", DEFAULT_RARE_SUCCESS_CHANCE)


def get_global_rare_loss_chance(db_path: str) -> float:
    override = get_civil_war_chance_override(db_path, GLOBAL_RARE_LOSS_KEY)
    if override is not None:
        return normalize_chance(override)
    return get_env_chance("CIVIL_WAR_RARE_LOSS_CHANCE", DEFAULT_RARE_LOSS_CHANCE)


def get_global_mafia_event_chance(db_path: str) -> float:
    override = get_civil_war_chance_override(db_path, GLOBAL_MAFIA_EVENT_KEY)
    if override is not None:
        return normalize_chance(override)
    return get_env_chance("CIVIL_WAR_MAFIA_EVENT_CHANCE", DEFAULT_MAFIA_EVENT_CHANCE)


def get_global_rat_event_chance(db_path: str) -> float:
    override = get_civil_war_chance_override(db_path, GLOBAL_RAT_EVENT_KEY)
    if override is not None:
        return normalize_chance(override)
    return get_env_chance("CIVIL_WAR_RAT_EVENT_CHANCE", DEFAULT_RAT_EVENT_CHANCE)
