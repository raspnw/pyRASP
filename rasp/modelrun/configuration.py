import os
import rasp
from rasp.configuration import BaseConfiguration, BaseSectionConfiguration, setup

class GribConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.max_age_hours = self.get_value('max_age_hours', optional=True, default=5)
        self.unfiltered_download_path = self.get_path('unfiltered_download_path', create=True)
        self.max_wait_mins = self.get_value('max_wait_mins', optional=True, default=120)
        self.max_downloads = self.get_value('max_downloads', optional=True, default=5)

class WPSConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.debug_level = self.get_value('debug_level', optional=True, default=0)

        geogrid = self.get_section('geogrid')
        metgrid = self.get_section('metgrid')
        ungrib = self.get_section('ungrib')

        self.geog_data_path = geogrid.get_path('geog_data_path', create=True)
        self.geog_download_url = geogrid.get_value('geog_download_url')
        self.force_geog_data_res = geogrid.get_bool('force_geog_data_res', optional=True, default=False)
        self.default_geog_data_res = geogrid.get_value('default_geog_data_res', optional=(not self.force_geog_data_res), default=None)

        self.geogrid_program_path = geogrid.get_wrf_path(setup, 'program_path', 'WPS/geogrid')
        self.geogrid_tables_path = geogrid.get_wrf_path(setup, 'tables_path', 'WPS/geogrid')

        self.metgrid_program_path = metgrid.get_wrf_path(setup, 'program_path', 'WPS/metgrid')
        self.metgrid_tables_path = metgrid.get_wrf_path(setup, 'tables_path', 'WPS/metgrid')

        self.ungrib_program_path = ungrib.get_wrf_path(setup, 'program_path', 'WPS/ungrib')
        self.ungrib_tables_path = ungrib.get_wrf_path(setup, 'tables_path', 'WPS/ungrib/Variable_Tables')

class WRFConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.debug_level = self.get_value('debug_level', optional=True, default=0)

        self.program_path = self.get_wrf_path(setup, 'program_path', 'WRF/main')
        self.tables_path = self.get_wrf_path(setup, 'tables_path', 'WRF/run')

        self.use_adaptive_timestep = self.get_bool('use_adaptive_timestep')
        self.time_step_to_dx_to_ratio = self.get_value('time_step_to_dx_to_ratio')
        self.history_interval = self.get_value('history_interval')
        self.iofields = self.get_list('iofields', optional=True)

class ModelRunConfiguration(BaseConfiguration):
    def __init__(self):
        super().__init__(os.path.join(rasp.configuration_path, 'model_run.yaml'))

        self.start_hour_offset = self.get_value('start_hour_offset')
        self.dump_netcdf = self.get_bool('dump_netcdf', optional=True, default=False)
        if self.dump_netcdf:
            self.ncdump_path = self.get_wrf_path(setup, 'ncdump_path', 'LIBRARIES/netcdf/bin/ncdump')

        self.wps = WPSConfiguration(self.config_dict['wps'])
        self.wrf = WRFConfiguration(self.config_dict['wrf'])
        self.grib = GribConfiguration(self.config_dict['grib'])