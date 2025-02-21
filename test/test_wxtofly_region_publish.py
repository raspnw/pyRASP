import os
import logging
import sys
from pathlib import Path

import wxtofly

print(wxtofly.get_configuration().web.get_region_url('WA4', 'test'))
print(wxtofly.get_configuration().web.get_region_rel_path('WA4', 'test'))