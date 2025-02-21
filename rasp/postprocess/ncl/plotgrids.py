import os

import rasp
from rasp.postprocess.ncl.runscript import run_ncl_script

def plot_grids(wps_file_path, output_file_path, type="png", logger = rasp.postprocess.get_logger()):

    configuration = rasp.postprocess.get_configuration()

    logger.info("Plotting grids using {0}".format(wps_file_path))
    ncl_script_path = os.path.join(configuration.ncl.script_path, 'plotgrids.ncl')
    log_file_path = os.path.join(os.path.dirname(output_file_path), 'plotgrids.ncl.out')

    args = ['wps_file="{0}"'.format(wps_file_path),
            'output_file="{0}"'.format(output_file_path),
            'type="{0}"'.format(type)]

    run_ncl_script(ncl_script_path, log_file_path, ncl_script_args = args)
    # do not keep the log if no errors
    #os.remove(log_file_path)
