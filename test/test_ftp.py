import os
import logging
import datetime
import errno
import glob
import shutil
import time

from rasp.common.ftp import FTPHelper
from rasp.postprocess.publish import configuration as publish_configuration

import wxtofly

if __name__ == '__main__':
    region_name = 'PNW4'
    today = datetime.date.today()

    with FTPHelper(
        publish_configuration.ftp.server,
        publish_configuration.ftp.root_path) as ftp:

        rel_url = "{0}/windgrams".format(region_name)

        if ftp.rel_path_exists(rel_url):
            for dirname in ftp.rel_list_dir(rel_url):
                dir_date = datetime.datetime.strptime(dirname, wxtofly.configuration.upload_date_format).date()
                if dir_date < today:
                    ftp.rel_rmtree("{0}/{1}".format(rel_url, dirname))