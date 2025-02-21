import os
import logging
import time
import hashlib
import signal
import shutil
from threading import Event

def folder_size(path):
    """ function calculates folder size """
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += folder_size(entry.path)
    return total

def cleanup_path(path, max_age_hours, logger=logging.getLogger()):
    if os.path.exists(path):
        logger.debug("Removing files older than {0} hours from {1}".format(max_age_hours, path))
        min_time = time.time() - max_age_hours * 3600

        for dir_entry in os.scandir(path):
            if dir_entry.stat(follow_symlinks=False).st_mtime < min_time:
                logger.debug("Removing {0}".format(dir_entry.path))
                if dir_entry.is_symlink():
                    os.unlink(dir_entry.path)
                elif dir_entry.is_file():
                    os.remove(dir_entry.path)
                elif dir_entry.is_dir():
                    shutil.rmtree(dir_entry.path)

def  remove_all_files(path, logger=logging.getLogger()):
    """ function deletes all files in a directory """
    if os.path.exists(path):
        logger.debug("Removing all files from {0}".format(path))
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks = False):
                logger.debug("Deleting {0}".format(entry.name))
                os.remove(entry.path)
            if entry.is_symlink():
                logger.debug("Deleting symlink {0}".format(entry.name))
                os.remove(entry.path)

def get_file_hash(path, additional_data=None):
    """ function calcutales a SHA1 hash for a file and returns it as HEX string  """
    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    sha1 = hashlib.sha1()

    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    if not additional_data is None:
        sha1.update(additional_data)

    return sha1.hexdigest()

def create_file_symlink(src_path, link_path, logger=logging.getLogger()):
    """ function creates a symlink  """
    if os.path.islink(link_path):
        os.unlink(link_path)
    if os.path.isfile(link_path):
        os.remove(link_path)
    logger.debug("Creating symlink: {0} -> {1}".format(link_path, src_path))
    os.symlink(src_path, link_path, False)

wait_event = Event()

def set_event(signo, _frame, logger=logging.getLogger()):
    # signal handler used during wait
    # when signal is received the program will exit
    global wait_event
    logger.debug("Interrupted by {0}. Exiting".format(signo))
    exit()

def wait(seconds, logger=logging.getLogger()):
    """ 
    function blocks execution for seconds
    if use send a signal during the wait for example 
    hitting CTRL+C, the program will exit
    """
    global wait_event
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), set_event);
    logger.debug("Wait for {0} seconds".format(seconds))
    wait_event.wait(seconds)