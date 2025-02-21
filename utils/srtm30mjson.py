""" srtmjson.py

converts world.json tile coordinates from 
https://github.com/dwtkns/srtm-tile-grabber
to lat/lon coordinates

Original code:
Author: Sean Gillies (https://github.com/sgillies)

"""
import os
import json
import pprint
from itertools import chain

if __name__ == "__main__":
    
    # An example.


    with open(os.path.join(os.path.dirname(__file__), 'srtm30m_bounding_boxes.json'), 'rt') as f:
        topology = json.load(f)
    
    srtm_data = {
        'baseurl': 'https://e4ftl01.cr.usgs.gov//MODV6_Dal_D/SRTM/SRTMGL1.003/2000.02.11/',
        'username': '[REQUIRED]',
        'password': '[REQUIRED]',
        'tiles': []}

    for tile in topology['features']:

        srtm = {}
        filename = tile['properties']['dataFile']
        srtm['name'] = filename[:-4]
        srtm['bounds'] = {}

        print(srtm['name'])

        s = tile['geometry']

        
        if len(s['coordinates'][0]) != 5:
            raise ValueError("Invalid number of polygon coordinates")
        if s['coordinates'][0][0][0] != s['coordinates'][0][4][0] or s['coordinates'][0][0][1] != s['coordinates'][0][4][1]:
            raise ValueError("End point is not equal start point")

        lats = [p[1] for p in s['coordinates'][0]]
        lons = [p[0] for p in s['coordinates'][0]]

        srtm['bounds']['north'] = max(lats)
        srtm['bounds']['south'] = min(lats)
        srtm['bounds']['east'] = max(lons)
        srtm['bounds']['west'] = min(lons)

        pprint.pprint(s)

        srtm_data['tiles'].append(srtm)


    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rasp', 'data', 'srtm30m.json'), 'wt') as outfile:
        json.dump(srtm_data, outfile, indent=1)
