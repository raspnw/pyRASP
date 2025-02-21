import os
import logging
import sys
import datetime

from rasp.modelrun import configuration
from rasp.modelrun.run import run_model
from rasp.region import Region
from rasp.common.logging import start_file_log


if len(sys.argv) <= 1:
    region_name = 'PANOCHE'
else:
    region_name = sys.argv[1]

if __name__ == '__main__':

    region = Region(region_name)

    init_date_utc = datetime.datetime.utcnow().date() - datetime.timedelta(days = 1)
    init_hour_utc = 0
    forecast_day = 0
    run_output_path = Region.get_run_output_path(region.name, init_date_utc, init_hour_utc, forecast_day)
    run_model(region, init_date_utc, init_hour_utc, forecast_day, run_output_path)

    pass