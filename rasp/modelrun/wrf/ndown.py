import os
import errno
import shutil

import rasp
from rasp.common.program import run_program, search_program_output, ProgramFailedException
from rasp.modelrun.wrf.namelist import set_time_step
from rasp.modelrun.wrf.real import delete_input_bdy_files
from rasp.modelrun.wrf.wrf import delete_wrfout_files

def run_ndown(wps_namelist, input_namelist, run_path, log_path, logger=rasp.modelrun.get_logger()):
    logger.debug("Preparing to run ndown.exe")
    #Rename the 'wrfinput_d0X' file to 'wrfndi_d0X.'
    wrfinput_path = os.path.join(run_path, "wrfinput_d{0:02d}".format(wps_namelist.share.max_dom))
    #wrfndi_path = os.path.join(run_path, "wrfndi_d{0:02d}".format(wps_namelist.share.max_dom))
    wrfndi_path = os.path.join(run_path, "wrfndi_d02")
    logger.debug("Copy file {0} to {1}".format(wrfinput_path, wrfndi_path))
    if os.path.exists(wrfndi_path):
        if os.path.islink(wrfndi_path):
            os.unlink(wrfndi_path)
        elif os.path.isfile(wrfndi_path):
            os.remove(wrfndi_path)
    shutil.copyfile(wrfinput_path, wrfndi_path)
    delete_input_bdy_files(run_path)

    logger.debug("Modifying namelist.input")
    input_namelist.timecontrol.io_form_auxinput2 = input_namelist.format_netCDF
    logger.debug("io_form_auxinput2: {0}".format(input_namelist.timecontrol.io_form_auxinput2))
    if input_namelist.domains.max_dom > 2:
        delta_dom = input_namelist.domains.max_dom - 2
        input_namelist.domains.max_dom = 2
        for attr in input_namelist.domains.__dict__:
            if (attr != 'eta_levels') and isinstance(input_namelist.domains.__dict__[attr], list):
                input_namelist.domains.__dict__[attr] = input_namelist.domains.__dict__[attr][delta_dom:]
                logger.debug("{0}: {1}".format(attr, input_namelist.domains.__dict__[attr]))
    input_namelist.save()

    #make sure we have namelist.input in work path
    if not os.path.exists(os.path.join(run_path, 'namelist.input')):
        raise FileNotFoundError(errno.ENOENT, "namelist.input not found in working path", run_path)

    log_file_path = os.path.join(log_path, 'ndown.out')
    run_program(os.path.join(rasp.modelrun.get_configuration().wrf.program_path, 'ndown.exe'), run_path, log_file_path)
    if search_program_output(log_file_path, 'SUCCESS COMPLETE NDOWN_EM INIT'):
        logger.info("ndown.exe completed successfully")
    else:
        raise ProgramFailedException("ndown.exe failed. Check the log file for details: {0}".format(log_file_path))

    logger.debug("Modifying namelist.input")
    input_namelist.domains.max_dom = 1
    for attr in input_namelist.domains.__dict__:
        if (attr != 'eta_levels') and isinstance(input_namelist.domains.__dict__[attr], list):
            input_namelist.domains.__dict__[attr] = [input_namelist.domains.__dict__[attr][-1]]
            logger.debug("{0}: {1}".format(attr, input_namelist.domains.__dict__[attr]))
    for attr in input_namelist.timecontrol.__dict__:
        if isinstance(input_namelist.timecontrol.__dict__[attr], list):
            input_namelist.timecontrol.__dict__[attr] = [input_namelist.timecontrol.__dict__[attr][-1]]
            logger.debug("{0}: {1}".format(attr, input_namelist.timecontrol.__dict__[attr]))

    set_time_step(input_namelist)
    input_namelist.save()

    delete_wrfout_files(run_path)
    shutil.move(os.path.join(run_path, 'wrfinput_d02'), os.path.join(run_path, 'wrfinput_d01'))
    shutil.move(os.path.join(run_path, 'wrfbdy_d02'), os.path.join(run_path, 'wrfbdy_d01'))
