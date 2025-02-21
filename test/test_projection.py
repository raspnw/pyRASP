import os
import sys

import rasp
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.visualization.projection import WPSProjection
from rasp.region import Region

if len(sys.argv) <= 1:
    region_name = 'PANOCHE'
else:
    region_name = sys.argv[1]

wps_namelist = WPSNamelist(os.path.join(Region.get_region_path(region_name), 'namelist.wps'))
wps_proj = WPSProjection(wps_namelist)

i, j = wps_proj.to_parent_corners_ij(0, 0, 2)
print("i:{0}, j:{1}".format(i, j))
i, j = wps_proj.to_child_corners_ij(i, j, 2)
print("i:{0}, j:{1}".format(i, j))

i, j = wps_proj.to_moad_corners_ij(0, 0, 2)
print("i:{0}, j:{1}".format(i, j))
i, j = wps_proj.from_moad_corners_ij(i, j, 2)
print("i:{0}, j:{1}".format(i, j))
 

def mass_ij_to_latlon(i, j, grid = 1, ref_lat = 0, ref_lon = 0):
    lat, lon = wps_proj.mass_ij_to_latlon(i, j, grid)
    print("i:{0}, j:{1} = {2}, {3}".format(i, j, lat, lon))
    if ref_lat != 0 and ref_lon != 0:
        if round(ref_lat, 3) == round(lat, 3) and round(ref_lon, 3) == round(lon, 3):
            print("match")
        else:
            raise ArithmeticError("lat, lot doesn't match")
    x, y = wps_proj.latlon_to_mass_ij(lat, lon, grid)
    print("i:{0}, j:{1}".format(x, y))
    if x != i or y != j:
        raise ArithmeticError("i, j doesn't match")

def corners_ij_to_latlon(i, j, grid = 1, ref_lat = 0, ref_lon = 0):
    lat, lon = wps_proj.corners_ij_to_latlon(i, j, grid)
    print("i:{0}, j:{1} = {2}, {3}".format(i, j, lat, lon))
    if ref_lat != 0 and ref_lon != 0:
        if round(ref_lat, 3) == round(lat, 3) and round(ref_lon, 3) == round(lon, 3):
            print("match")
        else:
            raise ArithmeticError("lat, lot doesn't match")
    x, y = wps_proj.latlon_to_corners_ij(lat, lon, grid)
    print("i:{0}, j:{1}".format(x, y))
    if x != i or y != j:
        raise ArithmeticError("i, j doesn't match")

print("d01")
corners_ij_to_latlon(0, 0, 1, 33.1272, -121.446)
corners_ij_to_latlon(0, wps_namelist.geogrid.e_sn[0] - 1, 1)
corners_ij_to_latlon(wps_namelist.geogrid.e_we[0] - 1, wps_namelist.geogrid.e_sn[0] - 1, 1, 39.8792, -119.881)
corners_ij_to_latlon(wps_namelist.geogrid.e_we[0] - 1, 0, 1)

mass_ij_to_latlon(0, 0, 1, 33.20075, -121.4239)

print("d02")
corners_ij_to_latlon(0, 0, 2, 35.1163, -121.228)
corners_ij_to_latlon(0, wps_namelist.geogrid.e_sn[1] - 1, 2, 37.228, -122.832)
corners_ij_to_latlon(wps_namelist.geogrid.e_we[1] - 1, wps_namelist.geogrid.e_sn[1] - 1, 2, 38.1832, -120.853)
corners_ij_to_latlon(wps_namelist.geogrid.e_we[1] - 1, 0, 2, 36.0416, -119.287)
