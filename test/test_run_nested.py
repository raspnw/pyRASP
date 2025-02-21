import os
import logging
import sys
import datetime

from rasp.modelrun import configuration
from rasp.modelrun.run import run_model
from rasp.region import Region
from rasp.common.logging import start_file_log


if len(sys.argv) <= 1:
    region_name = 'PANOCHENEST'
else:
    region_name = sys.argv[1]

if __name__ == '__main__':

    region = Region(region_name)

    init_date_utc = datetime.date(2019, 5, 18)
    init_hour_utc = 18
    forecast_day = 0
    run_output_path = Region.get_run_output_path(region.name, init_date_utc, init_hour_utc, forecast_day)
    run_model(region, init_date_utc, init_hour_utc, forecast_day, run_output_path, nested=True, parent_output_path='/home/jiri/wx3/PANOCHE/run/20190518.18z+0')

    pass