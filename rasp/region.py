"""
This file contains region specific class definition
"""
import os
import shutil
import datetime
import json
import csv
import pytz
import logging
from timezonefinder import TimezoneFinder
import errno

import rasp
from rasp.configuration import BaseConfiguration, BaseSectionConfiguration, region_base_path
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.modelrun.grib.source import GribSourceConfiguration

class RegionSiteError(Exception):
    pass

class RegionSite(object):
    """Represent a point location"""
    def __init__(self, name, lat, lon, domain_id, area=None, state=None, country=None):
        self.name = name
        self.latitude = lat
        self.longitude = lon
        self.domain_id = domain_id
        self.area =  area
        self.state =  state
        self.country =  country

    def __str__(self):
        return '{0} [{1}, {2}], area: {3}, state: {4}'.format(self.name, self.latitude, self.longitude, self.area, self.state)


class RegionForecast(BaseSectionConfiguration):
    def __init__(self, config_dict, logger=logging.getLogger()):
        self.logger = logger
        super().__init__(config_dict)

        local_time = self.get_section('local_time')
        self.start_hour_local = local_time.get_value('start')
        self.end_hour_local = local_time.get_value('end')
        self.logger.debug("  start_hour_local: {0}".format(self.start_hour_local))
        self.logger.debug("  end_hour_local: {0}".format(self.end_hour_local))

class RegionConfiguration(BaseConfiguration):
    """
    RegionConfiguration object

    loads region configuration parameters from region.yaml

    """
    def __init__(self, base_path, logger=logging.getLogger()):
        self.logger = logger

        self.logger.debug("Initializing Region configuration object for region base path %s", base_path)
        super().__init__(os.path.join(base_path, 'region.yaml'))

        region = self.get_section('region')
        self.grib_source_name = region.get_value('grib_source')
        self.parent_region = region.get_value('parent_region', optional=True)

        self.forecast = RegionForecast(self.config_dict['forecast'])

        self.logger.debug("Grib source: %s", self.grib_source_name)

        self.site_files = self.get_list('site_files', optional=True, default=[])

