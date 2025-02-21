import os
import logging
import datetime
import errno
import glob
import shutil
import time

from rasp.postprocess.publish.publishqueue import publish_start, init_publishing
from rasp.postprocess.publish.publishserver import send_signal

if __name__ == '__main__':
    init_publishing()
    publish_start()
