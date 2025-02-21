import os
import logging
import datetime
import errno
import glob
import shutil
import time

from rasp.postprocess.rasp import list_raspout_files, create_blipspot_json_parallel
from wxtofly.run import configuration as wxtofly_configuration
from rasp.region import Region
from rasp.postprocess.publish.publishqueue import add_to_queue

if __name__ == '__main__':

    grid_id = 1
    region = Region('PNW4')

    add_to_queue(os.path.join(region.base_path, 'blipspots'), '/PNW4/blipspot')

