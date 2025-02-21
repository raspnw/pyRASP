import os
import logging
import sys
import datetime

from rasp.region import Region, RegionSite
from rasp.modelrun.run import run_model
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.postprocess.wrf import WRFPostProcess

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
    
    wps_namelist = WPSNamelist(region.template_wps_namelist_path)

    plot_output_path = os.path.join(run_output_path, 'plot')

    # all variables
    region.configuration.postprocessing.variables = []
    region.configuration.postprocessing.ncl.plot_soundings = True
    if len(region.configuration.postprocessing.sites) == 0:
        region.configuration.postprocessing.sites.append(RegionSite('center', wps_namelist.geogrid.ref_lat, wps_namelist.geogrid.ref_lon))

    wrf = WRFPostProcess(region, wps_namelist.share.max_dom, init_date, run_output_path)
    wrf.plot_variables(plot_output_path)

    pass