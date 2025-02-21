import os
import logging
import sys
import glob

from rasp.region import Region
from rasp.common.system import remove_all_files
from rasp.postprocess.wrf import plot_variables, list_wrfout_files

if __name__ == '__main__':

    region_name = sys.argv[1]
    region = Region(region_name)
    run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
    sites = region.get_sites()

    plots_output_path = os.path.join(run_output_path, 'plots')
    remove_all_files(plots_output_path)

    wrfout_files = list_wrfout_files(run_output_path, 1)
    variables = ['wstar']

    plot_variables(wrfout_files, region, variables, plots_output_path, plot_soundings=False, plot_units='imperial', type=sys.argv[2])

    pass