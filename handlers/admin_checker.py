# admin_checker.py
import logging
import os

logger = logging.getLogger(__name__)


def is_admin(username: str) -> bool:
    logger.info(f"Checking if {username} is admin")
    admins = os.getenv('ADMINS').split(',')
    return username in admins
