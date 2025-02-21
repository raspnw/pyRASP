from netCDF4 import Dataset

path = "D:\\wxtofly\\v3\\rasp\\test\\wrfout_d02_2019-05-12_120000"

d = Dataset(path, mode='r')

d.close()