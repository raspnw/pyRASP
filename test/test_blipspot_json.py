import os
import logging
import datetime
import errno
import glob
import shutil
import time

from wxtofly.blipspot import create_blipspot_json, create_blipspot_json_parallel
from rasp.postprocess.rasp import list_raspout_files
from wxtofly.run import configuration as wxtofly_configuration
from rasp.region import Region

if __name__ == '__main__':

    grid_id = 1
    region = Region('PNW4')

    raspout_files = list_raspout_files(os.path.join(region.base_path, 'rasp'), grid_id)
    create_blipspot_json(raspout_files, region.local_tzinfo, wxtofly_configuration.postprocessing.variables, os.path.join(region.base_path, 'blipspots'))
