import os
import datetime
import errno
import glob

import rasp

from rasp.modelrun.grib import cleanup_grib_download_folder
from rasp.modelrun.grib.download import create_grib_download_list
from rasp.modelrun.grib.downloadmanager import download_all
from rasp.modelrun.wps.ungrib import run_ungrib, delete_ungrib_files
from rasp.modelrun.wps.metgrid import run_metgrid
from rasp.modelrun.wps.geogrid import run_geogrid
from rasp.modelrun.wps.namelist import create_wps_namelist, WPSNamelist
from rasp.modelrun.wrf.namelist import create_input_namelist
from rasp.modelrun.wrf.real import run_real
from rasp.modelrun.wrf.ndown import run_ndown
from rasp.modelrun.wrf.wrf import run_wrf
from rasp.common.logging import start_file_log, stop_file_log
from rasp.common.system import create_file_symlink

class ModelRunException(Exception):
    pass

def get_forecast_date(init_date_utc, forecast_day):
    return init_date_utc + datetime.timedelta(days = forecast_day)

def check_wrfout_files(region, input_namelist, forecast_date, output_path, logger=rasp.modelrun.get_logger()):
    """
    Verify existence of all WRFOUT files for the final domain
    and create a list of files relevant to the region forecast period
    """
    logger.debug("Checking WRFOUT files")

    forecast_start_datetime = datetime.datetime.combine(forecast_date, datetime.time(hour = region.configuration.forecast.start_hour_local))
    logger.debug('forecast_start_datetime: {0:%Y-%m-%d_%H:%M:%S}'.format(forecast_start_datetime))

    # start from start date/time of the final domain
    wrfout_datetime = input_namelist.timecontrol.start_datetimes[input_namelist.domains.max_dom - 1]
    while  (wrfout_datetime <= input_namelist.timecontrol.end_datetimes[input_namelist.domains.max_dom - 1]):
        #logger.debug('wrfout_datetime: {0:%Y-%m-%d_%H:%M:%S}'.format(wrfout_datetime))
        filename = "wrfout_d{0:02d}_{1:%Y-%m-%d_%H:%M:%S}".format(input_namelist.domains.max_dom, wrfout_datetime)
        wrfout_file_path = os.path.join(output_path, filename)
        if not os.path.exists(wrfout_file_path):
            raise FileNotFoundError(errno.ENOENT, "WRFOUT file {0} not found".format(filename), wrfout_file_path)
        logger.debug("File found: {0}".format(filename))
        wrfout_datetime += datetime.timedelta(minutes = rasp.modelrun.get_configuration().wrf.history_interval)

