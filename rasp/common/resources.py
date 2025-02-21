import os
import logging
import platform
import resource

def set_limit(logger=logging.getLogger()):
    if (platform.system().lower() == 'linux'):
        logger.debug("Setting resource limit RLIMIT_STACK -> RLIM_INFINITY")
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
