"""
This file contains classes and function to execute metgrid.exe
"""

import os
import errno
import glob

import rasp
from rasp.modelrun import ncdump
from rasp.common.program import run_program, search_program_output, ProgramFailedException
from rasp.common.system import create_file_symlink


def prep_metgrid(region, wps_namelist, run_path, logger=rasp.modelrun.get_logger()):

    logger.debug("Preparing to run metgrid")
    configuration = rasp.modelrun.get_configuration()

    #make sure we have namelist.wps in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.wps')):
        raise FileNotFoundError(errno.ENOENT, "namelist.wps not found in working path", run_path)

    #delete old metgrid files
    logger.debug("Deleting old metgrid files")
    for f in glob.glob(os.path.join(run_path, "met_em.*")):
        if os.path.isfile(f):
            logger.debug("Deleting {0}".format(f))
            os.remove(f)

    logger.debug("Modifying namelist.wps")
    if configuration.wps.debug_level > 0:
        wps_namelist.share.debug_level = configuration.wps.debug_level
        logger.debug("debug_level: {0}".format(wps_namelist.share.debug_level))
    wps_namelist.metgrid.fg_name = wps_namelist.ungrib.prefix
    logger.debug("metgrid_fg_name: {0}".format(wps_namelist.metgrid.fg_name))
    wps_namelist.metgrid.opt_metgrid_tbl_path = run_path
    logger.debug("opt_metgrid_tbl_path: {0}".format(wps_namelist.metgrid.opt_metgrid_tbl_path))
    wps_namelist.metgrid.opt_output_from_metgrid_path = run_path
    logger.debug("opt_output_from_metgrid_path: {0}".format(wps_namelist.metgrid.opt_output_from_metgrid_path))
    wps_namelist.share.opt_output_from_geogrid_path = region.static_data_path
    logger.debug("opt_output_from_geogrid_path: {0}".format(wps_namelist.share.opt_output_from_geogrid_path))
    wps_namelist.metgrid.io_form_metgrid = wps_namelist.format_netCDF
    logger.debug("io_form_metgrid: {0}".format(wps_namelist.metgrid.io_form_metgrid))
    wps_namelist.save()

    #create symbolic link to VTable
    metgrid_table_path = os.path.join(configuration.wps.metgrid_tables_path, "METGRID.TBL.{0}".format(wps_namelist.share.wrf_core))
    logger.debug("Creating symbolic link to {0}".format(metgrid_table_path))
    if not os.path.exists(metgrid_table_path):
        raise FileNotFoundError(errno.ENOENT, "Metgrid table file does not exist", metgrid_table_path)

    create_file_symlink(metgrid_table_path, os.path.join(run_path, 'METGRID.TBL'))


def run_metgrid(region, wps_namelist, run_path, log_path, logger=rasp.modelrun.get_logger()):
    configuration = rasp.modelrun.get_configuration()
    prep_metgrid(region, wps_namelist, run_path)
    log_file_path = os.path.join(log_path, 'metgrid.out')
    run_program(os.path.join(configuration.wps.metgrid_program_path, 'metgrid.exe'), run_path, log_file_path)
    if search_program_output(log_file_path, 'Successful completion of metgrid'):
        logger.info("metgrid.exe completed successfully")
        if configuration.dump_netcdf:
            for netcdf_path in glob.glob(os.path.join(run_path, "met_em.d*.nc")):
                ncdump(netcdf_path, os.path.join(run_path, 'ncdump', "{0}.txt".format(os.path.basename(netcdf_path))))
    else:
        raise ProgramFailedException("metgrid.exe failed. Check the log file for details: {0}".format(log_file_path))