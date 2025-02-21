import requests
from requests.auth import HTTPBasicAuth

username = 'wxtofly'
password = 'TigerMt56&'

auth = HTTPBasicAuth(username, password)
path = 'D:\\wxtofly\\v3\\rasp\\test\\N47W122.SRTMGL1.hgt.zip'
url = 'https://e4ftl01.cr.usgs.gov/MODV6_Dal_D/SRTM/SRTMGL1.003/2000.02.11/N47W122.SRTMGL1.hgt.zip'
with requests.Session() as s:
    r = s.get(url, allow_redirects=False)
    r.next.prepare_auth(auth=auth)
    r = s.send(r.next, stream=True)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in r:
                f.write(chunk)