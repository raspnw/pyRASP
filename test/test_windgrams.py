import os
import logging
import sys
import datetime
import glob

from rasp.region import Region
from rasp.common.system import remove_all_files
from rasp.postprocess.wrf import plot_windgrams

if __name__ == '__main__':

    region_name = sys.argv[1]
    region = Region(region_name)
    run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
    sites = region.get_sites()

    windgram_output_path = os.path.join(run_output_path, 'windgrams')
    remove_all_files(windgram_output_path)

    plot_windgrams(run_output_path, sites, 1, windgram_output_path, utc_offset=region.utc_offset, timezone=region.timezone_id)

    pass