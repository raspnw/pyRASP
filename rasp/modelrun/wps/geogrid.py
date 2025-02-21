"""
This file contains classes and function to execute ungrib.exe
"""
import os
import errno
import glob
import shutil
import re
import subprocess
from urllib.parse import urljoin

import rasp
from rasp.modelrun import ncdump
from rasp.common.program import run_program, ProgramFailedException
from rasp.common.download import download_file, download_filelist
from rasp.common.system import get_file_hash
from rasp.modelrun.wps.elevation import ElevationDataConfiguration, ElevationData
from rasp.common.system import create_file_symlink

class DecompressException(Exception):
    pass

geog_file_urls = None

def prep_geogrid(region, wps_namelist, run_path, logger=rasp.modelrun.get_logger()):
    logger.debug("Preparing to run geogrid")
    configuration = rasp.modelrun.get_configuration()

    set_default_geog_data_res(wps_namelist, logger)

    #make sure we have namelist.wps in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.wps')):
        raise FileNotFoundError(errno.ENOENT, "namelist.wps not found in run path", run_path)

    #delete old geogrid files
    logger.debug("Deleting old geogrid files")
    for f in glob.glob(os.path.join(region.static_data_path, "geo_em.*")):
        if os.path.isfile(f):
            logger.debug("Deleting {0}".format(f))
            os.remove(f)

    # full path to GEOGRID.TBL
    geogrid_table_path = os.path.join(configuration.wps.geogrid_tables_path, "GEOGRID.TBL.{0}".format(wps_namelist.share.wrf_core))

    # function checks if elevation data are requested,
    # creates a new table file and
    # returns modified path
    # return geogrid_table_path without changes if elevation data are not requested
    geogrid_table_path = prep_geogrid_elevation_data(region, wps_namelist, geogrid_table_path, logger=logger)

    logger.debug("Modifying namelist.wps")
    if configuration.wps.debug_level > 0:
        wps_namelist.share.debug_level = configuration.wps.debug_level
        logger.debug("debug_level: {0}".format(wps_namelist.share.debug_level))
    wps_namelist.geogrid.opt_geogrid_tbl_path = run_path
    logger.debug("opt_geogrid_tbl_path: {0}".format(wps_namelist.geogrid.opt_geogrid_tbl_path))
    wps_namelist.geogrid.geog_data_path = configuration.wps.geog_data_path
    logger.debug("geogrid_data_path: {0}".format(wps_namelist.geogrid.geog_data_path))
    wps_namelist.share.opt_output_from_geogrid_path = region.static_data_path
    logger.debug("opt_output_from_geogrid_path: {0}".format(wps_namelist.share.opt_output_from_geogrid_path))
    wps_namelist.share.io_form_geogrid = wps_namelist.format_netCDF
    logger.debug("io_form_geogrid: {0}".format(wps_namelist.share.io_form_geogrid))
    wps_namelist.save()

    #create GEOGRID.TBL symbolic link
    logger.debug("Creating symbolic link to {0}".format(geogrid_table_path))
    if not os.path.exists(geogrid_table_path):
        raise FileNotFoundError(errno.ENOENT, "Geogrid table file does not exist", geogrid_table_path)

    create_file_symlink(geogrid_table_path, os.path.join(run_path, 'GEOGRID.TBL'))

def set_default_geog_data_res(wps_namelist, logger=rasp.modelrun.get_logger()):
    configuration = rasp.modelrun.get_configuration()
    save_required = False

    if not configuration.wps.force_geog_data_res and configuration.wps.default_geog_data_res is None:
        return

    for idx, geog_data_res in enumerate(wps_namelist.geogrid.geog_data_res):
        if configuration.wps.force_geog_data_res or geog_data_res == 'default':
            logger.debug('Replacing d{0:02} geog_data_res "default" with {1}'.format(idx + 1, configuration.wps.default_geog_data_res))
            wps_namelist.geogrid.geog_data_res[idx] = configuration.wps.default_geog_data_res
            save_required = True

    if save_required:
        wps_namelist.save()


def prep_geogrid_elevation_data(region, wps_namelist, geogrid_table_path, logger=rasp.modelrun.get_logger()):
    configuration = rasp.modelrun.get_configuration()

    # get list of supported elevation data names
    elevation_data_names = ElevationDataConfiguration.get_names()
    elevation_data_bounds = {}

    # walk throught the list of geog_data_res values
    for idx, geog_data_res in enumerate(wps_namelist.geogrid.geog_data_res):
        # for each geog_data_res value walk through the individual parts and match it against elevation data names
        for res in geog_data_res.split('+'):
            if res in elevation_data_names:
                grid_id = idx + 1
                logger.debug("Grid {0} using {1} elevation data for geogrid.".format(grid_id, res))
                # store the bounds of the area elevation data are needed for
                # if multiple grids use the same res, elevation data will be created for an area covering all
                if res not in elevation_data_bounds:
                    elevation_data_bounds[res] = wps_namelist.get_grid_bounds(grid_id)
                else:
                    grid_bounds = wps_namelist.get_grid_bounds(grid_id)
                    elevation_data_bounds[res].north = max(elevation_data_bounds[res].north, grid_bounds.north)
                    elevation_data_bounds[res].south = min(elevation_data_bounds[res].south, grid_bounds.south)
                    elevation_data_bounds[res].east = max(elevation_data_bounds[res].east, grid_bounds.east)
                    elevation_data_bounds[res].west = min(elevation_data_bounds[res].west, grid_bounds.west)
                break

    # enumerate all areas to cover with elevation data
    for res, bounds in elevation_data_bounds.items():
        # init unique table file path for current elevation data name
        # ElevationData module creates a new GEOGRID.TBL file
        table_path = os.path.join(region.static_data_path, "GEOGRID.TBL.{0}".format(res))

        logger.debug("Creating SRTM geog data, resolution: {0}".format(res))
        elevation_data = ElevationData(res, logger=logger)
        elevation_data.create_geog_data(
            region.name, 
            bounds, 
            geogrid_table_path, 
            table_path, 
            os.path.join(configuration.wps.geog_data_path, 'elevation_data'), 
            configuration.wps.geog_data_path)

        return table_path

    return geogrid_table_path


