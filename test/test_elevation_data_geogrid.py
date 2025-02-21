import os
import sys
import logging
import datetime
import errno
import glob
import shutil
import time
import datetime
from pathlib import Path

import rasp
from rasp.region import Region
from rasp.modelrun.wps.namelist import WPSNamelist, create_wps_namelist
from rasp.modelrun.wps.geogrid import run_geogrid
from rasp.modelrun.wps.elevation import ElevationDataConfiguration
import rasp.utils.netcdf

region_name = sys.argv[1]
res = sys.argv[2]

if __name__ == '__main__':

    region = Region(region_name)
    if os.path.exists(region.static_data_path):
        shutil.rmtree(region.static_data_path)
        os.mkdir(region.static_data_path)

    configuration = rasp.modelrun.get_configuration()

    output_path = os.path.join(Region.get_run_base_path(region.name), res)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    wps_namelist = create_wps_namelist(
        region,
        datetime.date.today(),
        output_path)
    for idx, geog_data_res in enumerate(wps_namelist.geogrid.geog_data_res):
        wps_namelist.geogrid.geog_data_res[idx] = wps_namelist.geogrid.geog_data_res[idx] + '+' + res
    wps_namelist.save()

    # run geogrid
    run_geogrid(region, wps_namelist, output_path, output_path)

    res_path = "{0}.{1}".format(region.static_data_path, res)
    if os.path.exists(res_path):
        shutil.rmtree(res_path)

    os.rename(region.static_data_path, res_path)

    for path in Path(res_path).glob('*.nc'):
        rasp.utils.netcdf.netCDF_to_image(path.resolve(), 'HGT_M')
