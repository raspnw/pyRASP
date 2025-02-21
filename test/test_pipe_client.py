import os
import logging
import subprocess
import time
import sys
import psutil

import rasp

fifo_name = 'rasp_publish'

if os.path.exists(fifo_name):
    #fifo = open(fifo_name, "w")
    #fifo.write("Another message from the sender!\n")
    #fifo.close()
    #exit()
    os.remove(fifo_name)

server_script = os.path.join(os.path.dirname(sys.argv[0]), 'test_pipe_server.py')
logger.debug("Starting server {0} {1}".format(sys.executable, server_script))

args = None
if sys.stdout.isatty():
    args = [
        psutil.Process(os.getpid()).parent().parent().name(),
        '-e',
        sys.executable,
        server_script
        ]
else:
    args = [
        sys.executable,
        server_script
        ]

subprocess.Popen(args)
# wait for pipe
while True:
    if os.path.exists(fifo_name):
        break
    logger.debug("Waiting for pipe")
    time.sleep(1)

logger.debug("Sending message")
fifo = open(fifo_name, "w")
fifo.write("Message from the sender!")
fifo.close()
fifo = open(fifo_name, "w")
fifo.write("Message from the sender!")
fifo.close()
fifo = open(fifo_name, "w")
fifo.write("Message from the sender!")
fifo.close()

