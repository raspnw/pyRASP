import sys
import os
import logging

import rasp.setup
from rasp.setup.utils import ensure_admin
import rasp.setup.packages
from rasp.common.logging import start_file_log
from rasp.configuration import base_path, setup


if __name__ == '__main__':

    start_file_log(rasp.setup.logger, os.path.join(base_path, 'install.log.csv'))

    ensure_admin()

    rasp.setup.packages.install_packages(setup.packages)

    pass