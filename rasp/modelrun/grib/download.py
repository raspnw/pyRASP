import os
import datetime
import requests
import time
import urllib.parse

import rasp

class GribException(Exception):
    pass

class GribDowloadItem(object):

    logger = rasp.modelrun.grib.get_logger()

    def __init__(self, region, init_date_utc, init_time, forecast_hour, grid_bounds = None):

        configuration = rasp.modelrun.get_configuration()

        GribDowloadItem.logger.debug("Creating GRIB download item")
        self.filename = region.grib_source.url_file_format.format(init_time = init_time, forecast_hour = forecast_hour, init_date_utc = init_date_utc)
        path = region.grib_source.url_path_format.format(init_time = init_time, forecast_hour = forecast_hour, init_date = init_date_utc)
        path = path.strip('/')
        path_fragments = path.split(sep = '/')
        self.dir = path_fragments[len(path_fragments) - 1]

        GribDowloadItem.logger.debug("filename: {0}".format(self.filename))
        GribDowloadItem.logger.debug("path: {0}".format(path))
        GribDowloadItem.logger.debug("dir: {0}".format(self.dir))

        if not region.grib_source.protocol in ['http', 'https']:
            raise GribException("Protocol {0} not supported for downloading GRIB files".format(region.grib_source.protocol))

        self.direct_url = '{0}://{1}/{2}/{3}'.format(
            region.grib_source.protocol.strip(':/'), 
            region.grib_source.server.strip('/'),
            path,
            self.filename.strip('/'))
        GribDowloadItem.logger.debug("direct url: {0}".format(self.direct_url))

        #initialize nomads filter for downloading sub-regions
        #do this only if file not downloaded yet
        self.use_nomads_filter = region.grib_source.use_nomads_filter
        if self.use_nomads_filter and not grid_bounds:
            GribDowloadItem.logger.warning("Unable to use nomads filter because grid bounds is not provided")
            self.use_nomads_filter = False

        if self.use_nomads_filter:
            #doing urllib.parse.urlencode on a dict puts the parameters in random order
            #which breaks the check functionality
            query = []
            query.append(urllib.parse.urlencode({'file': self.filename}))
            query.append(urllib.parse.urlencode({'all_lev': 'on'}))
            query.append(urllib.parse.urlencode({'all_var': 'on'}))
            query.append(urllib.parse.urlencode({'subregion': ''}))
            query.append(urllib.parse.urlencode({'leftlon': grid_bounds.west - 1}))
            query.append(urllib.parse.urlencode({'rightlon': grid_bounds.east + 1}))
            query.append(urllib.parse.urlencode({'toplat': grid_bounds.north + 1}))
            query.append(urllib.parse.urlencode({'bottomlat': grid_bounds.south - 1}))
            query.append(urllib.parse.urlencode({'dir': '/{0}'.format(self.dir)}))
            self.download_url = "{0}?{1}".format(region.grib_source.nomads_filter_url, '&'.join(query))
            download_folder_path = os.path.join(region.filtered_grib_download_path, self.dir)
        else:
            self.download_url = self.direct_url
            download_folder_path = os.path.join(configuration.grib.unfiltered_download_path, self.dir)
        GribDowloadItem.logger.debug("download URL: {0}".format(self.download_url))

        # this indicates whether GRIB file was downloaded
        self.downloaded = False

        #initialize local file
        #if one exists, check what was the download url
        #if it matches the url of this download, mark file as downloaded
        self.download_path = os.path.join(download_folder_path, self.filename)
        GribDowloadItem.logger.debug("local_file: {0}".format(self.download_path))
        self.local_url_file = "{0}.url".format(self.download_path)

        if not os.path.exists(download_folder_path):
            GribDowloadItem.logger.debug("Creating download folder {0}".format(download_folder_path))
            os.makedirs(download_folder_path)
        else:
            if os.path.exists(self.local_url_file):
                GribDowloadItem.logger.debug("Found previous URL file {0}".format(self.local_url_file))
                with open(self.local_url_file, 'rt') as f:
                    current_url = f.read()
                    GribDowloadItem.logger.debug("Previous download URL: {0}".format(current_url))
                if current_url == self.download_url:
                    GribDowloadItem.logger.debug("Previous download URL matches download item URL. Marking file as downloaded")
                    self.downloaded = True
                else:
                    GribDowloadItem.logger.debug("Deleting previous URL file")
                    os.remove(self.local_url_file)
            if not self.downloaded and os.path.exists(self.download_path): 
                GribDowloadItem.logger.debug("Deleting previous GRIB file")
                os.remove(self.download_path)


    def is_available(self):

        if self.downloaded:
            GribDowloadItem.logger.debug("GRIB already downloaded to {0}".format(self.download_path))
            return True

        GribDowloadItem.logger.debug("Sending HEAD request to {0}".format(self.direct_url))
        try:
            r = requests.head(self.direct_url, proxies = rasp.configuration.network.proxies)
            return (r.status_code == 200)
        except Exception as e:
            GribDowloadItem.logger.debug("Exception: {0}".format(e))
        return False

    def download(self):

        if self.downloaded:
            GribDowloadItem.logger.debug("GRIB already downloaded to {0}".format(self.download_path))
            return True

        GribDowloadItem.logger.info("Downloading {0} to {1}".format(self.download_url, self.download_path))
        try:
            r = requests.get(self.download_url, proxies = rasp.configuration.network.proxies, stream = True)
            if r.status_code == 200:
                with open(self.download_path, 'wb') as f:
                    for chunk in r:
                        f.write(chunk)
                self.downloaded = True
                GribDowloadItem.logger.debug("Saving download URL to {0}".format(self.local_url_file))
                with open(self.local_url_file, 'wt') as f:
                    f.write(self.download_url)
                GribDowloadItem.logger.info("Successfully downloaded {0} to {1}".format(self.download_url, self.download_path))
                return True
        except Exception as e:
            GribDowloadItem.logger.error("Download error: {0}".format(e))
        return False

