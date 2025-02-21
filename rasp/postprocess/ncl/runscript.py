import os
import errno

import rasp
from rasp.common.program import run_program, search_program_output, ProgramFailedException

def run_ncl_script(script_path, log_file_path, ncl_script_args = None, logger=rasp.postprocess.get_logger()):

    configuration = rasp.postprocess.get_configuration()
    logger.debug("Runnning NCL script: {0}".format(script_path))
    if not os.path.exists(script_path):
        raise FileNotFoundError(errno.ENOENT, "NCL script {0} not found".os.path.basename(script_path), script_path)

    logger.debug("Setting environment variables")
    os.environ['NCARG_ROOT'] = configuration.ncl.root_path
    logger.debug("NCARG_ROOT: {0}".format(os.environ['NCARG_ROOT']))
    os.environ['NCARG_COLORMAPS'] = os.path.join(configuration.ncl.root_path, 'lib/ncarg/colormaps')
    logger.debug("NCARG_COLORMAPS: {0}".format(os.environ['NCARG_COLORMAPS']))
    if not configuration.ncl.rangs_path is None:
        os.environ['NCARG_RANGS'] = configuration.ncl.rangs_path
        logger.debug("NCARG_RANGS: {0}".format(os.environ['NCARG_RANGS']))
    
    os.environ['NCL_JACK_FORTRAN'] = configuration.ncl.drjack_lib
    logger.debug("NCL_JACK_FORTRAN: {0}".format(os.environ['NCL_JACK_FORTRAN']))
    os.environ['NCL_DEF_LIB_DIR'] = os.path.dirname(configuration.ncl.drjack_lib)
    logger.debug("NCL_DEF_LIB_DIR: {0}".format(os.environ['NCL_DEF_LIB_DIR']))

    ncl_path = os.path.join(configuration.ncl.root_path, 'bin', 'ncl')
    logger.debug("ncl path {0}".format(ncl_path))
    if not os.path.exists(ncl_path):
        raise FileNotFoundError(errno.ENOENT, "NCL program not found", ncl_path)

    ncl_args = [ '-n', '-p', script_path ]
    if ncl_script_args:
        logger.debug("ncl script arguments:")
        for arg in ncl_script_args:
            logger.debug(arg)
        if isinstance(ncl_script_args, list):
            for arg in ncl_script_args:
                ncl_args.append(arg)
        else:
            ncl_args.append(ncl_script_args)

    run_program(ncl_path, configuration.ncl.script_path, log_file_path, program_args = ncl_args)

    if search_program_output(log_file_path, 'fatal:'):
        raise ProgramFailedException("ncl failed. Check the log file for details: {0}".format(log_file_path))
    else:
        logger.info("ncl completed successfully")



