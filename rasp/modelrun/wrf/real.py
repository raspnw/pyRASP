import os
import errno
import glob

import rasp
from rasp.modelrun import ncdump
from rasp.common.program import run_program, search_program_output, ProgramFailedException

def delete_input_bdy_files(path, logger=rasp.modelrun.get_logger()):
    #delete old wrfbdy files
    logger.debug("Deleting previous wrfbdy files")
    for f in glob.glob(os.path.join(path, "wrfbdy*")):
        if os.path.isfile(f):
            logger.debug("Deleting {0}".format(f))
            os.remove(f)

    #delete old wrfinput files
    logger.debug("Deleting previous wrfinput files")
    for f in glob.glob(os.path.join(path, "wrfinput*")):
        if os.path.isfile(f):
            logger.debug("Deleting {0}".format(f))
            os.remove(f)

def run_real(run_path, log_path, logger=rasp.modelrun.get_logger()):
    logger.debug("Preparing to run real.exe")
    configuration = rasp.modelrun.get_configuration()
    #make sure we have namelist.input in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.input')):
        raise FileNotFoundError(errno.ENOENT, "namelist.input not found in working path", run_path)

    delete_input_bdy_files(run_path)

    log_file_path = os.path.join(log_path, 'real.out')
    run_program(os.path.join(configuration.wrf.program_path, 'real.exe'), run_path, log_file_path)
    if search_program_output(log_file_path, 'SUCCESS COMPLETE REAL_EM INIT'):
        logger.info("real.exe completed successfully")
        if configuration.dump_netcdf:
            for netcdf_path in glob.glob(os.path.join(run_path, "wrfinput_d*")):
                ncdump(netcdf_path, os.path.join(run_path, 'ncdump', "{0}.txt".format(os.path.basename(netcdf_path))))
            for netcdf_path in glob.glob(os.path.join(run_path, "wrfbdy*")):
                ncdump(netcdf_path, os.path.join(run_path, 'ncdump', "{0}.txt".format(os.path.basename(netcdf_path))))
    else:
        raise ProgramFailedException("real.exe failed. Check the log file for details: {0}".format(log_file_path))