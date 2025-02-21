import sys
import os
import logging

import rasp.setup
from rasp.setup.compile import compile
from rasp.configuration import setup

if __name__ == '__main__':
    compile(version=setup.wrf_version, clean=False)
    pass