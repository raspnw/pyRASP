"""
This file contains classes and function to execute ungrib.exe
"""

import os
import errno
import glob

import rasp
from rasp.common.program import run_program, search_program_output, ProgramFailedException
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.common.system import create_file_symlink

class TooManyGribFilesException(Exception):
    pass

def delete_ungrib_files(path, logger=rasp.modelrun.get_logger()):
    #delete old ungrib files
    logger.debug("Deleting old ungrib files with prefix {0}".format(WPSNamelist.ungrib_prefix))
    for f in glob.glob(os.path.join(path, "{0}:*".format(WPSNamelist.ungrib_prefix))):
        if os.path.isfile(f):
            logger.debug("Deleting {0}".format(f))
            os.remove(f)
        if os.path.islink(f):
            logger.debug("Unlinking {0}".format(f))
            os.unlink(f)

def prep_ungrib(region, wps_namelist, grib_download_list, run_path, logger=rasp.modelrun.get_logger()):

    logger.debug("Preparing to run ungrib ")
    configuration = rasp.modelrun.get_configuration()

    #make sure we have namelist.wps in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.wps')):
        raise FileNotFoundError(errno.ENOENT, "namelist.wps not found in run path", run_path)

    delete_ungrib_files(run_path)

    logger.debug("Modifying namelist.wps")
    if configuration.wps.debug_level > 0:
        wps_namelist.share.debug_level = configuration.wps.debug_level
        logger.debug("debug_level: {0}".format(wps_namelist.share.debug_level))
    wps_namelist.share.opt_output_from_geogrid_path = region.static_data_path
    logger.debug("opt_output_from_geogrid_path: {0}".format(wps_namelist.share.opt_output_from_geogrid_path))
    wps_namelist.ungrib.prefix = WPSNamelist.ungrib_prefix
    logger.debug("prefix: {0}".format(wps_namelist.ungrib.prefix))
    wps_namelist.ungrib.out_format = 'WPS'
    logger.debug("out_format: {0}".format(wps_namelist.ungrib.out_format))
    wps_namelist.save()

    #create symbolic link to VTable
    ungrib_vtable_path = os.path.join(configuration.wps.ungrib_tables_path, region.grib_source.ungrib_vtable)
    logger.debug("Creating symbolic link to {0}".format(ungrib_vtable_path))
    if not os.path.exists(ungrib_vtable_path):
        raise FileNotFoundError(errno.ENOENT, "VTable file does not exist", ungrib_vtable_path)

    create_file_symlink(ungrib_vtable_path, os.path.join(run_path, 'Vtable'))

    #create symbolic link to grib files
    #first delete old files/symlinks
    logger.debug("Deleting old GRIBFILE symbolic links")
    for f in glob.glob(os.path.join(run_path, "GRIBFILE.*")):
        if os.path.islink(f):
            os.unlink(f)
        elif os.path.isfile(f):
            os.remove(f)

    alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    alpha_len = len(alpha)
    i1 = 0
    i2 = 0
    i3 = 0

    for grib_download in grib_download_list:
        link_filename = "GRIBFILE.{0}{1}{2}".format(alpha[i1], alpha[i2], alpha[i3])
        link_path = os.path.join(run_path, link_filename)
        i3 += 1
        if i3 >= alpha_len:
            i3 = 0
            i2 += 1
        if i2 >= alpha_len:
            i2 = 0
            i1 += 1
        if i1 >= alpha_len:
            raise TooManyGribFilesException("Out of letters for grib symlink extensions")
        logger.debug("Creating {0} link to {1}".format(link_filename, grib_download.download_path))
        if not os.path.exists(grib_download.download_path):
            raise FileNotFoundError(errno.ENOENT, "GRIB file not found", grib_download.download_path)
        create_file_symlink(grib_download.download_path, link_path)

def run_ungrib(region, wps_namelist, grib_download_list, run_path, log_path, logger=rasp.modelrun.get_logger()):
    configuration = rasp.modelrun.get_configuration()
    prep_ungrib(region, wps_namelist, grib_download_list, run_path)
    log_file_path = os.path.join(log_path, 'ungrib.out')
    run_program(os.path.join(configuration.wps.ungrib_program_path, 'ungrib.exe'), run_path, log_file_path)
    if search_program_output(log_file_path, 'Successful completion of ungrib'):
        logger.info("ungrib.exe completed successfully")
    else:
        raise ProgramFailedException("ungrib.exe failed. Check the log file for details: {0}".format(log_file_path))