import os
import logging
import time
import json
import tempfile
import shutil
from socket import gethostname
import threading

from rasp.postprocess.publish.utils import publish_file
from rasp.common.logging import log_exception, get_csv_formatter

class FileUploadHandler(logging.FileHandler):

    uploadLock = threading.Lock()
    emitLock = threading.Lock()
    logger = logging.getLogger()

    def uploadJson(path):
        FileUploadHandler.uploadLock.acquire()
        try:
            FileUploadHandler.emitLock.acquire()
            try:
                tmpfile = tempfile.NamedTemporaryFile(mode='r+b', delete=False)
                with open(path, 'r+b') as f_in:
                    shutil.copyfileobj(f_in, tmpfile)
                tmpfile.close()
            except Exception as e:
                log_exception("Creating log file failed", e, FileUploadHandler.logger)
                raise
            finally:
                FileUploadHandler.emitLock.release()

            try:
                publish_file(tmpfile.name, '/logs/{0}.csv'.format(gethostname()), FileUploadHandler.logger)
            except Exception as e:
                log_exception("Uploading log file failed", e, FileUploadHandler.logger)
                raise
            finally:
                os.remove(tmpfile.name)
        finally:
            FileUploadHandler.uploadLock.release()

    def __init__(self):
        with tempfile.NamedTemporaryFile() as f:
            filename = f.name

        if os.path.exists(filename):
            os.remove(filename)

        self.threads = []
        return super().__init__(filename)

    def emit(self, record):
        FileUploadHandler.emitLock.acquire()
        try:
            super().emit(record)
        finally:
            FileUploadHandler.emitLock.release()
        for t in self.threads:
            if not t.is_alive():
                self.threads.remove(t)
        FileUploadHandler.logger.debug("starting log upload thread for message: {0}".format(record.getMessage()))
        thread = threading.Thread(target=FileUploadHandler.uploadJson, args=(self.baseFilename, ))
        thread.start()
        self.threads.append(thread)

    def close(self):
        super().close()
        for t in self.threads:
            if t.is_alive():
               t.join()
        if os.path.exists(self.baseFilename):
            os.remove(self.baseFilename)


def start_file_upload_log(logger, level):
    formatter = get_csv_formatter()
    handler = FileUploadHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)
    return handler

def stop_file_upload_log(logger, handler):
    handler.close()
    logger.removeHandler(handler)


BUILTIN_ATTRS = {
    'args',
    'asctime',
    'created',
    'exc_info',
    'exc_text',
    'filename',
    'funcName',
    'levelname',
    'levelno',
    'lineno',
    'module',
    'msecs',
    'message',
    'msg',
    'name',
    'pathname',
    'process',
    'processName',
    'relativeCreated',
    'stack_info',
    'thread',
    'threadName',
}


class JSONFormatter(logging.Formatter):
    """JSON log formatter.

    Usage example::

        import logging

        import json_log_formatter

        json_handler = logging.FileHandler(filename='/var/log/my-log.json')
        json_handler.setFormatter(json_log_formatter.JSONFormatter())

        logger = logging.getLogger('my_json')
        logger.addHandler(json_handler)

        logger.info('Sign up', extra={'referral_code': '52d6ce'})

    The log file will contain the following log record (inline)::

        {
            "message": "Sign up",
            "time": "2015-09-01T06:06:26.524448",
            "referral_code": "52d6ce"
        }

    """

    json_lib = json

    def format(self, record):
        message = record.getMessage()
        extra = self.extra_from_record(record)
        json_record = self.json_record(message, extra, record)
        return self.to_json(json_record)

    def to_json(self, record):
        """Converts record dict to a JSON string.

        Override this method to change the way dict is converted to JSON.

        """
        return self.json_lib.dumps(record)

    def extra_from_record(self, record):
        """Returns `extra` dict you passed to logger.

        The `extra` keyword argument is used to populate the `__dict__` of
        the `LogRecord`.

        """
        return {
            attr_name: record.__dict__[attr_name]
            for attr_name in record.__dict__
            if attr_name not in BUILTIN_ATTRS
        }

    def json_record(self, message, extra, record):
        """Prepares a JSON payload which will be logged.

        Override this method to change JSON log format.

        :param message: Log message, e.g., `logger.info(msg='Sign up')`.
        :param extra: Dictionary that was passed as `extra` param
            `logger.info('Sign up', extra={'referral_code': '52d6ce'})`.
        :param record: `LogRecord` we got from `JSONFormatter.format()`.
        :return: Dictionary which will be passed to JSON lib.

        """
        extra['level'] = record.levelname
        extra['message'] = message
        if 'time' not in extra:
            extra['time'] = time.time()

        if record.exc_info:
            extra['exc_info'] = self.formatException(record.exc_info)

        return extra


