import os
import logging
import sys
import datetime
import json

from rasp.modelrun.wps.namelist import WPSNamelist

ns = WPSNamelist('D:\\wxtofly\\v3\\test\\UK12\\namelist.wps')

print(ns.get_grid_bounds(1))
