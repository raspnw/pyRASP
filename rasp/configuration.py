import os
import platform

from ruamel import yaml

from rasp import configuration_path
from rasp import logger

class InvalidConfigurationException(Exception):
    pass

with open(os.path.join(configuration_path, 'system.yaml'), 'rt') as f:
    system_config = yaml.safe_load(f.read())

base_path = os.path.expanduser(system_config['base_path'])
region_base_path = system_config['region_base_path'].format(base_path = base_path)
gdal_win_path = system_config['gdal_win_path'].format(base_path = base_path)

if platform.system() == 'Windows':
    base_path = 'd:\\wxtofly\\v3\\test'
    region_base_path = base_path

class BaseSectionConfiguration(object):
    def __init__(self, config_dict):
        global base_path
        self.config_dict = config_dict
        self.base_path = base_path

    def get_bool(self, key, optional = False, default = False):
        value = self.get_value(key, optional = optional, default = default)
        if isinstance(value, bool):
            return value
        else:
            return str(value).lower() in ("yes", "true", "1")

    def get_path(self, key, check = True, create=False, optional=False):
        if optional and not key in self.config_dict:
            return None

        path = os.path.expanduser(BaseSectionConfiguration.convert_to_system_path(self.config_dict[key]).format(base_path=base_path))
        if not os.path.exists(path):
            if create:
                os.makedirs(path)
            elif check and platform.system() != 'Windows':
                raise InvalidConfigurationException("Invalid configuration: path {0} does not exist".format(path))
        return path

    def convert_to_system_path(path):
        return path.replace('/', os.sep).replace('\\', os.sep) 

    def get_partial_path(self, key):
        return BaseSectionConfiguration.convert_to_system_path(self.config_dict[key])

    def get_wrf_path(self, setup, key, sub_path):
        if self.config_dict and key in self.config_dict:
            return self.get_path(key, check=True, create=False)
        else:
            path = os.path.join(setup.wrf_path, BaseSectionConfiguration.convert_to_system_path(sub_path))
            if not os.path.exists(path):
                raise InvalidConfigurationException("Invalid configuration: path {0} does not exist".format(path))
            return path

    def get_value(self, key, optional=False, default=None, allowed_values=None):
        if key in self.config_dict:
            value = self.config_dict[key]
        elif optional:
            value = default
        else:
            raise InvalidConfigurationException("Invalid configuration: setting \"{0}\" not found".format(key))
        if allowed_values:
            if not value in allowed_values:
                raise InvalidConfigurationException("Invalid configuration: setting \"{0}\" has unrecognized value, use \"{1}\"".format(key, ", ".join(allowed_values)))
        return value

    def get_section(self, key):
        return BaseSectionConfiguration(self.config_dict[key])

    def get_list(self, key, optional=False, default=None):
        value = self.get_value(key, optional = optional, default = default)
        if value is None:
            return None
        if isinstance(value, list):
            return value
        else:
            return [ value ]


class BaseConfiguration(BaseSectionConfiguration):
    """
    Configuration base class
    """
    def __init__(self, path, section = None):
        global base_path

        if section:
            logger.debug("Reading configuration file {0}, section {1}".format(path, section))
        else:
            logger.debug("Reading configuration file {0}".format(path))
        with open(path, 'rt') as f:
            self.config_dict = yaml.safe_load(f.read())
            if section:
                self.config_dict = self.config_dict[section]
        super().__init__(self.config_dict)

class NetworkConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.proxies = self.get_value('proxies', optional=True)

class SetupConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        global base_path
        super().__init__(config_dict)
        self.wrf_version = self.get_value('wrf_version', optional=False)
        self.packages = self.get_list('packages')
        self.wrf_path = os.path.join(base_path, 'WRF{0}'.format(self.wrf_version))

network = NetworkConfiguration(system_config['network'])
setup = SetupConfiguration(system_config['setup'])
