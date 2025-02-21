import os
import logging
import sys
from pathlib import Path

from rasp.region import Region
from wxtofly.job import create_job_from_run_output_path

region_name = sys.argv[1]
run_output_path = max(Path(Region.get_run_base_path(region_name)).glob('*/'), key=os.path.getmtime)
job = create_job_from_run_output_path(str(run_output_path))
job.publish_logs(str(run_output_path))
