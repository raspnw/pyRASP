import os
import logging
import logging.config
import errno

# initialize path to dir containing config files
configuration_path = os.path.join(
    os.path.dirname(__file__), 
    "config")

logger = logging.getLogger()

if not os.path.exists(configuration_path):
    logging.error("Configuration path %s not found", configuration_path)
    raise FileNotFoundError(
        errno.ENOENT, 
        os.strerror(errno.ENOENT), 
        configuration_path)

logging_config_path = os.path.join(configuration_path, 'logging.cfg')
if os.path.exists(logging_config_path):
    logger.debug("Loading default logging configuration file: {0}".format(logging_config_path))
    logging.config.fileConfig(logging_config_path, disable_existing_loggers=False)

logger.debug("Configuration path: {0}".format(configuration_path))

