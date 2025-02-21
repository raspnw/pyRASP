import os
import logging
import sys
import datetime
import json

from rasp.postprocess.wrf import WRFOUTFile

wrf_file = WRFOUTFile('D:\\wxtofly\\v3\\rasp\\test\\wrfout_d01_2019-05-12_120000')
wrf_file.domain_id += 1
print(wrf_file.get_filename())