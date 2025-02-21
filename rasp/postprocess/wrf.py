import os
import glob
import csv
import datetime
import pytz
import shutil
import re
import platform

from netCDF4 import Dataset
import numpy

import rasp
import rasp.postprocess.variables
from rasp.postprocess.ncl.runscript import run_ncl_script
from rasp.postprocess.rasp import RASPOUTFile
from rasp.postprocess.netcdf import netcdf_to_json, convert_numpy_value

class WRFFileNoFoundException(Exception):
    pass

class WRFOUTFile(object):

    wrfout_datetime_format = "%Y-%m-%d_%H:%M:%S"
    if platform.system() == 'Windows':
        wrfout_datetime_format = "%Y-%m-%d_%H%M%S"
    wrfout_filename_format = "wrfout_d{domain_id:02d}_{wrfout_datetime}"

    def get_filename(wrfout_domain_id, wrfout_datetime):
        return WRFOUTFile.wrfout_filename_format.format(domain_id = wrfout_domain_id, wrfout_datetime = wrfout_datetime.strftime(WRFOUTFile.wrfout_datetime_format))


    def __init__(self, path):
        self.logger = logger=rasp.postprocess.get_logger()

        self.logger.debug("Creating WRFOUT object: {0}".format(path))
        self.path = path
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, "WRFOUT file {0} not found".format(path), path)

        self.filename = os.path.basename(path)
        self.logger.debug("filename: {0}".format(self.filename))

        match = re.match( r'^wrfout_d([0-9]{2})_', self.filename)
        self.domain_id = int(match.group(1))
        self.logger.debug("domain_id: {0}".format(self.domain_id))

        self.datetime = datetime.datetime.strptime(self.filename, WRFOUTFile.wrfout_filename_format.format(domain_id = self.domain_id, wrfout_datetime = WRFOUTFile.wrfout_datetime_format))
        self.datetime = pytz.UTC.localize(self.datetime)
        self.logger.debug("datetime: {0}".format(self.datetime))

    def create_raspout_file(self, variables, output_path):
        self.logger.info("Creating RASP NetCDF from {0}".format(self.filename))
        ncl_script_path = os.path.join(rasp.postprocess.get_configuration().ncl.script_path, 'wrf_to_rasp.ncl')

        output_file = os.path.join(
            output_path, 
            RASPOUTFile.raspout_filename_format.format(
                domain_id = self.domain_id,
                raspout_datetime = self.datetime.strftime(RASPOUTFile.raspout_datetime_format)
                )
            )
        log_file_path = "{0}.log".format(output_file)

        if os.path.exists(output_file):
            os.remove(output_file)

        args = ['wrfout_file="{0}"'.format(self.path),
                'params="{0}"'.format(":".join(variables)),
                'output_file="{0}"'.format(output_file)]

        run_ncl_script(ncl_script_path, log_file_path, ncl_script_args = args)
        return RASPOUTFile(output_file)


    def plot_variables(self, region, variables, output_path, soundings=False, unit_system="imperial", type="png"):

        self.logger.debug("Plotting parameters from {0}".format(self.filename))

        datetime_local = region.to_local_datetime(self.datetime)

        log_path = output_path
        plot_output_path = os.path.join(
            output_path,
            "{0:%Y%m%d}".format(datetime_local),
            '{0:%H%M}'.format(datetime_local))
        os.makedirs(plot_output_path)

        self.logger.debug("output path: {0}".format(output_path))

        self.logger.debug("Setting environment variables")
        # determines if using DrJack's wrf_user_getvar() - default
        os.environ['GETVAR'] = 'DRJACK'
        os.environ['CONVERT'] = 'convert'
        self.logger.debug("GETVAR: {0}".format(os.environ['GETVAR']))
        self.logger.debug("CONVERT: {0}".format(os.environ['CONVERT']))

        plot_params = variables

        if soundings:
            plot_params = plot_params + soundings

        args = ['region="{0}"'.format(region.name),
                'output_path="{0}"'.format(plot_output_path),
                'wrfout_file="{0}"'.format(self.path),
                'params="{0}"'.format(":".join(plot_params)),
                'projection="mercator"',
                'img_size=800',
                'type="{0}"'.format(type),
                'units="{0}"'.format(unit_system)]

        ncl_script_path = os.path.join(rasp.postprocess.get_configuration().ncl.script_path, 'wrf2gm.ncl')
        log_file_path = os.path.join(log_path, 'wrf2gm_{0}.ncl.out'.format(self.filename))

        # must be run from script path to find other scripts
        run_ncl_script(ncl_script_path, log_file_path, ncl_script_args = args)


    def to_json(self, output_path, variables, bottom_top = None, decimals = 2, indent = None):
        self.logger.debug("Loading NetCDF file {0}".format(self.filename))
        for v in variables:
            json_path = os.path.join(output_path, "wrf_{0}_{1:%Y-%m-%d_%H%M}.json".format(v, self.datetime))
            self.logger.debug("Creating WRF JSON file {0}".format(json_path))
            if os.path.exists(json_path):
                os.remove(json_path)
            netcdf_to_json(self.path, json_path, variables=[v], bottom_top=bottom_top, decimals=decimals, indent=indent)


    def get_staggered_bounds(self):
        self.logger.debug("getting WRF OUT file bounds")
        dataset = Dataset(self.path, 'r')
        lat_min = float(dataset.variables['XLAT'][0].min())
        lat_max = float(dataset.variables['XLAT'][0].max())
        lon_min = float(dataset.variables['XLONG'][0].min())
        lon_max = float(dataset.variables['XLONG'][0].max())
        dataset.close()
        return ((lat_min, lat_max), (lon_min, lon_max))


    def get_attributes(self):
        self.logger.debug("getting WRF OUT attributes")
        dataset = Dataset(self.path, 'r')
        attributes = {}
        for attr_name in dataset.ncattrs():
            attributes[attr_name] = convert_numpy_value(dataset.getncattr(attr_name))
        dataset.close()
        return attributes