def create_grib_download_list(region, wps_namelist, init_date_utc, init_hour_utc, logger=rasp.modelrun.grib.get_logger()):
    
    logger.debug("Getting a list of GRIB file names to download")
    logger.debug("region: {0}".format(region.name))
    logger.debug("grib_source: {0}".format(region.grib_source.name))
    logger.debug("init_date_utc: {0:%Y-%m-%d}".format(init_date_utc))
    logger.debug("init_hour_utc: {0}z".format(init_hour_utc))

    logger.debug("WPS start_date(moad): {0:%Y-%m-%d_%H:%M:%S}".format(wps_namelist.share.start_datetimes[0]))
    logger.debug("WPS end_date(moad): {0:%Y-%m-%d_%H:%M:%S}".format(wps_namelist.share.end_datetimes[0]))

    init_datetime = datetime.datetime.combine(init_date_utc, datetime.time(hour = init_hour_utc))
    logger.debug("init_datetime: {0:%Y-%m-%d_%H:%M:%S}".format(init_datetime))
    grib_start = wps_namelist.share.start_datetimes[0] - init_datetime
    grib_start_hour = int(grib_start.total_seconds() / 60 / 60)
    logger.debug("grib_start_hour: %d", grib_start_hour)
    
    if grib_start_hour < 0:
        logger.warning("Calculated GRIB start hour is negative - adjusting WPS namelist start times")
        logger.debug('Current start times: {0}'.format(wps_namelist.share.start_datetimes))
        while (grib_start_hour < 0):
            grib_start_hour += region.grib_source.interval_hours
            for i in range(len(wps_namelist.share.start_datetimes)):
                wps_namelist.share.start_datetimes[i] = wps_namelist.share.start_datetimes[i] + datetime.timedelta(hours=region.grib_source.interval_hours)
        wps_namelist.save()
        logger.debug('Adjusted start times: {0}'.format(wps_namelist.share.start_datetimes))

    if (grib_start_hour % region.grib_source.interval_hours) != 0:
        raise GribException("Calculated GRIB start hour is not multiple of model interval")

    grib_delta = wps_namelist.share.end_datetimes[0] - wps_namelist.share.start_datetimes[0]
    grib_end_hours = grib_start_hour + int(grib_delta.total_seconds() / 60 / 60)
    logger.debug("grib_end_hours: %d", grib_end_hours)
    if (grib_end_hours % region.grib_source.interval_hours) != 0:
        raise GribException("Calculated GRIB end hours is not multiple of model interval")

    grid_bounds = wps_namelist.get_grid_bounds(1)

    grib_download_list = list()
    grib_fh = grib_start_hour
    while grib_fh <= grib_end_hours:
        grib_download_item = GribDowloadItem(region, init_date_utc, init_hour_utc, grib_fh, grid_bounds)
        grib_download_list.append(grib_download_item)
        logger.debug("grib[{0}]: {1} ({2})".format(len(grib_download_list), grib_download_item.filename, grib_download_item.direct_url))
        grib_fh += region.grib_source.interval_hours

    return grib_download_list