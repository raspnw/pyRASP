import os
import json

import rasp
from rasp import configuration_path
from rasp.configuration import BaseConfiguration, BaseSectionConfiguration
from rasp.postprocess.variables.colormap import VariableColorMap

class VariableConfiguration(BaseSectionConfiguration):
    def __init__(self, name, variable_dict, units_dict):
        super().__init__(variable_dict)
        units_config = BaseSectionConfiguration(units_dict)

        self.logger = rasp.postprocess.get_logger()
        self.logger.debug("Creating RASP variable object for {0}".format(name))

        self.name = name
        self.title = self.get_value('title')
        self.description = self.get_value('description', optional=True, default=None)
        self.ncl_plot = self.get_bool('ncl_plot', optional=True, default=True)
        self.rasp_variables = self.get_list('rasp_variables', optional=True, default=None)

        # get unit definition
        #if 'units' in variable_dict and variable_dict['units'] in units_dict:
        #    self.units = units_dict[variable_dict['units']]
        #else:
        #    self.units = {}
        #    self.units['metric'] = {}
        #    self.units['metric']['multiplier'] = 1
        #    self.units['metric']['units'] = '-'
        #    self.units['imperial'] = {}
        #    self.units['imperial']['multiplier'] = 1
        #    self.units['imperial']['units'] = '-'


        #if 'scale' in self.config_dict:
        #    scale_config = self.get_section('scale')
        #    self.scale_min = float(scale_config.get_value('min'))
        #    self.scale_max = float(scale_config.get_value('max'))
        #    self.scale_step = float(scale_config.get_value('step'))
        #    self.scale_unit_system = scale_config.get_value('unit_system', optional=True, default='metric')
        #else:
        #    self.scale_min = float(0)
        #    self.scale_max = float(10)
        #    self.scale_step = float(1)
        #    self.scale_unit_system = 'metric'

        #self.bins = []
        #level = self.scale_min
        #multiplier = 1
        #if (self.scale_unit_system != 'metric' ):
        #    multiplier = self.units[self.scale_unit_system]['multiplier']
        #while (level <= self.scale_max):
        #    self.bins.append(level * multiplier)
        #    level = round(level + self.scale_step, 2)

        #self.color_map = VariableColorMap.get_ncl_colormap_rainbow(len(self.bins))

    def get_scale(self):
        scale = {}
        scale['colors'] = []
        for c in self.color_map[1::]:
            scale['colors'].append('#{0:02x}{1:02x}{2:02x}'.format(c[0], c[1], c[2]))

        scale['ticks'] = {}
        scale['ticks']['metric'] = [round(bin, 2) for bin in self.bins]
        multiplier = self.units['metric']['multiplier']
        scale['ticks']['imperial'] = [round(bin * multiplier, 2) for bin in self.bins]
        return scale

    def save_json_metadata(self, path):
        metadata = {}
        metadata['name'] = self.name
        metadata['title'] = self.title
        metadata['description'] = self.description
        metadata['units'] = {}
        metadata['units']['metric'] = self.units['metric']['unit']
        metadata['units']['imperial'] = self.units['imperial']['unit']

        metadata['scale'] = self.get_scale()
        with open(path, 'w') as f:
            json.dump(metadata, f, ensure_ascii=False)

class VariablesConfiguration(BaseConfiguration):
    def __init__(self):
        super().__init__(os.path.join(configuration_path, 'rasp_variables.yaml'))
        self.variables = {}
        for v in self.config_dict['variables']:
            self.variables[v] = VariableConfiguration(v, self.config_dict['variables'][v], self.config_dict['units'])

    def __getitem__(self, key):
        return self.variables[key]