class Region(object):
    """
    Region class represents a region of forecast
    a corresponding folder must exists in [base_path]/name
    """
    def __init__(self, name, logger=logging.getLogger()):
        self.logger = logger
        self.name = name.upper()
        self.logger.info("Initializing region %s", self.name)
        
        #initialize base path for this region
        self.base_path = Region.get_region_path(self.name)
        if not os.path.exists(self.base_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.base_path)

        self.static_data_path = os.path.join(self.base_path, 'static')
        logger.info("Static data path: {0}".format(self.static_data_path))
        if not os.path.exists(self.static_data_path):
            os.mkdir(self.static_data_path)


        # check namelist templates exists
        # if not check wps and input files exist
        # if yes create template files, otherwise raise exception
        namelists = ['namelist.wps', 'namelist.input']
        for nl in namelists:
            nl_path = os.path.join(self.base_path, nl)
            if not os.path.exists(nl_path):
                raise FileNotFoundError(errno.ENOENT, "{0} file not found for region {1}".format(nl, self.name), nl_path)

        #initialize wps namelist path and extract ref coordinates
        self.template_wps_namelist_path = os.path.join(self.base_path, 'namelist.wps')
        if not os.path.exists(self.template_wps_namelist_path):
            raise FileNotFoundError(errno.ENOENT, "namelist.wps template for region {0} not found".format(self.name), self.template_wps_namelist_path)

        self.wps = WPSNamelist(self.template_wps_namelist_path, self.logger)
        self.logger.debug('Ref_latitude: %.2f', self.wps.geogrid.ref_lat)
        self.logger.debug('Ref_longitude: %.2f', self.wps.geogrid.ref_lon)
        self.max_dom = self.wps.share.max_dom

        #initialize region's timezone parameters
        timezonefinder = TimezoneFinder() 
        str_timezone = timezonefinder.timezone_at(lng = self.wps.geogrid.ref_lon, lat = self.wps.geogrid.ref_lat)
        self.local_tzinfo = pytz.timezone(str_timezone)
        now = datetime.datetime.now(self.local_tzinfo)
        self.timezone_id = now.strftime('%Z')
        # UTC offset
        # local time = UTC time + UTC offset
        self.utc_offset = now.utcoffset().total_seconds() / 60 / 60
        self.logger.info('Timezone: %s(%s)', str_timezone, self.timezone_id)
        self.logger.info('UTC offset: %.1f', self.utc_offset)

        #initialize configuration object
        self.configuration = RegionConfiguration(self.base_path, self.logger)

        #initialize grib model object
        self.grib_source = GribSourceConfiguration(self.configuration.grib_source_name, self.logger)

        #initialize region GRIB download path for filtered files
        self.filtered_grib_download_path = os.path.join(self.base_path, 'grib')

        self.sites = None
        self.grid_projections = None

    def to_local_hour(self, utc_hour):
        return utc_hour + self.utc_offset

    def to_utc_hour(self, local_hour):
        return local_hour - self.utc_offset

    def to_local_datetime(self, utc_datetime):
        return utc_datetime + datetime.timedelta(hours = self.utc_offset)

    def to_utc_datetime(self, local_datetime):
        return local_datetime - datetime.timedelta(hours = self.utc_offset)

    def get_forecast_start_datetime_local(self, forecast_date):
        return self.local_tzinfo.localize(
            datetime.datetime.combine(forecast_date, datetime.time(hour = self.configuration.forecast.start_hour_local))
            )

    def get_forecast_start_datetime_utc(self, forecast_date):
        local_dt = self.get_forecast_start_datetime_local(forecast_date)
        return local_dt.astimezone(pytz.utc)

    def get_forecast_end_datetime_local(self, forecast_date):
        return self.local_tzinfo.localize(
            datetime.datetime.combine(forecast_date, datetime.time(hour = self.configuration.forecast.end_hour_local))
            )

    def get_forecast_end_datetime_utc(self, forecast_date):
        local_dt = self.get_forecast_end_datetime_local(forecast_date)
        return local_dt.astimezone(pytz.utc)

    def get_site_domain(self, lat, lon, logger):

        if self.grid_projections is None:
            self.grid_projections = {}
            for grid_id in range(1, self.wps.share.max_dom + 1):
                self.grid_projections[grid_id] = self.wps.get_grid_projection(grid_id)

        site_domain_id = 1
        side_domain_dx = self.grid_projections[1].dx

        i, j = self.grid_projections[1].latlon_to_corners_ij(lat, lon)
        if i < 0 or i > (self.wps.geogrid.e_we[0] - 1) or j < 0 or j > (self.wps.geogrid.e_sn[0] - 1):
            return -1

        for grid_id in range(2, self.wps.share.max_dom + 1):
            i, j = self.grid_projections[grid_id].latlon_to_corners_ij(lat, lon)
            if i >= 0 and i <= (self.wps.geogrid.e_we[grid_id - 1] - 1) and j >= 0 and j <= (self.wps.geogrid.e_sn[grid_id - 1] - 1):
                if self.grid_projections[grid_id].dx < side_domain_dx:
                    side_domain_dx = self.grid_projections[grid_id].dx
                    site_domain_id = grid_id

        return site_domain_id

    def _add_site(self, name, lat, lon, area=None, state=None, country=None):
        site_domain_id = self.get_site_domain(
            lat,
            lon,
            self.logger
            )
        if site_domain_id >= 1:
            self.sites.append(
                 RegionSite(name, lat, lon, site_domain_id, area=area, state=state, country=country)
                )
        else:
            self.logger.warning("site {0} [lat={1}, lon={2}] is outside of region master domain".format(name, lat, lon));

    def get_sites(self):
        """ function parses sites.json and creates list of RegionSites objects """
        if self.sites:
            return self.sites

        self.sites = []

        for site_file_name in self.configuration.site_files:
            site_file_path = os.path.join(self.base_path, site_file_name)
            if not os.path.exists(site_file_path):
                raise FileNotFoundError(errno.ENOENT, "Sites file {0} not found for region {1}".format(site_file_path, self.name), site_file_path)
            _, ext = os.path.splitext(site_file_path)
            ext = ext.lower()
            if ext == '.json':
                self.logger.debug("Reading JSON site list from {0}".format(site_file_path))
                with open(site_file_path, 'rt') as f:
                    sites_data = json.load(f)
                    for site_dict in sites_data:
                        self._add_site(
                            site_dict['name'],
                            float(site_dict['lat']),
                            float(site_dict['lon']),
                            area=site_dict.get('area'),
                            state=site_dict.get('state'),
                            country=site_dict.get('country')
                            )
                            
            if ext == '.wpt':
                self.logger.debug("Reading waypoint site list from {0}".format(site_file_path))
                with open(site_file_path, 'rt') as f:
                    reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_NONE)
                    # file format http://www.oziexplorer3.com/eng/help/fileformats.html
                    next(reader, None)
                    next(reader, None)
                    next(reader, None)
                    next(reader, None)
                    for row in reader:
                        stripped_row = [x.strip() for x in row]
                        site_name = stripped_row[10]
                        if site_name == '':
                            site_name = stripped_row[1]
                        self._add_site(site_name,
                            float(stripped_row[2]),
                            float(stripped_row[3])
                            )
        return self.sites

    def get_region_path(region_name):
        return os.path.join(
            region_base_path,
            region_name
            )

    def get_run_base_path(region_name):
        return os.path.join(
            Region.get_region_path(region_name),
            'run'
            )

    def get_run_output_path(region_name, init_date_utc, init_hour_utc, forecast_day):
        return os.path.join(
            Region.get_run_base_path(region_name),
            '{0:%Y%m%d}.{1:02d}z+{2}'.format(init_date_utc, init_hour_utc, forecast_day)
            )