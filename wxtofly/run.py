# get machine config
# update region config
# update region sites
# run model
# do windgrams
# delete old windgrams
# upload windgrams
# do tiles
# delete old tiles
# upload tiles

import os
import sys
import json
import datetime
import time
import shutil
import logging
import glob
from socket import gethostname
from collections import OrderedDict

import wxtofly
from wxtofly.job import Job, create_job_from_run_output_path
from wxtofly.utils.loghandler import start_file_upload_log, stop_file_upload_log
from wxtofly.utils.process import kill_all
from wxtofly.utils.cleanup import cleanup_ftp_server
from wxtofly.utils.update import update_jobs_json, update_sites_json
from wxtofly.utils.variables import upload_variables_js
from wxtofly.setup.cron import update_cron_schedule
from wxtofly.utils.postprocess import publish_json

import rasp
from rasp.region import Region
from rasp.common.logging import log_exception, start_file_log, stop_file_log
from rasp.common.system import cleanup_path
from rasp.postprocess.publish.publishqueue import init_publishing, reset_total_queued, get_total_queued

logger = wxtofly.get_logger()
log_path = os.path.join(rasp.configuration.base_path, 'logs')
hostname = gethostname()
jobs_info = {}
job_run_info = None

def init_file_log(timestamp):
    cleanup_path(log_path, wxtofly.get_configuration().files_max_age_hours, logger=logger)
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    return start_file_log(logger, os.path.join(log_path, "wxtofly_{0}.log.csv".format(timestamp.strftime(wxtofly.get_configuration().log_timestamp_format))))


def add_jobs(jobs_dict, data, timestamp):
    """ function adds a new Job item to ordered jobs dictionary """
    for job_name in data:
        if not job_name in jobs_dict:
            try:
                logger.debug("Adding job: {0}".format(job_name))
                jobs_dict[job_name] = Job(job_name, timestamp=timestamp, logger=logger)
            except Exception as e:
                log_exception("Creating job failed".format(job_name), e, logger)
        else:
            logger.warning("Detected duplicate job: {0}".format(job_name))

# function performs postprocessing for existing run data
def redo_job_postprocess(region_name):
    timestamp = datetime.datetime.now()
    log_handler = init_file_log(timestamp)

    try:
        kill_all(logger)
        init_publishing()

        # find latest folder in region run path
        run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
        logger.debug("Redoing postprocess for path {0}".format(run_output_path))
        job = create_job_from_run_output_path(run_output_path)
        job.redo_postprocess()
    except Exception as e:
        log_exception("Postprocess redo failed", e, logger)
    finally:
        stop_file_log(logger, log_handler)

# function performs postprocessing for existing run data
def redo_job_windgrams(region_name):
    timestamp = datetime.datetime.now()
    log_handler = init_file_log(timestamp)

    try:
        #kill_all(logger)
        #init_publishing()

        # find latest folder in region run path
        run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
        logger.debug("Redoing postprocess for path {0}".format(run_output_path))
        job = create_job_from_run_output_path(run_output_path)
        job.postprocess_windgrams()
    except Exception as e:
        log_exception("Postprocess redo failed", e, logger)
    finally:
        stop_file_log(logger, log_handler)


def redo_job_site_blipspots(region_name):
    """Function performs postprocessing for existing run data"""
    timestamp = datetime.datetime.now()
    log_handler = init_file_log(timestamp)

    try:
        #kill_all(logger)
        #init_publishing()

        # find latest folder in region run path
        run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
        logger.debug("Redoing postprocess for path {0}".format(run_output_path))
        job = create_job_from_run_output_path(run_output_path)
        job.postprocess_site_blipspots(job.region.get_sites(), os.path.join(run_output_path, 'windgrams'))
    except Exception as e:
        log_exception("Postprocess redo failed", e, logger)
    finally:
        stop_file_log(logger, log_handler)


def redo_job_raspout(region_name):
    """Function performs postprocessing for existing run data"""
    timestamp = datetime.datetime.now()
    log_handler = init_file_log(timestamp)

    try:
        #kill_all(logger)
        #init_publishing()

        # find latest folder in region run path
        run_output_path = max(glob.glob(os.path.join(Region.get_run_base_path(region_name), '*/')), key=os.path.getmtime)
        logger.debug("Redoing postprocess for path {0}".format(run_output_path))
        job = create_job_from_run_output_path(run_output_path)
        job.postprocess_raspout()
    except Exception as e:
        log_exception("Postprocess redo failed", e, logger)
    finally:
        stop_file_log(logger, log_handler)

