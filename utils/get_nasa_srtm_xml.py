import os
import requests
from requests.auth import HTTPBasicAuth

username = 'rice2001'
password = 'Albert2001'

auth = HTTPBasicAuth(username, password)
dim = 3
path = 'D:\\wxtofly\\SRTM'


if dim == 1:
    folder = 'SRTMGL1.003'
    filename_suffix = '.SRTMGL1.hgt.zip.xml'
elif dim == 3:
    folder = 'SRTMGL3.003'
    filename_suffix = '.SRTMGL3.hgt.zip.xml'
else:
    raise Exception('Invalid SRTM dimension')

base_url = 'https://e4ftl01.cr.usgs.gov/MEASURES/' + folder + '/2000.02.11/'
path = os.path.join(path, folder)

if not os.path.exists(path):
    os.mkdir(path)

s = requests.Session()

def get_group_folder(lat, lon):
    if lat < 0:
        folder_name = 'S'
    else:
        folder_name = 'N'

    folder_name += format(abs(lat // 10), '02d')

    if lon < 0:
        folder_name += 'W'
    else:
        folder_name += 'E'

    folder_name += format(abs(lon // 10), '02d')

    return folder_name

def download_xml(url, filename, file_path):
    r = s.get(url, allow_redirects=False, stream=False)
    if r.status_code == 302:
        print("--> Authenticating")
        r.next.prepare_auth(auth=auth)
        r = s.send(r.next, stream=False)
    if r.status_code == 200:
        print("--> 200: {0}".format(filename))
        with open(file_path, 'wt+') as f:
            f.write(r.text)
    else:
        print("--> {0}".format(r.status_code))
        with open(file_path + ".{0}".format(r.status_code), 'wt+') as f:
            f.write(url)

def process_loc(lat, lon, filename):
    filename += filename_suffix
    url = base_url + filename

    group_path = os.path.join(path, get_group_folder(lat, lon))
    if not os.path.exists(group_path):
        os.mkdir(group_path)

    file_path = os.path.join(group_path, filename)
    file_path_404 = os.path.join(group_path, filename + '.404')

    if not os.path.exists(file_path) and not os.path.exists(file_path_404):
        print(url)

        attempts = 3
        while attempts > 0:
            try:
                attempts -= 1
                download_xml(url, filename, file_path)
                break
            except:
                if attempts == 0:
                    pass
                s = requests.Session()

def get_filename_lat(lat):
        if lat < 0:
            return 'S' + format(abs(lat), '02d')
        else:
            return 'N' + format(lat, '02d')

def get_filename_lon(lon):
        if lon < 0:
            return 'W' + format(abs(lon), '03d')
        else:
            return 'E' + format(lon, '03d')

# https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/N00E006.SRTMGL1.hgt.zip.xml
for lon in range (-180, 180):
    for lat in range (-90, 90):

        process_loc(lat, lon, get_filename_lat(lat) + get_filename_lon(lon))

        if lat == 0:
            process_loc(lat, lon, 'S00' + get_filename_lon(lon))
        if lon == 0:
            process_loc(lat, lon, get_filename_lat(lat) + 'W000')
        if lat == 0 and lon == 0:
            process_loc(lat, lon, 'S00W000')
