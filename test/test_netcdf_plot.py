import sys
import rasp.utils.netcdf

path = sys.argv[1]
rasp.utils.netcdf.netCDF_to_image(path, 'HGT_M')