def init_geog_file_urls(logger=rasp.modelrun.get_logger()):

    logger.debug("Initializing geog data download list")
    configuration = rasp.modelrun.get_configuration()

    global geog_file_urls
    geog_file_urls = {}

    filelist = download_filelist(configuration.wps.geog_download_url)
    for filename in filelist:
        if filename.endswith('.tar.gz') or filename.endswith('.tar.bz2'):
            parts = filename.split('.')
            geog_file_urls[parts[0]] = {}
            geog_file_urls[parts[0]]['url'] = urljoin(configuration.wps.geog_download_url, filename)
            geog_file_urls[parts[0]]['path'] = os.path.join(configuration.wps.geog_data_path, filename)

def download_geog_data(name, logger=rasp.modelrun.get_logger()):
    global geog_file_urls
    if not geog_file_urls:
        init_geog_file_urls()

    download_file(geog_file_urls[name]['url'], geog_file_urls[name]['path'])

    _, ext = os.path.splitext(geog_file_urls[name]['path'])
    ext = ext.lower()
    if ext == '.gz':
        tar_opts = 'xvzf'
    elif ext == '.bz2':
        tar_opts = 'xvjf'
    else:
        raise DecompressException("Don't know how to decompress file {0}".format(geog_file_urls[name]['path']))

    logger.debug("Extracting files from {0}".format(geog_file_urls[name]['path']))
    subprocess.check_output(['tar', tar_opts, geog_file_urls[name]['path'], '-C', rasp.modelrun.get_configuration().wps.geog_data_path])
    os.remove(geog_file_urls[name]['path'])

def get_namelist_hash(wps_namelist):
    configuration = rasp.modelrun.get_configuration()
    additional_data_string = None
    if not configuration.wps.default_geog_data_res is None:
        additional_data_string = configuration.wps.default_geog_data_res
        additional_data_string += str(configuration.wps.force_geog_data_res)
    return get_file_hash(wps_namelist.path, additional_data=additional_data_string.encode())

def run_geogrid(region, wps_namelist, run_path, log_path, logger=rasp.modelrun.get_logger()):
    logger.info("Running geogrid.exe")
    configuration = rasp.modelrun.get_configuration()

    wps_namelist_hash = get_namelist_hash(wps_namelist)

    wps_hash_file = os.path.join(region.static_data_path, 'wps.hash')
    hash_match = False
    if os.path.exists(wps_hash_file):
        logger.debug("Comparing namelist.wps hash")
        with open(wps_hash_file, 'rt') as f:
            hash = f.read()
            logger.debug("Current static data wps hash {0}".format(hash))
            logger.debug("wps hash {0}".format(wps_namelist_hash))
            hash_match = (hash == wps_namelist_hash)
    if not hash_match:
        logger.debug("Deleting all static data")
        # delete static data directory and recreate
        shutil.rmtree(region.static_data_path)
        os.makedirs(region.static_data_path)
        with open(wps_hash_file, 'wt') as f:
            logger.debug("Saving wps hash {0} to {1}".format(wps_namelist_hash, wps_hash_file))
            f.write(wps_namelist_hash)

    #run geogrid only if geogrid files do not exit or namelist.wps changed
    geodrid_files_exist = True

    if hash_match:
        for domain in range(1, wps_namelist.share.max_dom + 1):
            geodrid_files_exist = geodrid_files_exist and os.path.exists(os.path.join(region.static_data_path, "geo_em.d{0:02}.nc".format(domain)))

    if hash_match and geodrid_files_exist:
        logger.debug("Geogrid files already exist. Skipping running geogrid")
    else:
        prep_geogrid(region, wps_namelist, run_path)
        log_file_path = os.path.join(log_path, 'geogrid.out')

        success = False
        while True:
            run_program(os.path.join(configuration.wps.geogrid_program_path, 'geogrid.exe'), run_path, log_file_path)

            search_string = 'Successful completion of geogrid'
            logger.debug("Checking log file {0} contains {1}".format(log_file_path, search_string))

            lastline = None
            with open(log_file_path) as file:
                for line in file:
                    if line.strip() != '':
                        lastline = line
                        if search_string in line:
                            success = True
                            break

            if not success:
                # look for ERROR: Could not open /home/jiri/wx3/geog/topo_gmted2010_30s/index
                match = re.match( r'ERROR: Could not open {0}/(\w+)/\w+'.format(configuration.wps.geog_data_path.rstrip('/')), lastline)
                if match:
                    logger.debug("Found missing GEOG data {0}".format(match.group(1)))
                    download_geog_data(match.group(1) )
                else:
                    raise ProgramFailedException("geogrid.exe failed. Check the log file for details: {0}".format(log_file_path))
            else:
                logger.info("geogrid.exe completed successfully")
                if configuration.dump_netcdf:
                    for domain in range(1, wps_namelist.share.max_dom + 1):
                        ncdump(
                            os.path.join(region.static_data_path, "geo_em.d{0:02}.nc".format(domain)),
                            os.path.join(region.static_data_path, "geo_em.d{0:02}.txt".format(domain)))
                break