import os
import logging
import sys

import wxtofly
from wxtofly.utils.loghandler import start_file_upload_log, stop_file_upload_log

logger = wxtofly.get_logger()

handler = start_file_upload_log(logger, logging.DEBUG)
logger.debug('test')
logger.info('test')
stop_file_upload_log(logger, handler)
