import sys
import os
import logging

from rasp.setup.utils import ensure_admin
from rasp.setup.libs import configure_ldconfig
from rasp.setup.dependencies import check_rasp_programs
from rasp.setup.compile import get_lib_paths

if __name__ == '__main__':

    ensure_admin()
    configure_ldconfig(get_lib_paths())
    check_rasp_programs()

    pass