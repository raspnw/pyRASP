import os
import numpy
import re

import rasp

class VariableColorMap(object):
    
    ncl_colormap_rainbows = {}
    ncl_colormap_rgb = None
    logger = rasp.postprocess.get_logger()

    def get_image_data(rainbow):
        image = numpy.zeros([256, 256, 4], dtype=numpy.uint8)
        step = int(256 / len(rainbow))
        start = 0
        for c in rainbow:
            image[:,start:start + step] = c
            start += step
        return image

    def load_ncl_rgb(path):
        logger.debug("Loading RGB file {0}".format(path))
        rgb = []
        for line in open(path):
            line = line.strip()
            match = re.match( r'^\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)', line, re.M|re.I)
            if match:
                r = int(match.group(1))
                g = int(match.group(2))
                b = int(match.group(3))
                rgb.append([r, g, b])
        return rgb

    def get_ncl_colormap_rainbow(size):
        configuration = rasp.postprocess.get_configuration()
        if VariableColorMap.ncl_colormap_rgb is None:
            path = os.path.join(configuration.ncl.colormap_path, configuration.tiles.ncl_colormap)
            VariableColorMap.ncl_colormap_rgb = VariableColorMap.load_ncl_rgb(path)

        if not str(size) in VariableColorMap.ncl_colormap_rainbows:
            step = (len(VariableColorMap.ncl_colormap_rgb) - 1) / (size - 1)
            rainbow = []
            for i in range(0, size):
                c = VariableColorMap.ncl_colormap_rgb[int(round(i * step))]
                rainbow.append([c[0], c[1], c[2], 255])
            # insert transparent black for values below scale min
            rainbow.insert(0, [0, 0, 0, 0])
            VariableColorMap.ncl_colormap_rainbows[str(size)] = rainbow
        return VariableColorMap.ncl_colormap_rainbows[str(size)]
