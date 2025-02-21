import os
import logging
import sys

import rasp
from rasp.region import Region

from wxtofly.utils.cleanup import cleanup_ftp_server

region = Region('WA4')
cleanup_ftp_server(region, history_days=3)