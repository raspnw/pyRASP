import os
import platform
import zipfile
import subprocess
import json
import errno
import re
import shutil
from urllib.parse import urljoin
from ruamel import yaml
from pathlib import Path
import tarfile

import rasp
from rasp import configuration_path
from rasp.common.download import download_file
from rasp.common.logging import start_file_log, stop_file_log, log_exception
from rasp.configuration import BaseConfiguration

class ElevationDataConfiguration(BaseConfiguration):

    def get_names():
        with open(os.path.join(configuration_path, 'elevation.yaml'), 'rt') as f:
            config = yaml.safe_load(f.read())
        return list(config.keys())

    """Represent GRIB model definition"""
    def __init__(self, name, logger=rasp.modelrun.get_logger()):
        self.logger = logger
        self.name = name
        self.logger.debug("Getting elevation data configuration for {0}".format(name))

        super().__init__(os.path.join(configuration_path, 'elevation.yaml'), section=name)

        self.description = self.get_value('description', optional=True)
        self.citation = self.get_value('citation', optional=True)

        self.bounding_boxes_json = os.path.join(os.path.dirname(__file__), 'data', self.get_partial_path('bounding_boxes_json'))
        self.download_url = self.get_value('download_url', optional=False)
        self.username = self.get_value('username', optional=True)
        self.password = self.get_value('password', optional=True)
        self.filename_mask = self.get_value('filename_mask', optional=True, default=None)
        self.tile_overlap = self.get_value('tile_overlap', optional=True, default=0)

        self.logger.debug("name: {0}".format(self.name))
        self.logger.debug("description: {0}".format(self.description))
        self.logger.debug("citation: {0}".format(self.citation))
        self.logger.debug("bounding_boxes_json: {0}".format(self.bounding_boxes_json))
        self.logger.debug("download_url: {0}".format(self.download_url))
        self.logger.debug("tile_overlap: {0}".format(self.tile_overlap))
        if self.filename_mask:
            self.logger.debug("filename_mask: {0}".format(self.filename_mask))


    def __str__(self):
        return "{0} ({1})".format(self.name, self.description)

class ElevationDataException(Exception):
    pass

