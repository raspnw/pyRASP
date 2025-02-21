import os
import logging
import datetime
import errno
import glob
import shutil
import time
import json

from wxtofly.utils.jsonlog import start_json_log, stop_json_log

logger = logging.getLogger()

if __name__ == '__main__':
    handler = start_json_log(logger, logging.INFO)
    logger.debug('debug')
    logger.info('info')
    logger.error('error')
    stop_json_log(logger, handler)
