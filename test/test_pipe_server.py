import os
import logging
import subprocess
import time

import rasp

fifo_name = 'rasp_publish'
if os.path.exists(fifo_name):
    logger.debug("Exitting - pipe already exists")
    exit()

logger.debug("Create pipe")
os.mkfifo(fifo_name)

# read data
buffer_size = 1024
fd = os.open(fifo_name, os.O_RDONLY | os.O_NONBLOCK)
while True:
    try:
        s = os.read(fd, buffer_size) # buffer size may need tweaking
        print(len(s))
        if s != b'':
            print(s)
    except BlockingIOError as e:
        # logger.debug("No data")
        pass

    logger.debug("No data")
    time.sleep(1)

os.close(fd)