def run_model(region, init_date_utc, init_hour_utc, forecast_day, output_path, log_path = None, nested=False, parent_output_path = None, fn_state_change=None, logger=rasp.modelrun.get_logger()):
    """
    Performs a simulation run for a region

    The input data initialization date and time are determined by init_date_utc and init_hour_utc

    init_hour_utc is the input data initialization time in hours UTC
    the initialization date is the value of init_date_utc argument

    init_date_utc cannot be a future date (UTC time) 

    Simulation (forecast) time range is determined base on region settings. The date is 
    calculated as input data initiation date plus forecast_day

    forecast_day must be positive number and is the delta days between forecast date and 
    input data init date
    """

    if not os.path.exists(output_path):
        os.makedirs(output_path)


    # set log path to output path if not specified
    if not log_path:
        log_path = output_path

    # start run log
    run_log = start_file_log(logger, os.path.join(log_path, 'run.log.csv'))
    grib_log = start_file_log(rasp.modelrun.grib.get_logger(), os.path.join(log_path, 'grib.log.csv'))
    
    try:
        logger.info("Model run start: region={0}".format(region.name))
        logger.debug("Run output path: {0}".format(output_path))
        logger.info("Initialization data date: {0:%Y-%m-%d}".format(init_date_utc))
        logger.info("Initialization time: {0}z".format(init_hour_utc))
        logger.info("Forecast day: {0}".format(forecast_day))

        # check input values
        if nested:
            logger.debug("Model run for nest of: {0}".format(region.configuration.parent_region))
            if not region.configuration.parent_region:
                raise ModelRunException("Region {0} has no parent region".format(region.name))
            if not parent_output_path:
                raise ModelRunException("Parent region run output path must be provided for nested run")
            if not os.path.exists(parent_output_path):
                raise ModelRunException("Parent region run output path {0} does not exists".format(parent_output_path))
        if forecast_day < 0:
            raise ModelRunException("forecast_day must be equal or greater than 0")
        if not isinstance(init_date_utc, datetime.date):
            raise ModelRunException("init_date_utc is not of type date")
        if init_date_utc > datetime.datetime.utcnow().date():
            raise ModelRunException("init_date_utc cannot be in the future")

        # create namelist.wps in run output path
        forecast_date = get_forecast_date(init_date_utc, forecast_day)
        logger.info("Forecast date: {0:%Y-%m-%d}".format(forecast_date))
        wps_namelist = create_wps_namelist(
            region,
            forecast_date,
            output_path)

        # run geogrid
        if not fn_state_change is None:
            fn_state_change("geogrid", "start")
        run_geogrid(region, wps_namelist, output_path, log_path)
        if not fn_state_change is None:
            fn_state_change("geogrid", "end")

        if nested:
            delete_ungrib_files(output_path)

            #link parent ungrib files
            logger.debug("Link parent region ungrib files")
            for f in glob.glob(os.path.join(parent_output_path, "{0}:*".format(WPSNamelist.ungrib_prefix))):
                create_file_symlink(f, os.path.join(output_path, os.path.basename(f)))

            # copy WPS start and end times from parent namelist.wps
            # this is necessary in case the start time was adjusted during grib download
            parent_wps_namelist = WPSNamelist(os.path.join(parent_output_path, 'namelist.wps'), logger=logger)
            for i in range(len(wps_namelist.share.start_datetimes)):
                # start and end time is the same
                wps_namelist.share.start_datetimes[i] = parent_wps_namelist.share.start_datetimes[0]
                wps_namelist.share.end_datetimes[i] = parent_wps_namelist.share.end_datetimes[0]

        else:
            if not fn_state_change is None:
                fn_state_change("grib_download", "start")
            #cleanup grib download locations
            cleanup_grib_download_folder(region.filtered_grib_download_path)
            cleanup_grib_download_folder(rasp.modelrun.get_configuration().grib.unfiltered_download_path)

            # obtain list of grib download item
            grib_download_list = create_grib_download_list(region, wps_namelist, init_date_utc, init_hour_utc)

            # download all files
            download_all(grib_download_list)

            # run ungrib
            run_ungrib(region, wps_namelist, grib_download_list, output_path, log_path)
            if not fn_state_change is None:
                fn_state_change("grib_download", "end")

        #run metgrid
        if not fn_state_change is None:
            fn_state_change("metgrid", "start")
        run_metgrid(region, wps_namelist, output_path, log_path)
        if not fn_state_change is None:
            fn_state_change("metgrid", "end")

        #create namelist.input
        input_namelist = create_input_namelist(region, wps_namelist, output_path)

        # run real
        if not fn_state_change is None:
            fn_state_change("real", "start")
        run_real(output_path, log_path)
        if not fn_state_change is None:
            fn_state_change("real", "end")

        if nested:
            #link parent's final grid wrfout files
            logger.debug("Link parent region wrfout files")
            for f in glob.glob(os.path.join(parent_output_path, "wrfout_d*".format(wps_namelist.share.max_dom - 1))):
                create_file_symlink(f, os.path.join(output_path, "wrfout_d01{0}".format(os.path.basename(f)[10:])))

            # run ndown
            if not fn_state_change is None:
                fn_state_change("ndown", "start")
            run_ndown(wps_namelist, input_namelist, output_path, log_path)
            if not fn_state_change is None:
                fn_state_change("ndown", "end")

        #run wrf
        if not fn_state_change is None:
            fn_state_change("wrf", "start")
        run_wrf(output_path, log_path)
        if not fn_state_change is None:
            fn_state_change("wrf", "end")

        check_wrfout_files(region, input_namelist, forecast_date, output_path)

    except Exception as e:
        logger.error("ERROR: {0}".format(e))
        raise
    finally:
        stop_file_log(logger, run_log)
        stop_file_log(rasp.modelrun.grib.get_logger(), grib_log)