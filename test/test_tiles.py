import os
import logging
import datetime
import errno
import glob
import shutil
import time

import rasp.postprocess
from rasp.postprocess.rasp import RASPPostProcess
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.region import Region
from rasp.modelrun.run import run_model

if __name__ == '__main__':
    region = rasp.region.Region('PANOCHE')
    wps_namelist = WPSNamelist(region.template_wps_namelist_path)

    init_date_utc = datetime.datetime.utcnow().date() - datetime.timedelta(days = 1)
    init_hour_utc = 0
    forecast_day = 0
    run_output_path = Region.get_run_output_path(region.name, init_date_utc, init_hour_utc, forecast_day)

    tiles_output_path = os.path.join(run_output_path, 'tiles')

    rasp.postprocess.configuration.tiles_zoom_min = 8
    rasp.postprocess.configuration.tiles_zoom_max = 8

    rasp_postprocess = RASPPostProcess(region, os.path.join(run_output_path, 'rasp'))
    rasp_postprocess.create_tiles(tiles_static_data_path, tiles_output_path)

