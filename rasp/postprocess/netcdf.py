import json
import numpy
from netCDF4 import Dataset
import rasp

def dataset_to_json(dataset, output_file, variables = None, bottom_top = None, decimals = 2, indent = None, logger=rasp.postprocess.get_logger()):
    """Function saves NetCDF Dataset to JSON"""
    json_dimensions = {}
    json_variables = {}

    if variables is None:
        variables = dataset.variables.keys()

    for v in variables:
        if v == 'times':
            continue

        logger.debug("Adding variable {0} to json".format(v))

        data_array = None

        json_variables[v] = {}
        json_variables[v]['description'] = dataset.variables[v].description
        json_variables[v]['units'] = dataset.variables[v].units
        json_variables[v]['dimensions'] = []
        for dim in dataset.variables[v].dimensions:
            if dim == 'Time':
                continue
            json_variables[v]['dimensions'].append(dim)

            if (not bottom_top is None) and (dim == 'bottom_top'):
                if not dim in json_dimensions:
                    json_dimensions[dim] = len(bottom_top)
                bottom_top_mask = numpy.array([False] * dataset.dimensions[dim].size, dtype = bool)
                for z in bottom_top:
                    bottom_top_mask[z] = True
                data_array = dataset.variables[v][0][bottom_top_mask, :]
                continue

            if not dim in json_dimensions:
                json_dimensions[dim] = dataset.dimensions[dim].size

        if data_array is None:
            data_array = dataset.variables[v][0]

        if dataset.variables[v][0].dtype.kind == 'f':
            json_data_array = numpy.round(convert_numpy_array(data_array), decimals = decimals)
        else:
            json_data_array = convert_numpy_array(data_array)

        json_variables[v]['data'] = json_data_array.tolist()

    data = {}
    # data['attributes'] = json_attributes;
    data['dimensions'] = json_dimensions;
    data['variables'] = json_variables;

    with open(output_file, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent = indent)

def netcdf_to_json(path, output_file, variables = None, bottom_top = None, decimals = 2, indent = None, logger=rasp.postprocess.get_logger()):
    """Function saves NetCDF file to JSON"""
    dataset = Dataset(path, 'r')
    try:
        dataset_to_json(dataset, output_file, variables=variables, bottom_top=bottom_top, decimals=decimals, indent=indent)
    finally:
        dataset.close()


def convert_numpy_array(np_array):
    """Function converts numpy array of float or int to an array of python float and int

    Numpy values cannot be converted by JSON module
    """
    if np_array.dtype.kind == 'f':
        return np_array.astype(numpy.float)
    if np_array.dtype.kind == 'i':
        return np_array.astype(numpy.int)
    return np_array


def convert_numpy_value(value):
    """Function converts numpy float and int values to python float and int

    Numpy values cannot be converted by JSON module
    """
    if value.dtype.kind == 'f':
        return float(value)
    if value.dtype.kind == 'i':
        return int(value)
    return value


def get_grid_data(path, south_north, west_east, bottom_top = None, variables=None, logger=rasp.postprocess.get_logger()):
    """Function extracts data for specific grid point

    Arguments:
    path - NetCDF file path
    south_north - south-north grid coordinate
    west_east - west-east grid coordinate
    bottom_top - bottom-top coordinate for 3d variables
    variables - list of variables to extract

    Returns: dictionary
    """
    logger.debug("Extracting data for south_north={0}, west_east={1} from {2}".format(south_north, west_east, path))
    data = {}
    dataset = Dataset(path, 'r')
    for variable in variables:
        if bottom_top is None:
            data[variable] = convert_numpy_value(dataset.variables[variable][0][south_north][west_east])
        else:
            data[variable] = convert_numpy_value(dataset.variables[variable][0][bottom_top][south_north][west_east])
        logger.debug("   {0} = {1}".format(variable, data[variable]))
    dataset.close()
    return data