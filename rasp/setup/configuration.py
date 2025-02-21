import os
from collections import OrderedDict

from rasp.setup import logger
from rasp.configuration import BaseConfiguration, BaseSectionConfiguration, setup
from rasp import configuration_path

class LibCompileConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.inc_path = self.get_value('inc_path').rstrip('/')
        self.lib_path = self.get_value('lib_path').rstrip('/')
        self.apt_package = self.get_value('apt_package', optional = True)
        self.compile = self.get_bool('compile', optional=True, default=False)
        self.sources_url = self.get_value('sources_url', optional = True)
        self.configure_options = self.get_value('configure_options', optional = True)
        self.prefix = self.get_value('prefix', optional = True)
        self.cmake = self.get_bool('cmake', optional=True, default=False)

class CompileTestConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.enabled = self.get_bool('enabled')
        self.sources_url = self.get_value('sources_url')

class WRFCompileConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.sources_url = self.get_value('sources_url')
        options = self.get_section('options')
        self.options_compile_configuration = options.get_value('compile_configuration')
        self.options_nesting = options.get_value('nesting')

class WPSCompileConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.sources_url = self.get_value('sources_url')
        options = self.get_section('options')
        self.options_compile_configuration = options.get_value('compile_configuration')

class TestsCompilConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.system_environment = CompileTestConfiguration(config_dict['system_environment'])
        self.lib_compatibity = CompileTestConfiguration(config_dict['lib_compatibity'])

class CompileConfiguration(BaseConfiguration):
    def __init__(self):

        path = os.path.join(configuration_path, 'compile', 'wrf{0}.yaml'.format(setup.wrf_version))

        super().__init__(path)

        self.compile_path = setup.wrf_path
        self.auto_answer = self.get_bool('auto_answer', optional=True, default=True)

        self.wrf = WRFCompileConfiguration(self.config_dict['wrf'])
        self.wps = WPSCompileConfiguration(self.config_dict['wps'])
        self.tests = TestsCompilConfiguration(self.config_dict['tests'])

        # Ordered dictionary of library configurations
        # It preserves the order from configuration file
        # which is the compile order
        self.libraries = OrderedDict()
        for lib_config in self.config_dict['libraries']:
            for key in lib_config:
                logger.debug("Adding lib {0}".format(key))
                self.libraries[key] = LibCompileConfiguration(lib_config[key])
