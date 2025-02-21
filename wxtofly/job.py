import os
import logging
import time
import datetime
import errno
from pathlib import Path
from netCDF4 import Dataset
import numpy

import wxtofly
from wxtofly.utils.postprocess import publish_json, get_domain_polygon_path
from wxtofly.utils.system import create_clean_run_output_subdir
from wxtofly.utils.sites import create_sites_geojson
from wxtofly.utils.update import update_region_files
from wxtofly.utils.system import get_direct_subdirectories

import rasp
from rasp.region import Region, RegionSite
from rasp.modelrun.run import run_model, get_forecast_date
from rasp.modelrun.wps.namelist import WPSNamelist
from rasp.common.logging import log_exception, start_file_log, stop_file_log
from rasp.postprocess.wrf import list_wrfout_files, inc_wrfout_files_domain, create_raspout_files, plot_windgrams, plot_variables, get_validated_variables
from rasp.postprocess.rasp import list_raspout_files
from rasp.postprocess.netcdf import convert_numpy_value, convert_numpy_array
from rasp.postprocess.publish.publishqueue import add_to_queue
from rasp.common.system import wait

def create_job_from_run_output_path(run_output_path, logger=wxtofly.get_logger()):
    """Function creates Job object from run output path"""
    logger.debug("creating job from output path: {0}".format(run_output_path))

    # remove trailing /
    if run_output_path.endswith(os.sep):
        run_output_path = run_output_path[:-1]

    region_name = os.path.basename(os.path.dirname(os.path.dirname(run_output_path)))
    logger.debug("Extracted region name: {0}".format(region_name))

    run_dir_name = os.path.basename(run_output_path)
    logger.debug("run_dir_name: {0}".format(run_dir_name))

    head, str_day = run_dir_name.split('+')
    str_init_date, tail = head.split('.')
    init_hour_utc = int(tail[:-1])
    init_datetime = datetime.datetime.strptime(str_init_date, '%Y%m%d')
    job_name = '{0}+{1}'.format(region_name, str_day)
    logger.debug("Extracted job name: {0}".format(job_name))
    logger.debug("Extracted init date: {0}".format(init_datetime.date()))
    logger.debug("Extracted init init_hour_utc: {0}".format(init_hour_utc))

    job = Job(job_name, init_date_utc=init_datetime.date(), init_hour_utc=init_hour_utc, run_output_path=run_output_path)
    return job


