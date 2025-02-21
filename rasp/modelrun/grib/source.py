import os
import logging

from rasp import configuration_path
from rasp.configuration import BaseConfiguration

class GribSourceConfiguration(BaseConfiguration):
    """Represent GRIB model definition"""
    def __init__(self, name, logger=logging.getLogger()):
        self.logger = logger
        self.name = name
        self.logger.debug("Creating GRIB model definition object for %s", name)

        super().__init__(os.path.join(configuration_path, 'grib.yaml'), section=name)

        self.description = self.get_value('description', optional=True)
        self.interval_hours = self.get_value('interval_hours')

        self.protocol = self.get_value('protocol')
        self.server = self.get_value('server')
        self.url_path_format = self.get_value('url_path_format')
        self.url_file_format = self.get_value('url_file_format')
        self.ungrib_vtable = self.get_value('ungrib_vtable')
        self.use_nomads_filter = self.get_bool('use_nomads_filter', optional=True, default=False)
        self.model_cycles = self.get_list('model_cycles')
        self.model_cycles.sort()

        self.logger.debug("protocol: {0}".format(self.protocol))
        self.logger.debug("server: {0}".format(self.server))
        self.logger.debug("url_path_format: {0}".format(self.url_path_format))
        self.logger.debug("url_file_format: {0}".format(self.url_file_format))
        self.logger.debug("ungrib_vtable: {0}".format(self.ungrib_vtable))
        self.logger.debug("use_nomads_filter: {0}".format(self.use_nomads_filter))
        self.logger.debug("model_cycles: {0}".format(self.model_cycles))

        if self.use_nomads_filter:
            self.nomads_filter_url = self.get_value('nomads_filter_url')
            self.logger.debug("nomads_filter_url: {0}".format(self.nomads_filter_url))

    def __str__(self):
        return "{0} ({1})".format(self.name, self.description)
