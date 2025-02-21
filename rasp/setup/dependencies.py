import os

from rasp.setup import logger
from rasp.setup.libs import get_missing_libraries

def check_executable_files(executable_file_list):
    for f in executable_file_list:
        logger.info("Checking {0}".format(f))
        if not os.path.exists(f):
            logger.error("File {0} not found".format(f))
            continue
        missing_libs =  get_missing_libraries(f)
        if missing_libs:
            logger.error("File {0} has missing libraries: {1}".format(os.path.basename(f), missing_libs))
        else:
            logger.info("ok")
        
def check_rasp_programs():

    import rasp.modelrun
    import rasp.postprocess.ncl

    configuration = rasp.modelrun.get_configuration()

    programs = [
        os.path.join(configuration.wps.geogrid_program_path, 'geogrid.exe'),
        os.path.join(configuration.wps.metgrid_program_path, 'metgrid.exe'),
        os.path.join(configuration.wps.ungrib_program_path, 'ungrib.exe'),
        os.path.join(configuration.wrf.program_path, 'real.exe'),
        os.path.join(configuration.wrf.program_path, 'ndown.exe'),
        os.path.join(configuration.wrf.program_path, 'wrf.exe'),
        os.path.join(rasp.postprocess.get_configuration().ncl.root_path, 'bin', 'ncl')]

    logger.info("Checking RASP program dependencies")
    check_executable_files(programs)

if __name__ == '__main__':
    check_rasp_programs()