class ElevationData(object):

    def __init__(self, name, logger=rasp.modelrun.get_logger()):
        self.logger = logger
        self.name = name
        self.data_configuration = ElevationDataConfiguration(name, logger=self.logger)
        self.tiles = None

        self.logger.debug('Reading tile data from {0}'.format(self.data_configuration.bounding_boxes_json))
        with open(self.data_configuration.bounding_boxes_json, 'rt') as f:
            geojson = json.load(f)
            self.tiles = geojson['features']
            self.logger.debug('tile count: {0}'.format(len(self.tiles)))

    def get_tile_bounds(self, tile):
        polygon = tile['geometry']['coordinates'][0]
        north = south = polygon[0][1]
        east = west = polygon[0][0]
        iterpolygon = iter(polygon)
        next(iterpolygon)
        for lonlat in iterpolygon:
            east = max(east, lonlat[0])
            west = min(west, lonlat[0])
            north = max(north, lonlat[1])
            south = min(south, lonlat[1])
        return (north, south, east, west)

    def find_tiles(self, area_bounds):
        self.logger.debug('Looking for tiles in grid bounds: {0}'.format(area_bounds))
        area_tiles = []
        for tile in self.tiles:
            north, south, east, west = self.get_tile_bounds(tile)
            if north < area_bounds.south:
                continue
            if south > area_bounds.north:
                continue
            if west > area_bounds.east:
                continue
            if east < area_bounds.west:
                continue
            self.logger.debug('Found tile: {0}'.format(tile['properties']))
            self.logger.debug('Tile bounds: north ={0}, south = {1}, east = {2}, west = {3}'.format(north, south, east, west))
            tile['bounds'] = {
               'north': north,
               'south': south,
               'east': east,
               'west': west
               }
            area_tiles.append(tile)
        return area_tiles


    def check_tile_filename(self, tile):
        if 'filename' in tile['properties']:
            return True;
        if 'SUFF_NAME' in tile['properties']:
            tile['properties']['filename'] = tile['properties']['SUFF_NAME'];
            if tile['properties']['filename'][0] == '_':
                tile['properties']['filename'] = tile['properties']['filename'][1:]
            return True
        else:
            return False
            

    def download_tile_data(self, tiles, download_path):
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        for tile in tiles:
            if not self.check_tile_filename(tile):
                raise ElevationDataException("Unable to determine tile filename, tile: {0}".format(tile['properties']))

            filename = tile['properties']['filename']
            name, ext = os.path.splitext(filename)
            tile['name'] = name

            self.logger.debug("Processing tile {0}".format(tile['name']))

            tile_url = self.data_configuration.download_url.format(**tile['properties'])
            tile['tile_path'] = os.path.join(download_path, filename)
            if not os.path.exists(tile['tile_path']):
                download_file(tile_url, tile['tile_path'], username=self.data_configuration.username, password=self.data_configuration.password, logger=self.logger)

            tile['unpack_path'] = os.path.join(download_path, name)
            if not os.path.exists(tile['unpack_path']):
                os.mkdir(tile['unpack_path'])

                self.logger.debug("Extracting files from {0} to {1}".format(tile['tile_path'], tile['unpack_path']))
                try:
                    if tile['tile_path'][-4:] == '.zip':
                        zip = zipfile.ZipFile(tile['tile_path'], 'r')
                        zip.extractall(tile['unpack_path'])
                        zip.close()
                    elif  tile['tile_path'][-7:] == '.tar.gz':
                        tar = tarfile.open(tile['tile_path'])
                        tar.extractall(path=tile['unpack_path'])
                        tar.close()
                    else:
                        raise ElevationDataException("Don't know how to unpack {0}".format(tile['tile_path']))
                except Exception as e:
                    log_exception("Unable to unpack file {0}".format(filename), e, logger=self.logger);
                    self.remove_tile(tile)
                    raise

            if self.find_bil_hdr_files(tile):
                continue

            input_file_found = False
            if self.data_configuration.filename_mask:
                input_file_found = self.find_input_file_and_convert(tile, self.data_configuration.filename_mask)
            else:
                for filename_mask in ['*.tif', '*.hgt']:
                    input_file_found = self.find_input_file_and_convert(tile, filename_mask)
                    if input_file_found:
                        break;

            if not input_file_found:
                self.logger.error("Unable to find input file in {0}".format(tile['unpack_path']))
                raise ElevationDataException("Unable to find input file in {0}".format(tile['unpack_path']))

    def remove_tile(self, tile):
        if os.path.exists(tile['tile_path']):
            os.remove(tile['tile_path'])
        if os.path.exists(tile['unpack_path']):
            shutil.rmtree(tile['unpack_path'])

    def find_bil_hdr_files(self, tile):
        bil_files = list(Path(tile['unpack_path']).glob('**/*.bil'))
        hdr_files = list(Path(tile['unpack_path']).glob('**/*.hdr'))
        if len(bil_files) > 1:
            raise ElevationDataException("Multiple BIL files found in {0}".format(tile['unpack_path']))
        if len(hdr_files) > 1:
            raise ElevationDataException("Multiple HDR files found in {0}".format(tile['unpack_path']))
        if len(bil_files) == 1 and len(hdr_files) == 1:
            tile['bil_path'] = str(bil_files[0].resolve())
            tile['hdr_path'] = str(hdr_files[0].resolve())
            return True
        return False

    def find_input_file_and_convert(self, tile, filename_mask):
        input_files = list(Path(tile['unpack_path']).glob('**/{0}'.format(filename_mask)))
        if len(input_files) > 1:
            raise ElevationDataException("Multiple {0} files found in {1}".format(filename_mask, tile['unpack_path']))
        if len(input_files) == 1:
            input_path = str(input_files[0].resolve())
            try:
                self.convert_to_binary(input_path)
            except:
                self.logger.error("Conversion of {0} to binary failed".format(input_path))
                self.remove_tile(tile)
                raise
            if not self.find_bil_hdr_files(tile):
                raise ElevationDataException("BIL and HDR files not created in {0}".format(tile['unpack_path']))
            else:
                return True
        return False

    def convert_to_binary(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, "data file not found", path)
        bil_file_path = "{0}.bil".format(path[:-4])
        if not os.path.exists(bil_file_path):
            gdal_translate_path = 'gdal_translate'
            if platform.system() == 'Windows':
                gdal_translate_path = os.path.join(rasp.configuration.gdal_win_path, gdal_translate_path + '.exe')
            args = [gdal_translate_path, '-of', 'ENVI', path, bil_file_path]
            self.logger.debug("Executing: {0}".format(" ".join(args)))
            subprocess.check_output(args)


    def get_tiles_latlon_bounds(self, tiles):
        self.logger.debug("Overall tiles bounds:")

        north = tiles[0]['bounds']['north']
        south = tiles[0]['bounds']['south']
        east = tiles[0]['bounds']['east']
        west = tiles[0]['bounds']['west']

        tileiter = iter(tiles)
        next(tileiter)

        for tile in tileiter:
            south = min(tile['bounds']['south'], south)
            north = max(tile['bounds']['north'], north)
            west = min(tile['bounds']['west'], west)
            east = max(tile['bounds']['east'], east)

        self.logger.debug("north: {0}".format(north))
        self.logger.debug("south: {0}".format(south))
        self.logger.debug("west: {0}".format(west))
        self.logger.debug("east: {0}".format(east))
        return (north, south, west, east)


    def get_hrd(self, tile):

        hdr = {}

        self.logger.debug("Parsing {0}".format(tile['hdr_path']))
        #map info = {Geographic Lat/Lon, 1, 1, -5.00041608553147, 45.0004168845861, 0.000833333333333333, 0.000833333333333333,WGS-84}
        with open(tile['hdr_path'], 'rt') as f:
            for line in f:
                match = re.match(r'^([a-z ]+) = (.+)', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    if key == 'map info':
                        value = re.match(r'\{(.+)\}', value).group(1)
                        hdr[key] = [field.strip() for field in value.split(',')]
                    elif key == 'samples':
                        hdr[key] = int(value)
                    elif key == 'lines':
                        hdr[key] = int(value)
                    else:
                        hdr[key] = value
                    self.logger.debug('{0}: {1}'.format(key, value))
        
        return hdr


    # tile_matrix[y][x]
    def create_tile_matrix(self, tiles):

        self.logger.debug("Creating tile matrix")

        # get bounding box for found tiles
        north, south, west, east = self.get_tiles_latlon_bounds(tiles)

        tile_matrix = {}
        tile_size_lon = tiles[0]['bounds']['east'] - tiles[0]['bounds']['west']
        tile_size_lat = tiles[0]['bounds']['north'] - tiles[0]['bounds']['south']

        self.logger.debug("tile_size_lon: {0}".format(tile_size_lon))
        self.logger.debug("tile_size_lat: {0}".format(tile_size_lat))

        max_name_len = 0

        for tile in tiles:

            max_name_len = max(max_name_len, len(tile['name']))

            self.logger.debug("tile: {0}".format(tile['properties']['filename']))

            cent_lon = (tile['bounds']['west'] + tile['bounds']['east']) / 2
            cent_lat = (tile['bounds']['north'] + tile['bounds']['south']) / 2

            x = int((cent_lon - west) // tile_size_lon)
            y = int((cent_lat - south) // tile_size_lat)

            self.logger.debug("x,y: {0},{1}".format(x, y))
            
            tile['hdr'] = self.get_hrd(tile)
            if not 'map info' in tile['hdr']:
                raise ElevationDataException("\"map info\" not found in {0}".format(tile['hdr_path']))


            #known lon/lat
            tile['known_lon'] = float(tile['hdr']['map info'][3])
            tile['known_lat'] = float(tile['hdr']['map info'][4])
            tile['dx'] = float(tile['hdr']['map info'][5])
            tile['dy'] = float(tile['hdr']['map info'][6])
            tile['lines'] = tile['hdr']['lines']
            tile['samples'] = tile['hdr']['samples']

            self.logger.debug("known lat/lon[{0}][{1}] = {2}, {3}".format(y, x, tile['known_lat'], tile['known_lon']))
            tile_matrix[y, x] = tile

        rows, cols = max(tile_matrix)
        max_name_len += 1
        self.logger.debug("Matrix has values:")
        for y in range(rows, -1, -1):
            str = '   {0:02}:'.format(y)
            for x in range(cols + 1):
                if (y, x) in tile_matrix:
                    str += tile_matrix[y, x]['name'].rjust(max_name_len)
                else:
                    str += ' '.rjust(max_name_len)
            self.logger.debug(str)

        return tile_matrix


    def find_known_lat_lon(self, tile_matrix):

        if (0, 0) in tile_matrix:
            self.logger.debug("SW tile exists. known_lat/lon = {0}/{1}".format(tile_matrix[0, 0]['known_lat'], tile_matrix[0, 0]['known_lon']))
            return (tile_matrix[0, 0]['known_lat'], tile_matrix[0, 0]['known_lon'])
        else:
            self.logger.debug("SW tile does not exists. Determining known_lat/lon.")
            rows, cols = max(tile_matrix)

            self.logger.debug("Matrix known lat/lon:")
            for y in range(rows, -1, -1):
                str = '{0:02}:'.format(y)
                for x in range(cols + 1):
                    if (y, x) in tile_matrix:
                        str += " [{0:8.3f},{1:8.3f}]".format(tile_matrix[y, x]['known_lat'], tile_matrix[y, x]['known_lon'])
                    else:
                        str += ' '.rjust(20)
                self.logger.debug(str)

            found_known_lat = False
            found_known_lon = False

            for y in range(rows + 1):
                if (y, 0) in tile_matrix:
                    known_lon = tile_matrix[y, 0]['known_lon']
                    self.logger.debug("SW tile known_lon: {0} (from tile [{1}][{2}]".format(known_lon, y, 0))
                    found_known_lon = True
                    break

            for x in range(cols):
                if (0, x) in tile_matrix:
                    known_lat = tile_matrix[0, x]['known_lat']
                    self.logger.debug("SW tile known_lat: {0} (from tile [{1}][{2}]".format(known_lat, 0, x))
                    found_known_lat = True
                    break

            if not found_known_lon or not found_known_lat:
                raise ElevationDataException("Current implementation is unable to determine known lat/lon from tile set")

            return (known_lat, known_lon)


    def create_index_file(self, known_lat, known_lon, index_file_path, tile_x, tile_y, dx, dy):
        self.logger.debug('Creating index file {0}'.format(index_file_path))
        with open(index_file_path, 'wt') as f:
            f.write("type = continuous\n")
            f.write("signed = yes\n")
            f.write("projection = regular_ll\n")
            f.write("dx = {0}\n".format(dx))
            f.write("dy = {0}\n".format(dy))
            f.write("known_x = 1.0\n")
            f.write("known_y = {0}\n".format(tile_y))
            f.write("known_lat = {0}\n".format(known_lat))
            f.write("known_lon = {0}\n".format(known_lon))
            f.write("wordsize = 2\n")
            f.write("endian = little\n")
            f.write("tile_x = {0}\n".format(tile_x))
            f.write("tile_y = {0}\n".format(tile_y))
            f.write("tile_z = 1\n")
            f.write("tile_bdr=1\n")
            f.write("row_order = top_bottom\n")
            f.write("missing_value = 32768\n")
            f.write("units = \"meters MSL\"\n")
            if self.data_configuration.description is None:
                f.write("description = \"{0}\"\n".format(self.name))
            else:
                f.write("description = \"{0}\"\n".format(self.data_configuration.description))

        with open(index_file_path, 'rt') as f:
            self.logger.debug(f.read())

    def get_tile_dims(self, tile_matrix):
        rows, cols = max(tile_matrix)
        for y in range(rows + 1):
            for x in range(cols + 1):
                if (y, x) in tile_matrix:
                    return (tile_matrix[y, x]['samples'] - 2 * self.data_configuration.tile_overlap, #tile_x
                            tile_matrix[y, x]['lines'] - 2 * self.data_configuration.tile_overlap, #tile_y
                            tile_matrix[y, x]['dx'], #dx
                            tile_matrix[y, x]['dy'], #dy
                            )

    def copy_bil_files(self, tile_matrix, geog_data_path, tile_x, tile_y):

        self.logger.debug("Copying BIL files")

        rows_step = tile_y
        cols_step = tile_x

        rows_start = 1
        rows_end = tile_y

        rows, cols = max(tile_matrix)
        is_complete_set = True

        #00001-ncols.00001-nrows
        for y in range(rows + 1):
            cols_start = 1
            cols_end = tile_x
            for x in range(cols + 1):
                if (y, x) in tile_matrix:
                    tile_matrix[y, x]['col-row'] = "{0:05}-{1:05}.{2:05}-{3:05}".format(cols_start, cols_end, rows_start, rows_end)
                    dest_path = os.path.join(geog_data_path, tile_matrix[y, x]['col-row'])
                    self.logger.debug("{0} --> {1}".format(os.path.basename(tile_matrix[y, x]['bil_path']), os.path.basename(dest_path)))
                    self.logger.debug("source: {0}".format(tile_matrix[y, x]['bil_path']))
                    self.logger.debug("destination: {0}".format(dest_path))
                    self.logger.debug("cols_start: {0}".format(cols_start))
                    self.logger.debug("cols_end: {0}".format(cols_end))
                    self.logger.debug("rows_start: {0}".format(rows_start))
                    self.logger.debug("rows_end: {0}".format(rows_end))
                    shutil.copyfile(tile_matrix[y, x]['bil_path'], dest_path)
                else:
                    is_complete_set = False
                cols_start += cols_step
                cols_end += cols_step
            rows_start += rows_step
            rows_end += rows_step


        self.logger.debug("Matrix data cols.rows files:")
        for y in range(rows, -1, -1):
            str = '{0:02}:'.format(y)
            for x in range(cols + 1):
                if (y, x) in tile_matrix:
                    str += " {0}".format(tile_matrix[y, x]['col-row'])
                else:
                    str += ' '.rjust(24)
            self.logger.debug(str)

        return is_complete_set


    def create_geogrid_tbl(self, is_complete_set, geogrid_table_path, modified_geogrid_table_path, geog_dirname):
        self.logger.debug("Creating {0} from {1}".format(modified_geogrid_table_path, geogrid_table_path))
        if is_complete_set:
            self.logger.debug("for complete tile set")
        else:
            self.logger.debug("for incomplete tile set")

        # immediatel above the line with "30s:average..."
        # add interp_option = SRTM3S:average_gcell(4.0)+four_pt+average_4pt
        # and above the line with "30s:topo ..."
        # add rel_path= SRTM3S:topo_SRTM{RES}_{REGION}/
        hgt_m_section = False
        interp_option_complete = False
        rel_path_complete = False
        df_complete = False
        modify_complete = False
        with open(geogrid_table_path, 'rt') as fin:
            with open(modified_geogrid_table_path, 'wt+') as fout:
                for line in fin:
                    if modify_complete:
                        fout.write(line)
                        continue

                    if not hgt_m_section and re.match(r'^name\s*=\s*HGT_M', line):
                        hgt_m_section = True
                        self.logger.debug("Entering HGT_M section")
                        if not is_complete_set:
                            self.logger.debug("Adding HGT_M/priority 2 section")
                            fout.write("name = HGT_M\n")
                            fout.write("        priority = 2\n")
                            fout.write("        dest_type = continuous\n")
                            fout.write("        df_dx=SLPX\n")
                            fout.write("        df_dy=SLPY\n")
                            fout.write("        smooth_option = smth-desmth_special; smooth_passes=1\n")
                            fout.write("#       fill_missing=0.\n")
                            fout.write("        interp_option = {0}:average_gcell(4.0)+four_pt+average_4pt\n".format(self.name))
                            fout.write("        interp_option = 30s:average_gcell(4.0)+four_pt+average_4pt\n")
                            fout.write("        interp_option = 2m:four_pt\n")
                            fout.write("        interp_option = 5m:four_pt\n")
                            fout.write("        interp_option = 10m:four_pt\n")
                            fout.write("        rel_path= {0}:{1}/\n".format(self.name, geog_dirname))
                            fout.write("        rel_path = 30s:topo_gmted2010_30s/\n")
                            fout.write("        rel_path = 2m:topo_2m/\n")
                            fout.write("        rel_path = 5m:topo_5m/\n")
                            fout.write("        rel_path = 10m:topo_10m/\n")
                            fout.write("===============================\n")
                        fout.write(line)
                        continue

                    if hgt_m_section and re.match(r'^={5,}', line):
                        self.logger.debug("Modification complete")
                        hgt_m_section = False
                        modify_complete = True
                        fout.write(line)
                        continue

                    if hgt_m_section and not is_complete_set:
                        if re.match(r'^\s+dest_type\s*=', line):
                            fout.write(line)
                            #fout.write("        df_dx=SLPX\n")
                            #fout.write("        df_dy=SLPY\n")
                            continue
                        elif re.match(r'^\s+(df_dx|df_dy)\s*=', line):
                            continue

                    if hgt_m_section and not interp_option_complete and re.match(r'^\s+interp_option\s*=', line):
                        fout.write("        interp_option = {0}:average_gcell(4.0)+four_pt+average_4pt\n".format(self.name))
                        interp_option_complete = True
                        fout.write(line)
                        continue

                    if hgt_m_section and not rel_path_complete and re.match(r'^\s+rel_path\s*=', line):
                        fout.write("        rel_path = {0}:{1}\n".format(self.name, geog_dirname))
                        rel_path_complete = True
                        fout.write(line)
                        continue
                    fout.write(line)


    # region_name - region name, used in geog data dir name
    # area_bounds - bounds of the grid to create SRTM geog data for
    # geogrid_table_path - path to GEOGRID.TBL file
    # modified_geogrid_table_path - path to where modifued SRTM GEOGRID.TBL file will be created
    # download_path - path to location where SRTM data are downloaded
    # geog_data_path - geog_data path
    def create_geog_data(self, region_name, area_bounds, geogrid_table_path, modified_geogrid_table_path, download_path, geog_data_path):
        geog_dirname = '{0}_{1}'.format(self.name, region_name)
        geog_data_path = os.path.join(geog_data_path, geog_dirname)
        self.logger.debug("Creating elevation data for geogrid")
        self.logger.debug("geog data path: {0}".format(geog_data_path))

        if not os.path.exists(geog_data_path) or not os.path.exists(modified_geogrid_table_path):

            if not os.path.exists(geog_data_path):
                os.makedirs(geog_data_path)

            log_handler = start_file_log(self.logger, os.path.join(geog_data_path, '{0}.log.csv'.format(self.name)))

            # find tiles matching grid bounds
            tiles = self.find_tiles(area_bounds)
            if len(tiles) == 0:
                self.logger.warning("No tiles found")
                return

            self.logger.debug("Found {0} tiles covering area".format(len(tiles)))

            # download found tiles data to download_path
            self.download_tile_data(tiles, download_path)

            # create a tile matrix which contains information about which tiles are missing from grid bounds
            tile_matrix = self.create_tile_matrix(tiles)

            # get known_lat, known_lon using the tile matrix
            # this is used to create the geog data index file
            known_lat, known_lon = self.find_known_lat_lon(tile_matrix)

            try:
                tile_x, tile_y, dx, dy = self.get_tile_dims(tile_matrix)
                # rename and copy bil files
                # function return a boolean indicating whether all tiles exist for grid
                is_complete_set = self.copy_bil_files(tile_matrix, geog_data_path, tile_x, tile_y)

                # init path to geog index file and create it
                index_file_path = os.path.join(geog_data_path, 'index')
                self.create_index_file(known_lat, known_lon, index_file_path, tile_x, tile_y, dx, dy)

                # modify GEOGRID.TBL to understand srtm data
                self.create_geogrid_tbl(is_complete_set, geogrid_table_path, modified_geogrid_table_path, geog_dirname)
                # for debugging copy the original table file
                shutil.copyfile(geogrid_table_path, "{0}.original".format(modified_geogrid_table_path))

            except Exception as e:
                self.logger.error("ERROR: {0}".format(e))
                self.logger.debug("Deleting {0}".format(geog_data_path))
                shutil.rmtree(geog_data_path)
                raise
            stop_file_log(self.logger, log_handler)