def list_wrfout_files(path, domain_id, start_datetime_utc=None, end_datetime_utc=None, logger=rasp.postprocess.get_logger()):
    """Returns a filtered list of WRFOUT files in path.

    Keyword arguments:
    path -- path where to look for WRFOUT files
    domain_id -- function returns WRFOUT files only for domain with the same id
    """

    logger.debug("Looking for WRFOUT files")
    if not start_datetime_utc is None:
        logger.debug('start_datetime: {0:%Y-%m-%d_%H:%M:%S} UTC'.format(start_datetime_utc))
    if not end_datetime_utc is None:
        logger.debug('end_datetime: {0:%Y-%m-%d_%H:%M:%S} UTC'.format(end_datetime_utc))

    wrfout_files = []
    search_path = os.path.join(path, "wrfout_d{0:02d}_*".format(domain_id))
    logger.debug('search_path: {0}'.format(search_path))

    for file_path in glob.glob(search_path):
        wrfout_file = WRFOUTFile(file_path)
        if not start_datetime_utc is None and wrfout_file.datetime < start_datetime_utc:
            continue
        if not end_datetime_utc is None and wrfout_file.datetime > end_datetime_utc:
            continue
        logger.debug("Found WRFOUT file: {0}".format(wrfout_file.filename))
        wrfout_files.append(wrfout_file)

    if len(wrfout_files) == 0:
        raise WRFFileNoFoundException("No WRFOUT files found")
    return wrfout_files



def inc_wrfout_files_domain(path, logger=rasp.postprocess.get_logger()):
    """Function increments domain id of all WRFOUT files in directory.
    This is used after one-way nested runs to have consistent WRFOUT file names"""

    logger.debug("Incrementing WRFOUT files domain")

    search_path = os.path.join(path, "wrfout_d??_*")
    logger.debug('search_path: {0}'.format(search_path))
    wrfout_files = []
    for file_path in glob.glob(search_path):
        wrfout_file = WRFOUTFile(file_path)
        logger.debug("Found WRFOUT file: {0}".format(wrfout_file.filename))
        wrfout_files.append(wrfout_file)

    min_domain = min(f.domain_id for f in wrfout_files)
    max_domain = min(f.domain_id for f in wrfout_files)

    for domain_id in range(max_domain, min_domain - 1, -1):
        for wrfout_file in filter(lambda x: x.domain_id == domain_id, wrfout_files):
            new_filename = WRFOUTFile.get_filename(wrfout_file.domain_id + 1, wrfout_file.datetime)
            logger.debug("Renaming {0} -> {1}".format(wrfout_file.filename, new_filename))
            os.rename(wrfout_file.path, os.path.join(path, new_filename))


def create_raspout_files(wrfout_files, variables, output_path, logger=rasp.postprocess.get_logger()):
    """Function creates RASPOUT files from list of WRFOUT file like objects"""
    logger.debug("Creating RASPOUT files")
    logger.debug("Variables: {0}".format(variables))
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    raspout_files = []
    for wrfout_file in wrfout_files:
        logger.debug("Creating RASPOUT file for {0}".format(wrfout_file.filename))
        raspout_files.append(
            wrfout_file.create_raspout_file(
                get_validated_variables(variables, False, logger=logger),
                output_path
                )
            )
    return raspout_files



def create_sites_csv(sites, domain_id, csv_file_path, logger=rasp.postprocess.get_logger()):
    """Function creates sites CSV file used by windgrams.ncl NCL script"""
    domain_sites_count = 0
    logger.debug("Creatin temp CSV file {0}".format(csv_file_path))
    if os.path.exists(csv_file_path):
        os.remove(csv_file_path)

    with open(csv_file_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter = ' ', quoting = csv.QUOTE_NONE)
        for site in sites:
            if site.domain_id == domain_id:
                row = [site.name.replace(" ", "_"), site.latitude, site.longitude]
                logger.debug("row: {0}".format(row))
                csv_writer.writerow(row)
                domain_sites_count += 1

    return domain_sites_count

