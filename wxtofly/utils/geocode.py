import os
import logging
import json

from shapely.geometry import mapping, shape
from shapely.prepared import prep
from shapely.geometry import Point

class GeoCode(object):
    def __init__(self, geojson_path, name_property = 'NAME'):
        with open(geojson_path, 'rt') as f:
            self.geojson = json.load(f)

        self.shapes = {}

        for feature in self.geojson["features"]:
            geometry = feature["geometry"]
            if not name_property in feature["properties"]:
                raise GeoCodeError("Feature does not contain property {0} in file {1}".format(name_property, geojson_path))
            name = feature["properties"][name_property]
            self.shapes[name] = prep(shape(geometry))

    def get_name(self, lat, lon, default = None):
        point = Point(lon, lat)
        for name, shape in self.shapes.items():
            if shape.contains(point):
                return name
        return default