import os
import datetime
import shutil

import rasp
from rasp.modelrun.namelistbase import NamelistBase, NamelistSectionBase
from rasp.modelrun.wps.projection import WPSProjection


class GridBounds(object):
    def __init__(self, north, south, west, east):
        self.north = north
        self.south = south
        self.west = west
        self.east = east
    def __str__(self):
        return "north: {0}, south: {1}, west: {2}, east: {3}".format(self.north, self.south, self.west, self.east)

class GridCorners(object):
    def __init__(self, sw, se, ne, nw):
        self.sw = sw
        self.se = se
        self.ne = ne
        self.nw = nw

class ShareWPSNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.wrf_core = section_dict['wrf_core']
        self.max_dom = section_dict['max_dom']

        self.start_datetimes = self.get_datetimes(self.get_array('start_date'), "%Y-%m-%d_%H:%M:%S")
        self.end_datetimes = self.get_datetimes(self.get_array('end_date'), "%Y-%m-%d_%H:%M:%S")

        self.interval_seconds = section_dict['interval_seconds']
        self.io_form_geogrid = section_dict['io_form_geogrid']
        self.opt_output_from_geogrid_path = self.get_opt_value('opt_output_from_geogrid_path')

        self.debug_level = self.get_opt_value('debug_level', 0)

    def set_dictionary_values(self):
        self.section_dict['max_dom'] = self.max_dom

        self.section_dict['start_date'] = self.get_datetime_strings(self.start_datetimes, "%Y-%m-%d_%H:%M:%S")
        self.section_dict['end_date'] = self.get_datetime_strings(self.end_datetimes, "%Y-%m-%d_%H:%M:%S")

        self.section_dict['interval_seconds'] = self.interval_seconds
        self.section_dict['io_form_geogrid'] = self.io_form_geogrid
        self.set_opt_value('opt_output_from_geogrid_path', self.opt_output_from_geogrid_path)

        self.section_dict['debug_level'] = self.debug_level

class GeogridWPSNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.ref_lat = section_dict['ref_lat']
        self.ref_lon = section_dict['ref_lon']
        self.geog_data_path  = section_dict['geog_data_path']

        """Resolution of source data to be used when interpolating static terrestrial data. <br> Options are 10m (~19km), 5m (~9km), 2m (~4km), 30s (~.9km)"""
        self.geog_data_res  = self.get_array('geog_data_res')

        self.opt_geogrid_tbl_path = section_dict['opt_geogrid_tbl_path']
        self.dx = section_dict['dx']
        self.dy = section_dict['dy']
        self.map_proj = section_dict['map_proj']
        self.stand_lon = section_dict['stand_lon']
        self.truelat1 = section_dict['truelat1']
        self.truelat2 = section_dict['truelat2']
        self.parent_id = self.get_array('parent_id')
        self.parent_grid_ratio = self.get_array('parent_grid_ratio')
        self.i_parent_start = self.get_array('i_parent_start')
        self.j_parent_start = self.get_array('j_parent_start')
        self.e_we = self.get_array('e_we')
        self.e_sn = self.get_array('e_sn')

    def set_dictionary_values(self):
        self.section_dict['geog_data_path'] = self.geog_data_path
        self.section_dict['opt_geogrid_tbl_path'] = self.opt_geogrid_tbl_path
        self.section_dict['i_parent_start'] = self.i_parent_start
        self.section_dict['j_parent_start'] = self.j_parent_start
        self.section_dict['e_we'] = self.e_we
        self.section_dict['e_sn'] = self.e_sn
        self.section_dict['dx'] = self.dx
        self.section_dict['dy'] = self.dy
        self.section_dict['geog_data_res'] = self.geog_data_res

class MetgridNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.fg_name = section_dict['fg_name']
        self.io_form_metgrid = section_dict['io_form_metgrid']
        self.opt_metgrid_tbl_path = section_dict['opt_metgrid_tbl_path']
        if 'opt_output_from_metgrid_path' in section_dict: 
            self.opt_output_from_metgrid_path = section_dict['opt_output_from_metgrid_path']
        else:
            self.opt_output_from_metgrid_path = None
    def set_dictionary_values(self):
        self.section_dict['fg_name'] = self.fg_name
        self.section_dict['opt_metgrid_tbl_path'] = self.opt_metgrid_tbl_path
        self.section_dict['io_form_metgrid'] = self.io_form_metgrid
        if self.opt_output_from_metgrid_path:
            self.section_dict['opt_output_from_metgrid_path'] = self.opt_output_from_metgrid_path

class UngribNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.out_format = self.section_dict['out_format']
        self.prefix = self.section_dict['prefix']

    def set_dictionary_values(self):
        self.section_dict['out_format'] = self.out_format
        self.section_dict['prefix'] = self.prefix

class WPSNamelist(NamelistBase):
    """
    WPS namelist object
    loads data from namelist.wps file
    """
    def __init__(self, path, logger=rasp.modelrun.get_logger()):
        super().__init__(path, logger)

        #initialize attribute for selected values
        self.share = ShareWPSNamelistSection(self.namelist['share'])
        self.geogrid = GeogridWPSNamelistSection(self.namelist['geogrid'])
        self.metgrid = MetgridNamelistSection(self.namelist['metgrid'])
        self.ungrib = UngribNamelistSection(self.namelist['ungrib'])

    def save(self):
        self.share.set_dictionary_values()
        self.geogrid.set_dictionary_values()
        self.metgrid.set_dictionary_values()
        self.ungrib.set_dictionary_values()
        super().save()

    def get_grid_projection(self, grid_id):
        self.logger.debug("Initializing WPS projection for {0}, grid: {1}".format(self.path, grid_id))
        projection = WPSProjection(
            self.geogrid.map_proj,
            self.geogrid.ref_lat,
            self.geogrid.ref_lon,
            self.geogrid.truelat1,
            self.geogrid.truelat2,
            self.geogrid.stand_lon,
            self.geogrid.dx,
            self.geogrid.dy,
            self.geogrid.e_we[0],
            self.geogrid.e_sn[0]
            )

        # create projection object adapted to the nest grid
        if grid_id != 1:
            e_we = self.geogrid.e_we[0]
            e_sn = self.geogrid.e_sn[0]
            dx = self.geogrid.dx
            dy = self.geogrid.dy
            i_parent_start = self.geogrid.i_parent_start[grid_id - 1]
            j_parent_start = self.geogrid.j_parent_start[grid_id - 1]
            tmp_grid = grid_id
            while (tmp_grid != 1):
                parent_grid_ratio = self.geogrid.parent_grid_ratio[tmp_grid - 1]
                dx /= parent_grid_ratio
                dy /= parent_grid_ratio
                i_parent_start = (i_parent_start - 1) * parent_grid_ratio + 1
                j_parent_start = (j_parent_start - 1) * parent_grid_ratio + 1
                e_we = (e_we - 1) * parent_grid_ratio + 1
                e_sn = (e_sn - 1) * parent_grid_ratio + 1
                tmp_grid = self.geogrid.parent_id[tmp_grid - 1];

            # create new projection for grid
            projection = WPSProjection(
                self.geogrid.map_proj,
                self.geogrid.ref_lat,
                self.geogrid.ref_lon,
                self.geogrid.truelat1,
                self.geogrid.truelat2,
                self.geogrid.stand_lon,
                dx,
                dy,
                e_we,
                e_sn)
            projection.corners_offset_i += (i_parent_start - 1) * dx
            projection.corners_offset_j += (j_parent_start - 1) * dy
        return projection;


    def get_grid_corners(self, grid_id):
        wps_projection = self.get_grid_projection(grid_id)

        sw = wps_projection.corners_ij_to_latlon(0, 0)
        se = wps_projection.corners_ij_to_latlon(self.geogrid.e_we[grid_id -1] - 1, 0)
        ne = wps_projection.corners_ij_to_latlon(self.geogrid.e_we[grid_id -1] - 1, self.geogrid.e_sn[grid_id - 1] - 1)
        nw = wps_projection.corners_ij_to_latlon(0, self.geogrid.e_sn[grid_id - 1] - 1)

        self.logger.debug("Grid {0} corners".format(grid_id))
        self.logger.debug("sw: lat={0}, lon={1}".format(sw[0], sw[1]))
        self.logger.debug("se: lat={0}, lon={1}".format(se[0], se[1]))
        self.logger.debug("ne: lat={0}, lon={1}".format(ne[0], ne[1]))
        self.logger.debug("nw: lat={0}, lon={1}".format(nw[0], nw[1]))

        return GridCorners(sw, se, ne, nw)

    def get_grid_bounds(self, grid_id):

        wps_projection = self.get_grid_projection(grid_id)

        for i in range(0, self.geogrid.e_we[grid_id -1]):
            if i == 0:
                south = wps_projection.corners_ij_to_latlon(i, 0)[0]
                north = wps_projection.corners_ij_to_latlon(i, self.geogrid.e_sn[grid_id - 1] - 1)[0]
            else:
                south = min(south, wps_projection.corners_ij_to_latlon(i, 0)[0])
                north = max(north, wps_projection.corners_ij_to_latlon(i, self.geogrid.e_sn[grid_id - 1] - 1)[0])

        for j in range(0, self.geogrid.e_sn[grid_id -1]):
            if j == 0:
                east = wps_projection.corners_ij_to_latlon(self.geogrid.e_we[grid_id -1] - 1, j)[1]
                west = wps_projection.corners_ij_to_latlon(0, j)[1]
            else:
                east = max(east, wps_projection.corners_ij_to_latlon(self.geogrid.e_we[grid_id -1] - 1, j)[1])
                west = min(west, wps_projection.corners_ij_to_latlon(0, j)[1])

        self.logger.debug("Grid {0} bounds".format(grid_id))
        self.logger.debug("north: {0}".format(north))
        self.logger.debug("south: {0}".format(south))
        self.logger.debug("west: {0}".format(west))
        self.logger.debug("east: {0}".format(east))

        return GridBounds(north, south, west, east)

    ungrib_prefix = 'UNGRIB'

