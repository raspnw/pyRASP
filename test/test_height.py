import os
import logging
import sys

from rasp.postprocess.netcdf import netcdf_to_json
from rasp.region import Region

region = Region('CHELAN')
for i in range(1, region.max_dom + 1):
    netcdf_to_json(
        os.path.join(region.static_data_path, "geo_em.d{0:02}.nc".format(i)),
        os.path.join(region.static_data_path, "hgt.d{0:02}.json".format(i)),
        ['HGT_M'],
        decimals=1
        )
