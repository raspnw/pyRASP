import os
import logging
import logging.config

from wxtofly.configuration import WxToFlyConfiguration

# initialize paths
configuration_path = os.path.join(os.path.dirname(__file__), 'config')
data_path = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_path):
    os.mkdir(data_path)

wxtofly_configuration = None
wxtofly_logger = None

logging_config_path = os.path.join(configuration_path, 'logging.cfg')
if os.path.exists(logging_config_path):
    logging.debug("Loading default logging configuration file: {0}".format(logging_config_path))
    logging.config.fileConfig(logging_config_path, disable_existing_loggers=False)

def get_configuration():
    global wxtofly_configuration
    if wxtofly_configuration is None:
        wxtofly_configuration = WxToFlyConfiguration(os.path.join(configuration_path, 'wxtofly.yaml'))
    return wxtofly_configuration

def get_logger():
    global wxtofly_logger
    if wxtofly_logger is None:
        wxtofly_logger = logging.getLogger('wxtofly')
    return wxtofly_logger