import os
import logging
import datetime
import errno
import glob
import shutil
import time

from rasp.postprocess.rasp import list_raspout_files, create_rasp_json_files
from wxtofly.run import configuration as wxtofly_configuration

if __name__ == '__main__':

    raspout_files = list_raspout_files('/home/jiri/wx3/PNW4/run/20180622.12z+0/rasp', 1)
    create_rasp_json_files(raspout_files, wxtofly_configuration.postprocessing.variables, '/home/jiri/wx3/PNW4/run/20180622.12z+0/json')

