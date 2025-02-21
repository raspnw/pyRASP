import os
import errno
import glob
import logging
import rasp
from rasp.utils.program import run_program, search_program_output

def run_ndown(wps_namelist, input_namelist, run_path, log_path):
    logging.debug("Preparing to run ndown.exe")

    #make sure we have namelist.input in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.input')):
        raise FileNotFoundError(errno.ENOENT, "namelist.input not found in working path", run_path)

    log_file_path = os.path.join(log_path, 'ndown.out')
    run_program(os.path.join(rasp.configuration.model_run.program_path, 'ndown.exe'), run_path, log_file_path)
    if search_program_output(log_file_path, 'SUCCESS COMPLETE REAL_EM INIT'):
        logging.info("ndown.exe completed successfully")
    else:
        raise rasp.exceptions.ProgramFailedException("ndown.exe failed. Check the log file for details: {0}".format(log_file_path))