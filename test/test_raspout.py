import os
import logging
import sys
import datetime

from rasp.region import Region
from rasp.modelrun.run import run_model
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.postprocess.wrf import WRFPostProcess

if len(sys.argv) <= 1:
    region_name = 'PANOCHE'
else:
    region_name = sys.argv[1]

if __name__ == '__main__':

    region = Region(region_name)

    init_date_utc = datetime.date(2018, 6, 22)
    init_hour_utc = 12
    forecast_day = 0
    run_output_path = Region.get_run_output_path(region.name, init_date_utc, init_hour_utc, forecast_day)

    wps_namelist = WPSNamelist(region.template_wps_namelist_path)

    raspout_output_path = os.path.join(run_output_path, 'rasp')

    # all variables
    region.configuration.postprocessing.variables = [
        "rain",
        "zblcl",
        "zblcldif",
        "zblclmask",
        #"xbl",
        #"boxmax",
        "zsfclcl",
        "zsfclcldif",
        "zsfclclmask",
        "cloudsuck",
        "aboveblicw",
        "sfcshf",
        "hbl",
        "blcloudpct",
        "blicw",
        "bltopvariab",
        "blwindshear",
        "wstar",
        "experimental2",
        "experimental1",
        "hwcrit",
        "hglider",
        "uvmet",
        "bltopwind",
        "blwind",
        "bsratio",
        "wblmaxmin",
        "zwblmaxmin",
        "mslpress",
        "cape",
        "sfctemp",
        "sfcdewpt",
        "dbl",
        "sfcsun",
        "sfcsunpct",
        "dwcrit",
        "blcwbase",
        # WRF=<wrf_parameter>
        # WINDnnn
        # PRESSnnn
        # stars
        "wstar_bsratio",
        "press850"]

    wrf = WRFPostProcess(region, wps_namelist.share.max_dom, init_date, run_output_path)
    wrf.create_raspout_files(raspout_output_path)

    pass