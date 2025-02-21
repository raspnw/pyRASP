import os
import urllib.parse

from rasp.configuration import BaseConfiguration, BaseSectionConfiguration
from rasp.postprocess.variables import validate_list

class WebConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.schema = 'http'
        self.server = self.get_value('server')
        self.root_path = self.get_value('root_path', optional=True, default=None)
        if not self.root_path is None:
            self.root_path = self.root_path.strip('/')
        self.region_root_path = self.get_value('region_root_path', optional=True, default=None)
        if not self.region_root_path is None:
            self.region_root_path = self.region_root_path.strip('/')

        self.jobs_path = self.get_value('jobs_path').strip('/')
        self.jobs_url = self.get_url(self.jobs_path)

    def get_url(self, path):
        # function creates absolute url using server and root_path settings
        # root_path can be not set or empty
        if not self.root_path is None:
            path = urllib.parse.urljoin('{0}/'.format(self.root_path), path)
        return urllib.parse.urlunparse((self.schema, self.server, path, None, None, None))

    def get_region_rel_path(self, region_name, rel_path):
        # function creates region specific absolute url using server, root_path and region_name settings
        # root_path can be not set or empty
        # assumes region related content is under /root_path/region_root_path/{REGION_NAME}/rel_path
        path = urllib.parse.urljoin('{0}/'.format(region_name), rel_path)

        if not self.region_root_path is None:
            path = urllib.parse.urljoin('{0}/'.format(self.region_root_path), path)

        return path

    def get_region_url(self, region_name, rel_path):
        # function creates region specific absolute url using server, root_path and region_name settings
        # root_path can be not set or empty
        # assumes region related content is under /root_path/region_root_path/{REGION_NAME}/rel_path
        path = self.get_region_rel_path(region_name, rel_path)
        if not self.root_path is None:
            path = urllib.parse.urljoin('{0}/'.format(self.root_path), path)

        return urllib.parse.urlunparse((self.schema, self.server, path, None, None, None))


class WxToFlyPostProcessBlipspotConfig(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.grid = self.get_bool('grid', optional=True, default=False)
        self.sites = self.get_bool('sites', optional=True, default=False)
        self.variables = self.get_list('variables', optional=True, default=[])


class WxToFlyPostProcessPlotsConfig(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.enabled = self.get_bool('enabled')
        self.units = self.get_value('units', allowed_values=['metric', 'imperial'])
        self.variables = self.get_list('variables', optional=True, default=[])


class WxToFlyPostProcessWindgramsConfig(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.enabled = self.get_bool('enabled')


class WxToFlyPostProcessSoundingsConfig(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.enabled = self.get_bool('enabled')


class WxToFlyPostProcessingConfig(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.plots = WxToFlyPostProcessPlotsConfig(config_dict['plots'])
        self.windgrams = WxToFlyPostProcessWindgramsConfig(config_dict['windgrams'])
        self.soundings = WxToFlyPostProcessSoundingsConfig(config_dict['soundings'])
        self.blipspot = WxToFlyPostProcessBlipspotConfig(config_dict['blipspot'])


class WxToFlyConfiguration(BaseConfiguration):
    def __init__(self, path):
        super().__init__(path)

        self.upload_date_format = "%Y%m%d"
        self.log_timestamp_format = "%Y-%m-%d_%H:%M:%S"
        self.start_time_offset = self.get_value('start_time_offset', optional=True, default=90)
        self.files_max_age_hours = self.get_value('files_max_age_hours', optional=True, default=3)
        self.live_log = self.get_bool('live_log', optional = True, default=False)
        self.upload_run_logs = self.get_bool('upload_run_logs', optional = True, default=False)

        self.web = WebConfiguration(self.config_dict['web'])
        self.postprocessing = WxToFlyPostProcessingConfig(self.config_dict['postprocessing'])
