# admin_checker.py
import logging
import os


logger = logging.getLogger(__name__)

def is_admin(admin_id: int) -> bool:
    logger.info(f"Checking if user with id {admin_id} is admin")
    admins = [int(x) for x in os.getenv('ADMINS_IDS').split(',')]
    return admin_id in admins