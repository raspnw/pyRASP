import pyproj
import logging

class WPSProjection(object):

    def __init__(self, map_proj, ref_lat, ref_lon, truelat1, truelat2, stand_lon, dx, dy, e_we, e_sn, logger=logging.getLogger()):
        self.logger = logger
        if map_proj != 'lambert':
            raise NotImplementedError("WPSProjection supports only lambert grid projection")

        self.dx = dx
        self.dy = dy

        radius = 6370e3
        self.logger.debug("radius: {0}".format(radius))
        
        # Spherical latlon used by WRF
        self.latlon_sphere = pyproj.Proj(
            proj = 'latlong',
            a = radius,
            b = radius,
            towgs84 = '0,0,0',
            no_defs = True)

        # Lambert Conformal Conic used by WRF
        self.lambert_grid = pyproj.Proj(
            proj = 'lcc',
            lat_1 = truelat1,
            lat_2 = truelat2,
            lat_0 = ref_lat,
            lon_0 = stand_lon,
            a = radius,
            b = radius,
            towgs84 = '0,0,0',
            no_defs = True)

        self.logger.debug("Lambert Conformal Conic projection: {0}".format(self.lambert_grid.srs))
        self.logger.debug("lat_1: {0}".format(truelat1))
        self.logger.debug("lat_2: {0}".format(truelat2))
        self.logger.debug("lat_0: {0}".format(ref_lat))
        self.logger.debug("lon_0: {0}".format(stand_lon))
        self.logger.debug("dx: {0}".format(dx))
        self.logger.debug("dy: {0}".format(dy))
        self.logger.debug("e_sn: {0}".format(e_sn))
        self.logger.debug("e_we: {0}".format(e_we))

        # mass grid starts from center of SW grid cell - point 0, 0
        mass_grid_size_i = (e_we - 2) * dx
        mass_grid_size_j = (e_sn - 2) * dy

        # corners grid starts from SW corner - point 0, 0
        corners_grid_size_i = (e_we - 1) * dx
        corners_grid_size_j = (e_sn - 1) * dy

        grid_center_i, grid_center_j = pyproj.transform(
                self.latlon_sphere,
                self.lambert_grid,
                ref_lon,
                ref_lat)

        self.logger.debug("grid_center_i: {0}".format(grid_center_i))
        self.logger.debug("grid_center_j: {0}".format(grid_center_j))
        
        self.mass_offset_i = grid_center_i - mass_grid_size_i * 0.5
        self.mass_offset_j = grid_center_j - mass_grid_size_j * 0.5

        self.corners_offset_i = grid_center_i - corners_grid_size_i * 0.5
        self.corners_offset_j = grid_center_j - corners_grid_size_j * 0.5

    def latlon_to_corners_ij(self, lat, lon):
        i, j = pyproj.transform(
            self.latlon_sphere,
            self.lambert_grid,
            lon,
            lat)

        return ((i - self.corners_offset_i) / self.dx,
                (j - self.corners_offset_j) / self.dy)

    def corners_ij_to_latlon(self, i, j):
        """
        Convert grid corners coordinates to latitude and longitude
        (0, 0) is the SW corner
        NE corner is (e_we - 1, e_sn - 1)
        """
        
        # transform coordinates to lat, lon
        lon, lat = pyproj.transform(
            self.lambert_grid,
            self.latlon_sphere,
            i * self.dx + self.corners_offset_i,
            j * self.dy + self.corners_offset_j)
        return (lat, lon)
