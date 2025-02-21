import os
import errno
import subprocess
import signal
import time
import datetime
import logging

class ProgramFailedException(Exception):
    pass

def sigint_handler(signal, frame):
    #print('Interrupted by user')
    try:
        exit(1)
    except:
        pass
signal.signal(signal.SIGINT, sigint_handler)

def run_program(program_path, work_path, log_file_path, program_args = None, logger=logging.getLogger()):

    filename = os.path.basename(program_path)
    logger.info("Running {0}".format(filename))
    logger.info("working path: {0}".format(work_path))

    if not os.path.exists(program_path):
        raise FileNotFoundError(errno.ENOENT, "Program not found", program_path)

    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    logger.debug("Running {0}, stdout file: {1}".format(program_path, log_file_path))

    run_args = [ program_path ]
    if program_args:
        logger.debug("program arguments:")
        if isinstance(program_args, list):
            for arg in program_args:
                run_args.append(arg)
                logger.debug(arg)
        else:
            run_args.append(program_args)
            logger.debug(program_args)

    logger.debug("Command: {0}".format(" ".join(run_args)))

    start_time = time.time()
    with open(log_file_path, 'w') as std_out:
        completed_process = subprocess.run(run_args, stdout = std_out, cwd = work_path, stderr = subprocess.STDOUT)
        logger.debug("{0} finished with exit code {1}".format(filename, completed_process.returncode))
        completed_process.check_returncode()
    logger.info("Execution time: {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))

    if not os.path.exists(log_file_path):
        raise ProgramFailedException("{0} out file not found: {1}".format(filename, log_file_path))

def search_program_output(log_file_path, search_string, logger=logging.getLogger()):
    logger.debug("Checking log file {0} contains {1}".format(log_file_path, search_string))

    with open(log_file_path) as file:
        for line in file:
            if search_string in line:
                return True
    return False