class Job(object):
    """ class representing single job """

    # static properties holding the run start time and 
    # input model UTC init date
    run_start_datetime_utc = datetime.datetime.utcnow()
    init_date_utc = run_start_datetime_utc.date()

    # function initializes static properties
    def set_run_start_time():
        Job.run_start_datetime_utc = datetime.datetime.utcnow()
        Job.init_date_utc = Job.run_start_datetime_utc.date()

    def __init__(self, job_name, init_date_utc=None, init_hour_utc=None, timestamp=None, run_output_path=None, logger=wxtofly.get_logger()):
        self.logger = logger
        self.name = job_name
        self.init_hour_utc = None
        self.logger.debug("Creating job: {0}".format(job_name))

        if init_date_utc is None:
            self.init_date_utc = Job.init_date_utc
        else:
            self.init_date_utc = init_date_utc

        # get input model init hour from job name or use passed value
        if ':' in job_name:
            str_init_hour_utc, job_name = job_name.split(':')
            self.init_hour_utc = int(str_init_hour_utc)
        else:
            self.init_hour_utc = init_hour_utc

        if '+' in job_name:
            self.region_name, str_day = job_name.split('+')
            self.forecast_day = int(str_day)
        elif '-' in job_name:
            self.region_name, str_day = job_name.split('-')
            self.forecast_day = 0
            self.init_date_utc = self.init_date_utc - datetime.timedelta(days = int(str_day))
        else:
            self.region_name = job_name
            self.forecast_day = 0
        
        self.forecast_date = get_forecast_date(self.init_date_utc, self.forecast_day)
        self.log_path = os.path.join(Region.get_region_path(self.region_name), 'logs')

        self.logger.debug("region name: {0}".format(self.region_name))
        self.logger.debug("init_date_utc: {0}".format(self.init_date_utc))
        if self.init_hour_utc is not None:
            self.logger.debug("init_hour_utc: {0}".format(self.init_hour_utc))
        self.logger.debug("forecast_day: {0}".format(self.forecast_day))
        self.logger.debug("log_path: {0}".format(self.log_path))

        # update region files
        update_region_files(self.region_name, logger=self.logger)

        #init properties
        self.region = Region(self.region_name, logger=self.logger)
        self.run_output_path = run_output_path
        self.raspout_output_path = None
        self.timestamp = timestamp
        self.nested = False
        self.postprocess_start_domain = 1
        if self.region.configuration.parent_region != None:
            self.logger.info("job is a one-way nested run")
            self.nested = True
            self.postprocess_start_domain = 2



    def determine_init_time(self):
        """ function determines model init time from the run start time and region's GRIB cycle times """
        self.logger.debug("Determining init time")
        init_time = 0

        # walk through GRIB cycle times and return the nearest in the past
        for cycle_hour in self.region.grib_source.model_cycles:
            if (Job.run_start_datetime_utc.hour - cycle_hour) < 0:
                self.logger.debug("Init hour: {0:02}".format(init_time))
                return init_time
            init_time = cycle_hour
        return init_time

    def get_parent_output_path(self):
        """Returns parent region run output path for one-way nested runs"""
        return Region.get_run_output_path(self.region.configuration.parent_region, self.init_date_utc, self.init_hour_utc, self.forecast_day)

    def run(self, fn_state_change=None):
        """Function executes job"""
        wxtofly_configuration = wxtofly.get_configuration()
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()

        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)
        log_handler = start_file_log(self.logger, os.path.join(self.log_path, "{0}_{1}.log.csv".format(self.name, self.timestamp.strftime(wxtofly.get_configuration().log_timestamp_format))))

        try:
            self.logger.info("Starting job: {0}".format(self.name))

            # determine init time for this job
            init_hour_utc = self.determine_init_time()
            if self.init_hour_utc is None:
                self.init_hour_utc = init_hour_utc
            self.logger.debug("Init hour: {0:02}".format(init_hour_utc))

            if init_hour_utc != self.init_hour_utc:
                self.logger.info("Job {0} not for current model init hour {1} - Skipping".format(job.name, init_hour_utc))
                return

            # GRIB is not available at model init time
            # wait at least until wxtofly_configuration.start_time_offset after the init time
            utc_start_time = datetime.datetime.combine(self.init_date_utc, datetime.time(hour=self.init_hour_utc)) + datetime.timedelta(minutes=wxtofly_configuration.start_time_offset)
            job_start_datetime_utc = datetime.datetime.utcnow()
            self.logger.debug("Job start time: UTC {0}".format(job_start_datetime_utc))
            self.logger.debug("Job min start time: UTC {0}".format(utc_start_time))
            if utc_start_time > job_start_datetime_utc:
                wait_time = (utc_start_time - job_start_datetime_utc)
                self.logger.info("Wait time: {0}".format(wait_time))
                wait(wait_time.total_seconds())
                self.logger.debug("Resuming job after wait. Current time: {0}".format(datetime.datetime.utcnow()))


            # initialize model run object
            # and run simulation
            # it creates run.log in run directory
            if self.run_output_path is None:
                self.run_output_path = Region.get_run_output_path(self.region.name, self.init_date_utc, self.init_hour_utc, self.forecast_day)
            self.logger.info("Starting WRF model simulation")
            start_time = time.time()

            parent_output_path = None
            if self.nested:
                parent_output_path = self.get_parent_output_path()
                self.logger.info("Parent region output path: {0}".format(parent_output_path))

            run_model(self.region, self.init_date_utc, self.init_hour_utc, self.forecast_day, self.run_output_path, nested=self.nested, parent_output_path=parent_output_path, fn_state_change=fn_state_change)
            self.logger.info("Finished WRF model simulation in {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))

            if self.nested:
                # when nested WRFOUT files have d01 for nested domain
                # rename WRFOUT files to indicate the correct domain
                inc_wrfout_files_domain(self.run_output_path)

            if not fn_state_change is None:
                fn_state_change("postprocess", "start")
            self.postprocess(fn_state_change=fn_state_change)
            if not fn_state_change is None:
                fn_state_change("postprocess", "end")
        except Exception as e:
            log_exception("job failed", e, self.logger)
            raise
        finally:
            stop_file_log(self.logger, log_handler)
            

    def redo_postprocess(self):
        if not os.path.exists(self.run_output_path):
            self.logger.error("Run output path {0} not found".format(self.run_output_path))
            raise FileNotFoundError(errno.ENOENT,  os.strerror(errno.ENOENT), self.run_output_path)

        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()
        log_handler = start_file_log(self.logger, os.path.join(self.log_path, "redo_{0}_{1}.log.csv".format(self.name, self.timestamp.strftime(wxtofly.get_configuration().log_timestamp_format))))

        try:
            self.postprocess()
        except Exception as e:
            log_exception("postprocess redo failed", e, self.logger)
            raise
        finally:
            stop_file_log(self.logger, log_handler)


    def postprocess(self, fn_state_change=None):
        wxtofly_configuration = wxtofly.get_configuration()

        #init publish log
        publish_log_handler = start_file_log(rasp.postprocess.publish.get_logger(), os.path.join(self.log_path, "{0}_{1}.publish.log.csv".format(self.name, self.timestamp.strftime(wxtofly_configuration.log_timestamp_format))))

        try:
            self.publish_domains_geojson()

            if wxtofly_configuration.postprocessing.blipspot.grid or wxtofly_configuration.postprocessing.blipspot.sites:
                self.postprocess_raspout()

            # prepare stuff for windgrams which is common for all domains
            if wxtofly_configuration.postprocessing.windgrams.enabled:
                if not fn_state_change is None:
                    fn_state_change("windgrams", "start")
                self.postprocess_windgrams()
                if not fn_state_change is None:
                    fn_state_change("windgrams", "end")

            if wxtofly_configuration.postprocessing.windgrams.enabled:
                if not fn_state_change is None:
                    fn_state_change("plots", "start")
                self.postprocess_plots()
                if not fn_state_change is None:
                    fn_state_change("plots", "end")

            if wxtofly_configuration.postprocessing.blipspot.grid:
                if not fn_state_change is None:
                    fn_state_change("blipspot", "start")
                self.postprocess_blipspots()
                if not fn_state_change is None:
                    fn_state_change("blipspot", "end")

        finally:
            if wxtofly_configuration.upload_run_logs:
                self.publish_logs()
            stop_file_log(rasp.postprocess.publish.get_logger(), publish_log_handler)

    def get_encoded_name(self):
        enc_name = self.name.replace(':', '.')
        enc_name = enc_name.replace('+', '.p.')
        return enc_name

    def publish_logs(self):
        try:
            self.logger.debug('collecting job logs')
            metadata = {
                'logs': []
                }
            for path in Path(self.run_output_path).rglob('*.csv'):
                metadata['logs'].append(path.name)
                add_to_queue(path.resolve(), 'logs/{0}/{1}'.format(self.get_encoded_name(), path.name))
            for path in Path(self.run_output_path).rglob('*.log'):
                metadata['logs'].append(path.name)
                add_to_queue(path.resolve(), 'logs/{0}/{1}'.format(self.get_encoded_name(), path.name))
            for path in Path(self.run_output_path).rglob('*.out'):
                metadata['logs'].append(path.name)
                add_to_queue(path.resolve(), 'logs/{0}/{1}'.format(self.get_encoded_name(), path.name))

            add_to_queue(os.path.join(self.run_output_path, 'namelist.wps'), 'logs/{0}/namelist.wps'.format(self.get_encoded_name()))
            metadata['logs'].append('namelist.wps')
            
            add_to_queue(os.path.join(self.run_output_path, 'namelist.input'), 'logs/{0}/namelist.input'.format(self.get_encoded_name()))
            metadata['logs'].append('namelist.input')

            publish_json(metadata, os.path.join(self.run_output_path, 'logs.json'), 'logs/{0}/logs.json'.format(self.get_encoded_name()))
        except Exception as e:
            log_exception("publishing job logs failed", e, self.logger)


    def publish_domains_geojson(self):

        geojson_path = os.path.join(self.region.static_data_path, "domains.geo.json")
        rel_url = wxtofly.get_configuration().web.get_region_rel_path(self.region_name, os.path.basename(geojson_path))

        if os.path.exists(geojson_path):
            add_to_queue(geojson_path, rel_url)
            return 

        self.logger.debug('creating domains geojson')
        geojson = {'type':'FeatureCollection', 'features':[]}
        wps_namelist = WPSNamelist(os.path.join(self.run_output_path, 'namelist.wps'))

        for domain_id in range(self.postprocess_start_domain, self.region.max_dom + 1):
            self.logger.debug('  domain: d{0:02}'.format(domain_id))
            projection = wps_namelist.get_grid_projection(domain_id)
            e_we = wps_namelist.geogrid.e_we[domain_id - 1]
            e_sn = wps_namelist.geogrid.e_sn[domain_id - 1]

            feature = {
                'type': 'Feature',
                'properties': {
                    'name': 'd{0:02}'.format(domain_id) ,
                    'id': domain_id,
                    'dx': round(projection.dx, 3),
                    'e_we': e_we,
                    'e_sn': e_sn
                    },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [] } }
            feature['geometry']['coordinates'].append(get_domain_polygon_path(projection, e_we, e_sn))
            geojson['features'].append(feature)

        publish_json(geojson, geojson_path, rel_url)


    def get_escaped_run_dir_name(self):
        """Function returns escaped run output path
        This value is used in publish URL and currently only replaces '+' with '_'
        """
        return os.path.basename(self.run_output_path).replace('+', '_')

    def get_wrfout_files(self, domain_id):
        return list_wrfout_files(self.run_output_path, domain_id, self.region.get_forecast_start_datetime_utc(self.forecast_date), self.region.get_forecast_end_datetime_utc(self.forecast_date))


    def postprocess_site_blipspots(self, sites, output_path, rel_publish_url=None, decimals=2):
        if self.raspout_output_path is None:
            self.raspout_output_path = os.path.join(self.run_output_path, 'rasp')

        self.logger.debug("Creating BLIPSPOT JSON files for region sites")
        self.logger.debug("Run output path: {0}".format(self.run_output_path))
        wxtofly_configuration = wxtofly.get_configuration()
        wps_namelist = WPSNamelist(os.path.join(self.run_output_path, 'namelist.wps'))
        valid_variables = get_validated_variables(wxtofly_configuration.postprocessing.blipspot.variables, False, logger=self.logger)
        if rel_publish_url is None:
            rel_publish_url = wxtofly_configuration.web.get_region_rel_path(
                self.region_name,
                "windgrams/{0}/{1}".format(self.forecast_date.strftime(wxtofly_configuration.upload_date_format), self.get_escaped_run_dir_name()))
        self.logger.debug("Relative publish URL: {0}".format(rel_publish_url))

        for domain_id in range(self.postprocess_start_domain, self.region.max_dom + 1):
        
            self.logger.debug("Creating BLIPSPOT JSON files for region sites for domain d{0:02}".format(domain_id))
            projection = wps_namelist.get_grid_projection(domain_id)
            raspout_files = list_raspout_files(self.raspout_output_path, domain_id)
            raspout_files.sort(key=lambda raspout_file: raspout_file.datetime)
            datasets = []

            times = []

            for raspout_file in raspout_files:
                self.logger.debug("Loading RASPOUT file {0} as NetCDF Dataset".format(raspout_file.filename))
                datasets.append(Dataset(raspout_file.path, 'r'))
                times.append(raspout_file.datetime.astimezone(self.region.local_tzinfo).strftime('%H:%M'))

            self.logger.debug("RASPOUT variables: {0}".format(datasets[0].variables.keys()))

            for site in sites:
                if site.domain_id != domain_id:
                    continue
                i, j = projection.latlon_to_corners_ij(site.latitude, site.longitude)

                self.logger.debug('Extracting data for site {0}'.format(site.name))
                self.logger.debug(' lat: {0}'.format(site.latitude))
                self.logger.debug(' lon: {0}'.format(site.longitude))
                self.logger.debug('   i: {0} ({1})'.format(int(i), i))
                self.logger.debug('   j: {0} ({1})'.format(int(j), j))

                # adjust i,j to array index
                i = int(i - 1)
                j = int(j - 1)

                data = {
                    'i': i,
                    'j': j,
                    'lat': site.latitude,
                    'lon': site.longitude,
                    'name': site.name,
                    'fcstdate': raspout_files[0].datetime.astimezone(self.region.local_tzinfo).strftime('%Y-%m-%d'),
                    'init_hour': self.init_hour_utc,
                    'init_date': self.init_date_utc.strftime('%Y-%m-%d'),
                    'grid': 'd{0:02}'.format(domain_id),
                    'dx': round(projection.dx, decimals),
                    'time': times
                    }

                for variable in valid_variables:
                    data[variable] = [];

                    #special time-less variables
                    if variable == 'terhgt':
                        data[variable] = round(convert_numpy_value(datasets[0].variables[variable][0][j][i]), decimals)
                        continue

                    for d in range(0, len(datasets)):
                        if 'bottom_top' in datasets[d].variables[variable].dimensions:
                            if datasets[d].variables[variable].dtype.kind == 'f':
                                # round float
                                data[variable].append(numpy.round(
                                    convert_numpy_array(datasets[d].variables[variable][0, :, j, i]),
                                    decimals=decimals
                                    ).tolist())
                            else:
                                data[variable].append(convert_numpy_array(datasets[d].variables[variable][0, :, j, i]).tolist())
                        else:
                            if datasets[d].variables[variable].dtype.kind == 'f':
                                data[variable].append(round(convert_numpy_value(datasets[d].variables[variable][0][j][i]), decimals))
                            else:
                                data[variable].append(convert_numpy_value(datasets[d].variables[variable][0][j][i]))

                publish_json(
                    data,
                    os.path.join(output_path, "{0}.json".format(site.name)),
                    '{0}/{1}.json'.format(rel_publish_url, site.name))

            for dataset in datasets:
                dataset.close()


    def postprocess_windgrams(self):
        self.logger.debug("Creating windgrams")

        wxtofly_configuration = wxtofly.get_configuration()
        run_dir_name_escaped = self.get_escaped_run_dir_name()
        postprocess_logger = rasp.postprocess.get_logger()

        # initialize windgrams output path and create it if not exists
        windgram_output_path = create_clean_run_output_subdir(self.run_output_path, 'windgrams')
        rel_windgrams_url = wxtofly_configuration.web.get_region_rel_path(
            self.region_name,
            "windgrams/{0}/{1}".format(self.forecast_date.strftime(wxtofly_configuration.upload_date_format), run_dir_name_escaped))

        self.logger.debug("Loading region sites")
        sites = self.region.get_sites()
        self.logger.debug("Total number of sites: {0}".format(len(sites)))

        # create sites GeoJSON file containing all sites sites
        publish_json(
            create_sites_geojson(sites, list(range(self.postprocess_start_domain, self.region.max_dom + 1))), 
            os.path.join(self.region.base_path, 'sites.geo.json'),
            wxtofly_configuration.web.get_region_rel_path(self.region_name, 'sites.geo.json'))

        # loop over all domains
        for domain_id in range(self.postprocess_start_domain, self.region.max_dom + 1):
            self.logger.info("Post-processing WRF output for domain d{0:02}".format(domain_id))

            # create windgrams
            windgrams_log = start_file_log(postprocess_logger, os.path.join(windgram_output_path, 'windgrams_d{0:02}.log.csv'.format(domain_id)))
            try:
                start_time = time.time()
                plot_windgrams(self.run_output_path, sites, domain_id, windgram_output_path, utc_offset=self.region.utc_offset, timezone=self.region.timezone_id, logger=postprocess_logger)
                self.logger.info("Finished plotting Windgrams in {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))
                
                # add windgrams to publish queue
                add_to_queue(windgram_output_path, rel_windgrams_url, pattern="*.png")
            finally:
                stop_file_log(postprocess_logger, windgrams_log)

        # create windgrams metadata.json to indicate which forecast date sub folder to use
        publish_json(
            {
                'current': run_dir_name_escaped
            }, 
            os.path.join(windgram_output_path, 'metadata.json'),
            wxtofly_configuration.web.get_region_rel_path(self.region_name, "windgrams/{0}/metadata.json".format(self.forecast_date.strftime(wxtofly_configuration.upload_date_format))))

        if wxtofly_configuration.postprocessing.blipspot.sites:
            self.postprocess_site_blipspots(sites, windgram_output_path, rel_windgrams_url)


    def postprocess_plots(self):
        wxtofly_configuration = wxtofly.get_configuration()
        run_dir_name_escaped = self.get_escaped_run_dir_name()
        postprocess_logger = rasp.postprocess.get_logger()

        for domain_id in range(self.postprocess_start_domain, self.region.max_dom + 1):
            self.logger.info("Post-processing WRF output for domain d{0:02}".format(domain_id))
            wrfout_files = self.get_wrfout_files(domain_id)

            # create variable plots
            # initializxe tiles output path and create it if not exists
            plots_output_path = create_clean_run_output_subdir(self.run_output_path, 'plots', 'd{0:02}'.format(domain_id))
            plots_log = start_file_log(postprocess_logger, os.path.join(plots_output_path, 'plots_d{0:02}.log.csv'.format(domain_id)))

            try:
                self.logger.info("Plotting RASP variables")
                start_time = time.time()
                plot_variables(wrfout_files, self.region, wxtofly_configuration.postprocessing.plots.variables, plots_output_path, logger=postprocess_logger)
                self.logger.info("Finished plotting RASP variables in {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))
                self.add_plots_to_queue(wrfout_files, plots_output_path, run_dir_name_escaped)

            finally:
                stop_file_log(postprocess_logger, plots_log)

    # upload plots to /[REGION]/plots/[DOMAIN]/[DATE]/[RUN]/[TIME]/[VAR].body.png
    # create run metadata.json in /[REGION]/plots/[DOMAIN]/[DATE]/metadata.json
    # create times metadata.json in /[REGION]/plots/[DOMAIN]/[DATE]/[RUN]/metadata.json
    def add_plots_to_queue(self, wrfout_files, plots_output_path, run_dir_name_escaped):
        # get the domain staggered grid bounds from first WRFOUT file
        grid_bounds = wrfout_files[0].get_staggered_bounds()
        # relative upload url
        rel_plots_url = wxtofly.get_configuration().web.get_region_rel_path(self.region.name, "plots/d{0:02}".format(wrfout_files[0].domain_id))

        for date_dir in get_direct_subdirectories(plots_output_path):

            # add plots to upload queue
            add_to_queue(os.path.join(plots_output_path, date_dir), "{0}/{1}/{2}".format(rel_plots_url, date_dir, run_dir_name_escaped), pattern="*.png")

            # save metadata as json and add to upload queue
            publish_json(
                {
                'date': date_dir,
                'times': get_direct_subdirectories(os.path.join(plots_output_path, date_dir)),
                'variables': wxtofly.get_configuration().postprocessing.plots.variables,
                'timestamp': int(time.time()),
                'region': self.region.name,
                'init_date': "{0:%Y%m%d}".format(self.init_date_utc),
                'init_time': self.init_hour_utc,
                'data_source': self.region.grib_source.name,
                'data_description': self.region.grib_source.description,
                'bounds': {
                    'north': grid_bounds[0][1],
                    'south': grid_bounds[0][0],
                    'west': grid_bounds[1][0],
                    'east': grid_bounds[1][1],
                    }
                },
                os.path.join(plots_output_path, date_dir, 'metadata.json'),
                '{0}/{1}/{2}/metadata.json'.format(rel_plots_url, date_dir, run_dir_name_escaped))

            # create run metadata
            publish_json({
                'current': run_dir_name_escaped
                }, 
                os.path.join(plots_output_path, 'metadata.json'),
                '{0}/{1}/metadata.json'.format(rel_plots_url, date_dir))


    def postprocess_raspout(self):
        wxtofly_configuration = wxtofly.get_configuration()
        postprocess_logger = rasp.postprocess.get_logger()
        self.raspout_output_path = create_clean_run_output_subdir(self.run_output_path, 'rasp')

        variables = []
        variables.extend(wxtofly_configuration.postprocessing.blipspot.variables)
        variables.extend(wxtofly_configuration.postprocessing.plots.variables)
        variables = list(set(variables))

        for domain_id in range(self.postprocess_start_domain, self.region.max_dom + 1):
            # create RASPOUT files
            raspout_log = start_file_log(postprocess_logger, os.path.join(self.raspout_output_path, 'raspout_d{0:02}.log.csv'.format(domain_id)))
            try:
                self.logger.info("Calculating RASP variables")
                start_time = time.time()
                raspout_files = create_raspout_files(self.get_wrfout_files(domain_id), variables, self.raspout_output_path)
                self.logger.info("Finished calculating RASP variables in {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))
            finally:
                stop_file_log(postprocess_logger, raspout_log)
            pass

    def postprocess_blipspots(self):
        wxtofly_configuration = wxtofly.get_configuration()

        for domain_id in range(self.postprocess_start_domain, self.region.max_dom + 1):
            # create blipspot JSON files
            #if wxtofly_configuration.postprocessing.blipspot.generate_json:
            #    blipspot_output_path = create_clean_run_output_subdir(self.run_output_path, 'blipspot', 'd{0:02}'.format(domain_id))
            #    blipspot_log = start_file_log(blipspot_logger, os.path.join(raspout_output_path, 'blipspot_d{0:02}.log.csv'.format(domain_id)))
            #    try:
            #        self.logger.info("Generating BLIPSPOT  data files")
            #        start_time = time.time()
            #        create_blipspot_json_parallel(
            #            raspout_files,
            #            region.local_tzinfo,
            #            wxtofly_configuration.postprocessing.variables,
            #            blipspot_output_path
            #            )
            #        self.logger.info("Finished generating BLIPSPOT data in {0}".format(datetime.timedelta(seconds = (time.time() - start_time))))
            #        rel_blipspot_url = wxtofly_configuration.web.get_region_rel_path(
            #            self.region_name, "blipspot/{0}/d{1:02}".format(
            #            self.forecast_date.strftime(wxtofly_configuration.upload_date_format),
            #            domain_id))
            #        add_to_queue(blipspot_output_path, rel_blipspot_url, pattern="*.json")
            #    finally:
            #        stop_file_log(blipspot_logger, blipspot_log)            
            pass
