import os
import sys
import logging
import datetime
import errno
import glob
import shutil
import time

import rasp
from rasp.region import Region
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.modelrun.wps.geogrid import prep_geogrid_elevation_data
from rasp.modelrun.wps.elevation import ElevationDataConfiguration

if len(sys.argv) <= 1:
    region_name = 'PANOCHE'
else:
    region_name = sys.argv[1]

if __name__ == '__main__':

    region = Region(region_name)
    configuration = rasp.modelrun.get_configuration()
    geogrid_table_path = os.path.join(configuration.wps.geogrid_tables_path, "GEOGRID.TBL.{0}".format(region.wps.share.wrf_core))

    for res in ElevationDataConfiguration.get_names():
        wps_namelist = WPSNamelist(region.template_wps_namelist_path)
        print(res)
        for idx, geog_data_res in enumerate(wps_namelist.geogrid.geog_data_res):
            wps_namelist.geogrid.geog_data_res[idx] = wps_namelist.geogrid.geog_data_res[idx] + '+' + res
        prep_geogrid_elevation_data(region, wps_namelist, geogrid_table_path)