import os
import subprocess
import re
import sys

from rasp.setup.utils import ensure_admin
from rasp.setup import logger

def get_missing_libraries(executable_file):
    
    ldd_output = subprocess.check_output(['ldd', executable_file])

    missing_libs = None

    for bytes in ldd_output.splitlines():
        line = bytes.decode(sys.stdout.encoding)
        match = re.match(r'\t(.*) => not found', str(line), re.IGNORECASE)
        if match:
            if not missing_libs:
                missing_libs = [match.group(1)]
            else:
                missing_libs.append(match.group(1))
    return missing_libs

def configure_ldconfig(lib_paths):
    ldconfig_file = '/etc/ld.so.conf.d/rasp.conf'
    logger.debug("ldconfig check: {0}".format(ldconfig_file))

    lib_paths = [path.rstrip('/') for path in lib_paths]
    logger.debug("lib directories: {0}".format(lib_paths))

    ldconfig_ok = os.path.exists(ldconfig_file)
    if ldconfig_ok:
        logger.debug("ldconfig file exists. Checking content")
        with open(ldconfig_file, "r") as f:
            ldconfig_lines = f.read().splitlines()

        for d in lib_paths:
            if not d in ldconfig_lines:
                logger.debug("{0} not found in ldconfig file".format(d))
                ldconfig_ok = False
                break

    if not ldconfig_ok:
        logger.debug("creating ldconfig file")
        ensure_admin()
        with open(ldconfig_file, "wt") as f:
            for d in lib_paths:
                f.write("{0}\n".format(d))
    else:
        logger.debug("ldconfig file ok")

    subprocess.run('ldconfig')
