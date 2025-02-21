import os
import logging
import json
import time
import datetime
from netCDF4 import Dataset
import numpy
from multiprocessing import Pool

from rasp.postprocess.variables.configuration import VariablesConfiguration

def get_blipspot_data(datasets, local_datetimes, i, j, variables, decimals=2):
    logger.debug("Extracting blipspot data for i,j: {0},{1}".format(i+1, j+1))
    data = {}
    data['terhgt'] = {
        'data': round(
            float(datasets[0].variables['HGT'][0][j][i]),
            decimals
            ),
        'units': datasets[0].variables['HGT'].units
        }
    data['geohgt'] = {
        'data': numpy.round(
            datasets[0].variables['Z'][0, :, j, i].astype(numpy.float),
            decimals=decimals
            ).tolist(),
        'units': datasets[0].variables['Z'].units
        }
    data['time'] = []
    add_time = True
    for variable in variables:
        data[var] = {
            'data': [],
            'units': datasets[0].variables[var].units
            }
        for d in range(0, len(datasets)):
            if add_time:
                data['time'].append(local_datetimes[d].timestamp())
            if 'bottom_top' in datasets[d].variables[var].dimensions:
                data[var]['data'].append(
                    numpy.round(
                        datasets[d].variables[var][0, :, j, i].astype(numpy.float),
                        decimals=decimals
                        ).tolist()
                    )
            else:
                data[var]['data'].append(
                    round(
                        float(datasets[d].variables[var][0][j][i]),
                        decimals
                        )
                    )
        add_time = False
    return data

def create_blipspot_json_j(datasets, local_datetimes, dim_west_east, j, variables, rasp_variables_settings, output_path):
    for i in range(0, dim_west_east):
        data = get_blipspot_data(datasets, local_datetimes, i, j, variables, rasp_variables_settings)
        j_output_path = os.path.join(output_path, str(j + 1))
        if not os.path.exists(j_output_path):
            os.makedirs(j_output_path)
        blipspot_json_path = os.path.join(j_output_path, "{0}.json".format(i + 1))
        logger.debug("Saving blipspot data to {0}".format(blipspot_json_path))
        with open(blipspot_json_path, "wt") as f:
            json.dump(data, f)


def create_blipspot_json(raspout_files, region_tzinfo, variables, output_path):
    """Function creates BLIPSPOT JSON from RASPOUT files"""

    raspout_files.sort(key=lambda raspout_file: raspout_file.datetime)
    datasets = []
    local_datetimes = []

    for raspout_file in raspout_files:
        logger.debug("Loading RASPOUT file {0} as NetCDF Dataset".format(raspout_file.filename))
        datasets.append(Dataset(raspout_file.path, 'r'))
        local_datetimes.append(raspout_file.datetime.astimezone(region_tzinfo))

    dim_west_east = datasets[0].dimensions['west_east'].size
    dim_south_north = datasets[0].dimensions['south_north'].size

    try:
        # ij are indexes not real ij mass-grid coordinates values which start from 1,1
        for j in range(0, dim_south_north):
            create_blipspot_json_j(datasets, local_datetimes, dim_west_east, j, variables, rasp_variables_settings, output_path)
    finally:
        for dataset in datasets:
            dataset.close()

def do_blipspot_work(task):
    datasets = []
    local_datetimes = []

    for raspout_file in task['raspout_files']:
        logger.debug("Loading RASPOUT file {0} as NetCDF Dataset".format(raspout_file.filename))
        datasets.append(Dataset(raspout_file.path, 'r'))
        local_datetimes.append(raspout_file.datetime.astimezone(task['region_tzinfo']))

    dim_west_east = datasets[0].dimensions['west_east'].size
    try:
        create_blipspot_json_j(datasets, local_datetimes, dim_west_east, task['j'], task['variables'], task['rasp_variables_settings'], task['output_path'])
    finally:
        for dataset in datasets:
            dataset.close()


def create_blipspot_json_parallel(raspout_files, region_tzinfo, variables, output_path):

    start_time = time.time()

    rasp_variables_settings = VariablesConfiguration(variables)

    raspout_files.sort(key=lambda raspout_file: raspout_file.datetime)
    dataset = Dataset(raspout_files[0].path, 'r')
    dim_south_north = dataset.dimensions['south_north'].size

    tasks = []
    for j in range(0, dim_south_north):
        task = {}
        task['raspout_files'] = raspout_files
        task['region_tzinfo'] = region_tzinfo
        task['j'] = j
        task['variables'] = variables
        task['output_path'] = output_path
        task['rasp_variables_settings'] = rasp_variables_settings
        tasks.append(task)

    # make the Pool of workers
    logger.debug("Executing {0} blipspot tasks".format(len(tasks)))
    pool = Pool(processes = os.cpu_count())
    results = pool.map_async(do_blipspot_work, tasks)
    results.get()
    #results.wait()
    pool.close()
    pool.terminate()

    logger.debug("Execution time: {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))

