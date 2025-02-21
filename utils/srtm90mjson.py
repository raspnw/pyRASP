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
    
    # An example.


    with open(os.path.join(os.path.dirname(__file__), 'dwtkns.json'), 'rt') as f:
        topology = json.load(f)
    
    scale = topology['transform']['scale']
    translate = topology['transform']['translate']

    srtm_data = {
        'baseurl': 'http://srtm.csi.cgiar.org/SRT-ZIP/SRTM_V41/SRTM_Data_GeoTiff/',
        'tiles': []}

    for tile in topology['objects']['srtm']['geometries']:

        srtm = {}
        srtm['name'] = tile['properties']['filename']
        srtm['bounds'] = {}

        print(tile['properties']['filename'])
        #http://srtm.csi.cgiar.org/SRT-ZIP/SRTM_V41/SRTM_Data_GeoTiff/srtm_33_09.zip

        s = geometry(tile, topology['arcs'], scale, translate)

        
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


    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rasp', 'data', 'srtm90m.json'), 'wt') as outfile:
        json.dump(srtm_data, outfile, indent=1)
