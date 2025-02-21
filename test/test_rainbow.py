import os
import logging
import sys
import datetime
import numpy 
from scipy.misc import imsave

import rasp.configuration
from rasp.postprocess.variables.configuration import VariablesConfiguration
from rasp.postprocess.variables.colormap import VariableColorMap


var_list = ['wstar']
vars_settings = VariablesConfiguration(var_list)
for v in var_list:
    image = VariableColorMap.get_image_data(vars_settings.variables[v].color_map)
    imsave(os.path.join(rasp.configuration.base_path, '{0}_rainbow.png'.format(v)), image)
    vars_settings.variables[v].save_json_metadata(os.path.join(rasp.configuration.base_path, '{0}_meta.json'.format(v)))