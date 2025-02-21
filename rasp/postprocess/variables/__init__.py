import os

import rasp
from rasp import configuration_path
from rasp.configuration import BaseConfiguration, InvalidConfigurationException
from rasp.postprocess.variables.configuration import VariablesConfiguration

variables_configuration = None

def validate_list(variables, logger=rasp.postprocess.get_logger()):
    if len(variables) > 0:
        variables_config_path = os.path.join(configuration_path, 'rasp_variables.yaml')
        variables_config = BaseConfiguration(variables_config_path)
        for variable in variables:
            logger.debug("Verifying variable {0}".format(variable))
            if not variable in variables_config.config_dict['variables']:
                raise InvalidConfigurationException("{0} is not recognized as valid variable name. See {1} for available variable names".format(variable, variables_config_path))

def get_configuration():
    global variables_configuration
    if variables_configuration is None:
        variables_configuration = VariablesConfiguration()
    return variables_configuration