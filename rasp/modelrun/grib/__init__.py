import os
import logging

import rasp
from rasp.common.system import cleanup_path

grib_download_logger = None

def cleanup_grib_download_folder(path):
    configuration = rasp.modelrun.get_configuration()
    if configuration.grib.max_age_hours > 0:
        cleanup_path(path, configuration.grib.max_age_hours)

def get_logger():
    global grib_download_logger
    if grib_download_logger == None:
        grib_download_logger = logging.getLogger('rasp.grib_download')
    return grib_download_logger
