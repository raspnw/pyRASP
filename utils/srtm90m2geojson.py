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

def rel2abs(arc, scale=None, translate=None):
    """Yields absolute coordinate tuples from a delta-encoded arc.

    If either the scale or translate parameter evaluate to False, yield the
    arc coordinates with no transformation."""
    if scale and translate:
        a, b = 0, 0
        for ax, bx in arc:
            a += ax
            b += bx
            yield scale[0]*a + translate[0], scale[1]*b + translate[1]
    else:
        for x, y in arc:
            yield x, y

def coordinates(arcs, topology_arcs, scale=None, translate=None):
    """Return GeoJSON coordinates for the sequence(s) of arcs.
    
    The arcs parameter may be a sequence of ints, each the index of a
    coordinate sequence within topology_arcs
    within the entire topology -- describing a line string, a sequence of 
    such sequences -- describing a polygon, or a sequence of polygon arcs.
    
    The topology_arcs parameter is a list of the shared, absolute or
    delta-encoded arcs in the dataset.

    The scale and translate parameters are used to convert from delta-encoded
    to absolute coordinates. They are 2-tuples and are usually provided by
    a TopoJSON dataset. 
    """
    if isinstance(arcs[0], int):
        coords = [
            list(
                rel2abs(
                    topology_arcs[arc if arc >= 0 else ~arc],
                    scale, 
                    translate )
                 )[::arc >= 0 or -1][i > 0:] \
            for i, arc in enumerate(arcs) ]
        return list(chain.from_iterable(coords))
    elif isinstance(arcs[0], (list, tuple)):
        return list(
            coordinates(arc, topology_arcs, scale, translate) for arc in arcs)
    else:
        raise ValueError("Invalid input %s", arcs)

def geometry(obj, topology_arcs, scale=None, translate=None):
    """Converts a topology object to a geometry object.
    
    The topology object is a dict with 'type' and 'arcs' items, such as
    {'type': "LineString", 'arcs': [0, 1, 2]}.

    See the coordinates() function for a description of the other three
    parameters.
    """
    return {
        "type": obj['type'], 
        "coordinates": coordinates(
            obj['arcs'], topology_arcs, scale, translate )}


if __name__ == "__main__":
    """
    {
        "type":"FeatureCollection",
        "features":[
            {
                "type":"Feature",
                "geometry":{
                    "type":"Polygon",
                    "coordinates":[[
                        [5.99972222,-0.00027778],
                        [7.00027778,-0.00027778],
                        [7.00027778,1.00027778],
                        [5.99972222,1.00027778],
                        [5.99972222,-0.00027778]
                    ]]
                },
                "properties":{
                    "dataFile":"N00E006.SRTMGL1.hgt.zip"
                 }
            }
        ]
    }
    """

    with open(os.path.join(os.path.dirname(__file__), 'world.json'), 'rt') as f:
        topology = json.load(f)
    
    scale = topology['transform']['scale']
    translate = topology['transform']['translate']

    srtm_data = {
        'type': 'FeatureCollection',
        'features': []}

    for tile in topology['objects']['srtm']['geometries']:

        srtm = {}
        srtm['type'] = 'Feature'
        srtm['properties'] = {
            'filename': tile['properties']['filename']}

        print(tile['properties']['filename'])
        #http://srtm.csi.cgiar.org/SRT-ZIP/SRTM_V41/SRTM_Data_GeoTiff/srtm_33_09.zip

        srtm['geometry'] = geometry(tile, topology['arcs'], scale, translate)
        
        srtm_data['features'].append(srtm)


    with open(os.path.join(os.path.dirname(__file__), 'srtm90m.geo.json'), 'wt+') as outfile:
        json.dump(srtm_data, outfile, indent=1)
