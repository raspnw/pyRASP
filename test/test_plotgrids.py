import os
import sys
import logging

import rasp
from rasp.postprocess.ncl.plotgrids import plot_grids
from rasp.region import Region

if len(sys.argv) <= 1:
    region_name = 'PANOCHE'
else:
    region_name = sys.argv[1]

plot_grids(
    os.path.join(Region.get_region_path(region_name), 'namelist.wps'),
    os.path.join(Region.get_region_path(region_name), 'domains.png'))

plot_grids(
    os.path.join(Region.get_region_path(region_name), 'namelist.wps'),
    os.path.join(Region.get_region_path(region_name), 'domains.svg'),
    type="svg")