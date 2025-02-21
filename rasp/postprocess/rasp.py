import os
import shutil
import json
import glob
import time
import datetime
import pytz
import re
from netCDF4 import Dataset

import rasp
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.postprocess.netcdf import netcdf_to_json

class RASPOUTFile(object):

    raspout_datetime_format = "%Y-%m-%d_%H%M"
    raspout_filename_format = "raspout_d{domain_id:02d}_{raspout_datetime}.nc"

    def __init__(self, path):

        self.logger = rasp.postprocess.get_logger()
        self.path = path
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, "RASPOUT file {0} not found".format(path), path)

        self.filename = os.path.basename(path)
        self.logger.debug(self.filename)

        match = re.match( r'^raspout_d([0-9]{2})_', self.filename)
        self.domain_id = int(match.group(1))

        self.datetime = datetime.datetime.strptime(self.filename, RASPOUTFile.raspout_filename_format.format(domain_id = self.domain_id, raspout_datetime = RASPOUTFile.raspout_datetime_format))
        self.datetime = pytz.UTC.localize(self.datetime)

    def to_json(self, output_path, variables, bottom_top = None, decimals = 2, indent = None):
        self.logger.debug("Loading RASPOUT file {0}".format(self.filename))
        for v in variables:
            json_path = os.path.join(output_path, "rasp_{0}_{1:%Y-%m-%d_%H%M}.json".format(v, self.datetime))
            self.logger.debug("Creating RASP JSON file {0}".format(json_path))
            if os.path.exists(json_path):
                os.remove(json_path)
            if v == 'uvmet':
                # special case for wind - need both components
                netcdf_to_json(self.path, json_path, variables=['umet', 'vmet'], bottom_top=bottom_top, decimals=decimals, indent=indent)
            else:
                netcdf_to_json(self.path, json_path, variables=[v], bottom_top=bottom_top, decimals=decimals, indent=indent)


def list_raspout_files(path, domain_id, logger=rasp.postprocess.get_logger()):
    """Returns a list of RASP OUT files in given path for a domain

    Keyword arguments:
    path -- path where to look for RASP OUT files
    domain_id -- function returns RASP OUT files only for domain with the same id
    """
    logger.debug("Looking for RASPOUT files")

    raspout_files = []
    search_path = os.path.join(path, "raspout_d{0:02d}_*.nc".format(domain_id))
    logger.debug('search_path: {0}'.format(search_path))
    for file_path in glob.glob(search_path):
        raspout_file = RASPOUTFile(file_path)
        raspout_files.append(raspout_file)
    return raspout_files


def get_blipspot_data(raspout_files, i, j, region_tzinfo, variables, output_path, decimals=2):
    """Function creates BLIPSPOT JSON from RASPOUT files"""

    data = {
        'i': i,
        'j': j,
        'time': []
    }

    raspout_files.sort(key=lambda raspout_file: raspout_file.datetime)
    datasets = []

    for raspout_file in raspout_files:
        logger.debug("Loading RASPOUT file {0} as NetCDF Dataset".format(raspout_file.filename))
        datasets.append(Dataset(raspout_file.path, 'r'))
        data['time'].append(raspout_file.datetime.astimezone(region_tzinfo).timestamp())

    for variable in variables:
        for d in range(0, len(datasets)):
            if 'bottom_top' in datasets[d].variables[var].dimensions:
                data[variable] = numpy.round(
                    datasets[d].variables[var][0, :, j, i].astype(numpy.float),
                    decimals=decimals
                    ).tolist()
            else:
                data[variable] = round(
                    float(datasets[d].variables[var][0][j][i]),
                    decimals)

    for dataset in datasets:
        dataset.close()