def create_wps_namelist(region, forecast_date, work_path, logger=rasp.modelrun.get_logger()):

    logger = rasp.modelrun.get_logger()
    logger.debug("Preparing namelist.wps for current run")

    namelist_path = os.path.join(work_path, 'namelist.wps')
    if os.path.exists(namelist_path):
        os.remove(namelist_path)

    logger.debug("Copying region template namelist.wps to {0}".format(namelist_path))
    shutil.copy(region.template_wps_namelist_path, namelist_path)

    namelist = WPSNamelist(namelist_path)

    #modify times in namelist.wps
    logger.debug("Calculating start and end WPS namelist times")

    if not type(forecast_date) is datetime.date:
        raise TypeError("forecast_date is not of datetime.date type")

    # convert date to datetime
    forecast_datetime_utc = datetime.datetime.combine(forecast_date, datetime.time(0))
    logger.debug("forecast_date: {0:%Y-%m-%d}".format(forecast_datetime_utc))

    # wps start time is the forecast start time adjusted to the times of available GRIB files
    # The GRIB file times are multiples of the model interval - typically 3 hours
    # These are the desired forecast start and end hours
    forecast_start_hour_utc = region.to_utc_hour(region.configuration.forecast.start_hour_local) - rasp.modelrun.get_configuration().start_hour_offset
    forecast_end_hour_utc = region.to_utc_hour(region.configuration.forecast.end_hour_local)

    # Find a nearest multiple of GRIB file interval <= for forecast start hour
    wps_start_hour_utc = forecast_start_hour_utc - (forecast_start_hour_utc % region.grib_source.interval_hours)
    # Find a nearest multiple of GRIB file interval >= for forecast end hour
    if (forecast_end_hour_utc % region.grib_source.interval_hours) == 0:
        wps_end_hour_utc = forecast_end_hour_utc
    else:
        wps_end_hour_utc = forecast_end_hour_utc + (region.grib_source.interval_hours - (forecast_end_hour_utc % region.grib_source.interval_hours))

    wps_start_datetime_utc = forecast_datetime_utc + datetime.timedelta(hours = wps_start_hour_utc)
    wps_end_datetime_utc = forecast_datetime_utc + datetime.timedelta(hours = wps_end_hour_utc)
    logger.debug("WPS start_date:{0:%Y-%m-%d_%H:%M:%S}".format(wps_start_datetime_utc))
    logger.debug("WPS end_date:{0:%Y-%m-%d_%H:%M:%S}".format(wps_end_datetime_utc))

    namelist.share.start_datetimes = [wps_start_datetime_utc] * namelist.share.max_dom
    namelist.share.end_datetimes = [wps_end_datetime_utc] * namelist.share.max_dom

    logger.debug("Setting namelist.wps values")
    namelist.share.interval_seconds = region.grib_source.interval_hours * 60 * 60
    logger.debug("interval_seconds: {0} seconds".format(namelist.share.interval_seconds))

    namelist.save()

    return namelist