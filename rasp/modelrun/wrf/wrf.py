import os
import errno
import glob

import rasp
from rasp.modelrun import ncdump
from rasp.common.program import run_program, search_program_output, ProgramFailedException
from rasp.common.system import create_file_symlink

def delete_wrfout_files(path, logger=rasp.modelrun.get_logger()):
    #delete old wrfout files
    logger.debug("Deleting previous wrfout files")
    for f in glob.glob(os.path.join(path, "wrfout*")):
        if os.path.islink(f):
            logger.debug("Unlinking {0}".format(f))
            os.unlink(f)
        if os.path.isfile(f):
            logger.debug("Deleting {0}".format(f))
            os.remove(f)


def run_wrf(run_path, log_path, logger=rasp.modelrun.get_logger()):
    logger.debug("Preparing to run wrf.exe")
    configuration = rasp.modelrun.get_configuration()

    #create symbolic links to Tables
    logger.debug("Creating symbolic links to WRF table/data files")
    for filename in os.listdir(configuration.wrf.tables_path):
        file_path = os.path.join(configuration.wrf.tables_path, filename)
        if os.path.isfile(file_path) and not filename.startswith('.') and not os.path.islink(file_path):
            link_path = os.path.join(run_path, filename)
            # if file already exists - do not overwrite
            if os.path.exists(link_path):
                continue
            create_file_symlink(file_path, link_path)

    #make sure we have namelist.input in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.input')):
        raise FileNotFoundError(errno.ENOENT, "namelist.input not found in working path", run_path)

    delete_wrfout_files(run_path)

    log_file_path = os.path.join(log_path, 'wrf.out')
    run_program(os.path.join(configuration.wrf.program_path, 'wrf.exe'), run_path, log_file_path)
    if search_program_output(log_file_path, 'SUCCESS COMPLETE WRF'):
        logger.info("wrf.exe completed successfully")
        if configuration.dump_netcdf:
            for netcdf_path in glob.glob(os.path.join(run_path, "wrfout_d*")):
                ncdump(netcdf_path, os.path.join(run_path, 'ncdump', "{0}.txt".format(os.path.basename(netcdf_path))))
    else:
        raise ProgramFailedException("wrf.exe failed. Check the log file for details: {0}".format(log_file_path))