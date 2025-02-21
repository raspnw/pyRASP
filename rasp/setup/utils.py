import os

from rasp.setup import logger

def is_admin():
    if os.getuid() == 0:
        return True
    return False

def ensure_admin():
    if not is_admin():
        logger.error("Administrator privileges required. Run command again with 'sudo'")
        raise PermissionError("Administrator privileges required. Run command again with 'sudo'")
    else:
        logger.debug("Running as Administrator")
    

