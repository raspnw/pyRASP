import os
import logging
import sys

import rasp
import rasp.postprocess
from rasp.common.logging import start_file_log, stop_file_log

postprocess_logger = rasp.postprocess.get_logger()
postprocess_logger.debug('test')

handler = start_file_log(postprocess_logger, os.path.join(os.path.dirname(__file__), 'log1.log.csv'))
postprocess_logger.debug('test')
stop_file_log(postprocess_logger, handler)

handler = start_file_log(postprocess_logger, os.path.join(os.path.dirname(__file__), 'log2.log.csv'))
postprocess_logger.debug('test')
stop_file_log(postprocess_logger, handler)