import os
import glob
import xml.etree.ElementTree as ET
import json

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

path = os.path.join(path, folder)
search_path = os.path.join(path, '**', '*.xml')

features = []

for filename in glob.iglob(search_path, recursive=True):
    print(filename)
    tree = ET.parse(filename)
    root = tree.getroot()

    feature = {'type': 'Feature'}

    for rect in root.iter('BoundingRectangle'):
        west = float(rect.find('WestBoundingCoordinate').text)
        north = float(rect.find('NorthBoundingCoordinate').text)
        east = float(rect.find('EastBoundingCoordinate').text)
        south = float(rect.find('SouthBoundingCoordinate').text)
        feature['geometry'] = {
            'type': 'Polygon',
            'coordinates': [[ 
                [west, north],
                [west, south],
                [east, south],
                [east, north],
                [west, north]]]
        }
        break

    for filename_element in root.iter('DistributedFileName'):
        feature['properties'] = {
            'filename': os.path.basename(filename_element.text)
        }
        break

    features.append(feature)

geo_json = {
    'type': 'FeatureCollection',
    'features': features,
}

with open(os.path.join(path, '{0}.json'.format(folder)), 'wt+') as outfile:
    json.dump(geo_json, outfile)
