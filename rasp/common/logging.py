import os
import sys
import csv
import logging
import traceback
import io

def get_csv_formatter():
    return CsvFormatter(datefmt="%Y-%m-%d %H:%M:%S.%f")

def start_file_log(logger, path):

    if os.path.exists(path):
        os.remove(path)

    handler = logging.FileHandler(path)
    formatter = get_csv_formatter()
    #logging.Formatter(fmt = "%(asctime)s: [%(levelname)s] - %(message)s", datefmt = "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return handler

def stop_file_log(logger, handler):
    logger.removeHandler(handler)

def log_exception(message, e, logger):
    if message:
        logger.error("ERROR: {0}: {1}".format(message, e))
    exc_type, exc_value, exc_tb = sys.exc_info()
    stack_trace = traceback.format_exception(exc_type, exc_value, exc_tb)
    for l in stack_trace:
        logger.debug('[EXCEPTION]{0}'.format(l.strip()))

class CsvFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.output = io.StringIO()
        self.writer = csv.writer(self.output, quoting=csv.QUOTE_ALL)

    def format(self, record):
        self.writer.writerow([self.formatTime(record), record.levelname, self.formatMessage(record)])
        data = self.output.getvalue()
        self.output.truncate(0)
        self.output.seek(0)
        return data.strip()