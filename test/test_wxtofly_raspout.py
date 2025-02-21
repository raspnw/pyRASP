import os
import logging
import datetime
import errno
import glob
import shutil
import time
import json

from wxtofly.run import configuration as wxtofly_configuration
from rasp.region import Region
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.postprocess.wrf import list_wrfout_files, create_raspout_files

if __name__ == '__main__':

    region_name = 'PNW4'
    region = Region(region_name)

    init_date_utc = datetime.date(2018, 6, 22)
    init_hour_utc = 12
    forecast_day = 0
    forecast_date = init_date_utc
    run_output_path = Region.get_run_output_path(region.name, init_date_utc, init_hour_utc, forecast_day)
    raspout_output_path = os.path.join(run_output_path, 'rasp')

    wps_namelist = WPSNamelist(region.template_wps_namelist_path)

    for domain_id in range(1, wps_namelist.share.max_dom + 1):
        wrfout_files = list_wrfout_files(run_output_path, domain_id, region.get_forecast_start_datetime_utc(forecast_date), region.get_forecast_end_datetime_utc(forecast_date))
        create_raspout_files(wrfout_files, wxtofly_configuration.postprocessing.variables, raspout_output_path)

