import os
import logging
import sys
import datetime
import json

from rasp.postprocess.wrf import WRFOUTFile
from rasp.modelrun.wps.namelist import WPSNamelist

wrf_file = WRFOUTFile('D:\\wxtofly\\v3\\rasp\\test\\wrfout_d01_2019-05-12_120000')
bounds = wrf_file.get_staggered_bounds()

print(bounds)
print(wrf_file.get_attributes())

with open(os.path.join(os.path.dirname(__file__), 'wrf.json'), 'wt+') as f:
    json.dump(wrf_file.get_attributes(), f, indent=2)

ns = WPSNamelist('D:\\wxtofly\\v3\\WA4\\namelist.wps')
print(ns.get_grid_bounds(1))