def plot_windgrams(run_output_path, sites, domain_id, output_path, utc_offset, rhcut=94, timezone=None, logger=rasp.postprocess.get_logger()):
    """Function creates windgram plots for a list of sites

    Arguments:
    run_output_path -- path where to look for WRFOUT files
    sites -- list of RegionSite objects
    domain_id -- defines which grid WRFOUT files to use
    output_path -- path for saving windgram files
    utc_offset -- UTC offset of the region time zone
    rhcut -- RH limit to display clouds in plots
    timezone -- region's timezone name (for plot subtitle only)
    """
    logger.debug("Plotting windgrams")

    if len(sites) == 0:
        logger.debug("Site list is empty")
        return

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    log_path = output_path

    wrfout_search_path = os.path.join(run_output_path, 'wrfout_d{0:02d}_*'.format(domain_id))
    # Create CSV file for consumption by windgrams_csv.ncl
    csv_file_path = os.path.join(output_path, 'sites.csv')

    if create_sites_csv(sites, domain_id, csv_file_path) == 0:
        logger.debug("No sites defined for domain {0}".format(domain_id))
        return

    args = ['output_path="{0}"'.format(output_path),
            'wrfout_search_path="{0}"'.format(wrfout_search_path),
            'csv_file="{0}"'.format(csv_file_path),
            'utc_offset={0}'.format(utc_offset),
            'rhcut={0}'.format(rhcut),
            'type="png"']
    if not timezone is None:
        args.append('timezone="{0}"'.format(timezone))

    ncl_script_path = os.path.join(rasp.postprocess.get_configuration().ncl.script_path, 'windgrams.ncl')
    log_file_path = os.path.join(log_path, 'windgrams_d{0:02}_ncl.out'.format(domain_id))
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # must be run from script path to find other scripts
    run_ncl_script(ncl_script_path, log_file_path, ncl_script_args = args)
    os.remove(csv_file_path)

def create_region_data(region, domain_id, plot_units, logger=rasp.postprocess.get_logger()):
    """Function creates region data file for plotting soundings
    """

    region_data_ncl_path = os.path.join(rasp.postprocess.get_configuration().ncl.script_path, 'rasp.region_data.ncl')
    logger.debug("Creating file {0}".format(region_data_ncl_path))

    if os.path.exists(region_data_ncl_path):
        os.remove(region_data_ncl_path)

    soundings = []
    with open(region_data_ncl_path, 'w', newline='') as file:
        file.write('==={0}\n'.format(region.name))
        #units
        file.write('{0}\n'.format(plot_units))
        soundings_idx = 0
        for site in region.get_sites():
            if site.domain_id == domain_id:
                soundings_idx += 1
                soundings.append('sounding{0}'.format(soundings_idx))
                file.write('sounding{0}\n'.format(soundings_idx))
                file.write('{0}\n'.format(site.name))
                file.write('{0}\n'.format(site.latitude))
                file.write('{0}\n'.format(site.longitude))
    return soundings

def get_validated_variables(variables, ncl_plot, logger=rasp.postprocess.get_logger()):
    """Function returns a list of variables validated 
    against rasp_variables.yaml configuration file"""

    logger.debug("Validating variables list {0}".format(variables))

    variables_configuration = rasp.postprocess.variables.get_configuration()
    valid_variables = []
    for variable in variables:
        if variable in variables_configuration.variables:
            if ncl_plot:
                if variables_configuration.variables[variable].ncl_plot:
                    valid_variables.append(variable)
            else:
                if variables_configuration.variables[variable].rasp_variables is None:
                    valid_variables.append(variable)
                else:
                    valid_variables.extend(variables_configuration.variables[variable].rasp_variables)
        else:
            logger.warning("{0} is not valid variable name.".format(variable))

    logger.debug("Validated list {0}".format(valid_variables))
    return valid_variables

def plot_variables(wrfout_files, region, variables, output_path, plot_soundings=False, plot_units='imperial', type='png', logger=rasp.postprocess.get_logger()):
    logger.debug("Plotting RASP variables")
    if os.path.exists(output_path):
        logger.debug("Deleting old plots")
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    soundings = create_region_data(region, wrfout_files[0].domain_id, plot_units)
    if not plot_soundings:
        soundings = None

    for wrfout_file in wrfout_files:
        wrfout_file.plot_variables(
            region,
            get_validated_variables(variables, True, logger=logger),
            output_path,
            soundings=soundings,
            unit_system=plot_units,
            type=type
            )