import os
import logging
import json

from rasp.postprocess.publish.publishqueue import add_to_queue
from rasp.postprocess.netcdf import netcdf_to_json

import wxtofly


def get_region_path(region_name):
    return "{0}/{1}"

def publish_json(data, local_path, publish_url, logger=wxtofly.get_logger()):
    """Function saves data dictionary as JSON file and publishes the file to remote location

    Arguments:
      data - dictionary to save to JSON file
      local_path - path to save JSON file as
      publish_url - URL location to publish JSON file
    """
    logger.debug("Publishing JSON")
    logger.debug("Local path: {0}".format(local_path))
    logger.debug("URL: {0}".format(publish_url))
    with open(local_path, 'wt+') as f:
        json.dump(data, f, indent=2)
    add_to_queue(local_path, publish_url)


def publish_height_data(region, logger=wxtofly.get_logger()):
    for i in range(1, region.max_dom + 1):
        hgt_json_path = os.path.join(region.static_data_path, "hgt.d{0:02}.json".format(i))
        if not os.path.exists(hgt_json_path):
            netcdf_to_json(
                os.path.join(region.static_data_path, "geo_em.d{0:02}.nc".format(i)),
                hgt_json_path,
                ['HGT_M'],
                decimals=1,
                logger=logging
                )
            add_to_queue(
                hgt_json_path,
                wxtofly.get_configuration().web.get_region_rel_path(region.name, "static/{0}".format(os.path.basename(hgt_json_path)))
                )


def get_domain_polygon_path(projection, e_we, e_sn, decimals=3):
    """Function creates polygon path for a grid

    Arguments:
      projection - grid projection
      e_we - west-east grid dimension
      e_sn - south-north grid dimension
    """
    path = []

    def _add_polygon_point(i, j):
        latlon = projection.corners_ij_to_latlon(i, j)
        path.append([round(latlon[1], decimals), round(latlon[0], decimals)])

    _add_polygon_point(0, 0)

    for i in range(1, e_we):
        _add_polygon_point(i, 0)

    for j in range(0, e_sn):
        _add_polygon_point(e_we - 1, j)

    for i in range(e_we - 1, -1, -1):
        _add_polygon_point(i, e_sn - 1)

    for j in range(e_sn - 1, 0, -1):
        _add_polygon_point(0, j)

    _add_polygon_point(0, 0)
    return path;