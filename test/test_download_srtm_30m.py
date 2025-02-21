from rasp.common.download import download_file

username = 'wxtofly'
password = 'TigerMt56&'
path = 'D:\\wxtofly\\v3\\rasp\\test\\N47W122.SRTMGL1.hgt.zip'
url = 'https://e4ftl01.cr.usgs.gov/MODV6_Dal_D/SRTM/SRTMGL1.003/2000.02.11/N47W122.SRTMGL1.hgt.zip'

download_file(url, path, username=username, password=password)