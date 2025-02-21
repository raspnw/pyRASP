import os
import json
import sys

current_path = os.path.dirname(__file__)
input_file_path = os.path.join(current_path, 'alos.txt')
output_file_path = os.path.join(current_path, 'AW3D30.json')

features = []

with open(input_file_path, 'rt') as f:
    for line in f:
        line = line.rstrip()
        print(line)

        feature = {'type': 'Feature'}

        names = line.split('/')

        if len(names) < 1:
            continue

        filename = names[len(names) - 1]

        if not filename.endswith('.tar.gz'):
            continue

        if '_' in filename:
            continue

        if filename[0] == 'S':
            lat = -1
        elif filename[0] == 'N':
            lat = 1
        else:
            raise Exception("Invalid filename")

        lat = lat * int(filename[1:4])

        if filename[4] == 'W':
            lon = -1
        elif filename[4] == 'E':
            lon = 1
        else:
            raise Exception("Invalid filename")

        lon = lon * int(filename[5:8])

        west = lon
        north = lat + 1
        east = lon + 1
        south = lat
        feature['geometry'] = {
            'type': 'Polygon',
            'coordinates': [[ 
                [west, north],
                [west, south],
                [east, south],
                [east, north],
                [west, north]]]
            }

        feature['properties'] = {
            'filename': filename,
            'path': line[0:-len(filename)]
        }

        features.append(feature)

print("total features: {0}".format(len(features)))
geo_json = {
    'type': 'FeatureCollection',
    'features': features,
}

with open(output_file_path, 'wt+') as f:
    json.dump(geo_json, f)