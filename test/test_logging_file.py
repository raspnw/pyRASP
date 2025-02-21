import os
import logging
import datetime
import errno
import glob
import shutil
import time

import rasp
from rasp.common.logging import start_file_log, stop_file_log
from rasp.configuration import base_path

if __name__ == '__main__':

    logger = logging.getLogger();
    handler = start_file_log(logger, os.path.join(base_path, 'test.log.csv'))
    
    logger.debug('debug')
    logger.info('info')
    
    logger.info("Initializing region %s", 'TEST')
    
    
    stop_file_log(logger, handler)
    logger.debug('debug')
    logger.info('info')

    try:
        raise Exception("test")
    except Exception as e:
        logger.exception("error")
