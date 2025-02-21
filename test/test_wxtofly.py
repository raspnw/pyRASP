import os
import logging
import sys

from wxtofly.run import wxtofly_run

if len(sys.argv) > 1:
    wxtofly_run(sys.argv[1])
else:
    wxtofly_run()