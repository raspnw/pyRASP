import os
import logging
import sys
import glob

from rasp.region import Region
from wxtofly.job import create_job_from_run_output_path

logger = logging.getLogger()

region_name = sys.argv[1]

run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
logger.debug("Redoing postprocess for path {0}".format(run_output_path))
job = create_job_from_run_output_path(run_output_path)
job.postprocess_raspout(run_output_path=run_output_path)