def run_state_change(stage, state):
    global job_run_info
    global jobs_info

    if not stage in job_run_info['run']:
        job_run_info['run'][stage] = {}
    job_run_info['run'][stage][state] = int(time.time() * 1000)
    publish_jobs_info(jobs_info)

def run_job(job, test_run=False):
    global job_run_info

    """ function executes a job """
    wxtofly_configuration = wxtofly.get_configuration()

    # remove old logs and runs for this region
    cleanup_path(job.log_path, wxtofly_configuration.files_max_age_hours, logger=logger)
    cleanup_path(Region.get_run_base_path(job.region_name), wxtofly_configuration.files_max_age_hours, logger=logger)
    # removes old forecast files from FTP server
    cleanup_ftp_server(job.region, history_days=2, logger=logger)
    update_sites_json(job.region, logger=logger)
    job.run(fn_state_change=run_state_change)

def update_files():
    upload_variables_js(logger=logger)

def publish_jobs_info(jobs_info):
    publish_json(jobs_info, os.path.join(log_path, 'jobs.json'), '/logs/{0}.jobs.json'.format(hostname))

def wxtofly_run(job_name=None, update_cron=False):
    global jobs_info
    global job_run_info

    wxtofly_configuration = wxtofly.get_configuration()

    # catpute run start time and initialize init_date for model run
    Job.set_run_start_time()

    # init wxtofly log
    timestamp = datetime.datetime.now()
    log_handler = init_file_log(timestamp)

    # brute-force cleanup before a new run
    # - kill all python processes
    # - delete publishing FIFO
    kill_all(logger)
    init_publishing()

    if wxtofly_configuration.live_log:
        json_handler = start_file_upload_log(logger, logging.DEBUG)

    try:
        logger.info("Staring WxToFLy run")

        # clean publish queue path
        publish_configuration = rasp.postprocess.publish.get_configuration()
        shutil.rmtree(publish_configuration.upload_queue_path)
        os.mkdir(publish_configuration.upload_queue_path)

        if job_name is None:
            # initialize jobs.json path and upadte from server if available
            jobs_json_path = os.path.join(wxtofly.data_path, 'jobs.json')
            update_jobs_json(jobs_json_path, logger=logger)

            # read jobs.json file
            with open(jobs_json_path, 'rt') as f:
                json_data = json.load(f)

            # find the jobs for this machine from the jobs.json data
            jobs = OrderedDict()
            for data in json_data:
                if hostname.lower() == data['machine'].lower():
                    add_jobs(jobs, data['jobs'], timestamp)
                    break

            if len(jobs) == 0:
                logger.warning("No jobs found for machine {0}".format(hostname))
                if update_cron:
                    schedule_wxtofly_run()

            if update_cron:
                update_cron_schedule(jobs)

        else:
            logger.debug("Performing run for single job: {0}".format(job_name))
            jobs = OrderedDict()
            add_jobs(jobs, [job_name], timestamp)
            handle_exception = False

        # init jobs info and upload to server
        for job in jobs.values():
            jobs_info[job.name] = {
                'region': job.region.name,
                'state': 'queued',
                'start': None,
                'end': None,
                'run': {},
                'published': 0
                }
        publish_jobs_info(jobs_info)

        # update various wxtofly files on server
        update_files()

        # execute jobs in the same order as in jobs.json
        for job in jobs.values():
            reset_total_queued()
            try:
                jobs_info[job.name]['start'] = int(time.time() * 1000)
                jobs_info[job.name]['state'] = 'running'
                publish_jobs_info(jobs_info)
                job_run_info = jobs_info[job.name]
                run_job(job)
                jobs_info[job.name]['end'] = int(time.time() * 1000)
                jobs_info[job.name]['state'] = 'finished'
            except Exception as e:
                log_exception("Job {0} failed".format(job.name), e, logger)
                jobs_info[job.name]['end'] = int(time.time() * 1000)
                jobs_info[job.name]['state'] = 'failed'
            jobs_info[job.name]['published'] = get_total_queued()
            publish_jobs_info(jobs_info)
        logger.info("Finished WxToFLy run")

    except Exception as e:
        log_exception("WxToFly run failed", e, logger)
    finally:
        stop_file_log(logger, log_handler)
        if wxtofly_configuration.live_log:
            stop_file_upload_log(logger, json_handler)
        pass

if __name__ == "__main__":
    job_name = None
    update_cron = not sys.stdout.isatty()

    if len(sys.argv) > 1:
        job_name = sys.argv[1]

    wxtofly_run(job_name, update_cron=update_cron)