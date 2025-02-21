import os
import logging
import sys
import datetime

from rasp.region import Region
from rasp.modelrun.wrf.wrf import run_wrf

if len(sys.argv) <= 1:
    region_name = 'PANOCHE'
else:
    region_name = sys.argv[1]

if __name__ == '__main__':

    init_date_utc = datetime.datetime.utcnow().date() - datetime.timedelta(days = 1)
    init_hour_utc = 0
    forecast_day = 0
    run_output_path = Region.get_run_output_path(region.name, init_date_utc, init_hour_utc, forecast_day)

    run_wrf(run_output_path, run_output_path)