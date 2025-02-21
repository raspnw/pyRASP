import os
import sys
import logging
import time

from crontab import CronTab

def get_pythonpath():
    import rasp
    import wxtofly

    paths = []
    if 'PYTHONPATH' in os.environ:
        paths = os.environ['PYTHONPATH'].split(':')

    paths.append(os.path.normpath(os.path.join(os.path.dirname(sys.modules['wxtofly'].__file__), '..')))
    paths.append(os.path.normpath(os.path.join(os.path.dirname(sys.modules['rasp'].__file__), '..')))

    paths = list(set(paths))
    return ":".join(paths)


def log_debug(logger):
    logger.debug("CRONTAB:")
    cron = CronTab(user=True)
    for line in cron.lines:
        logger.debug(line)

def clear():
    cron = CronTab(user=True)
    cron.remove_all()
    cron.write()

def schedule_heartbeat(logger=logging.getLogger()):
    cron = CronTab(user=True)

    for job in cron.find_comment('heartbeat'):
        cron.remove(job)
        cron.write()

    import wxtofly.utils.heartbeat
    command = 'python3 {0}'.format(os.path.normpath(sys.modules['wxtofly.utils.heartbeat'].__file__))
    logger.debug("Creating CRONTAB job: {0}".format(command))

    job = cron.new(command=command, comment='heartbeat')
    job.minute.every(5)
    job.env['PYTHONPATH'] = get_pythonpath()
    cron.write()
    log_debug(logger)

def schedule_wxtofly_run(hours=None, logger=logging.getLogger()):
    cron = CronTab(user=True)

    for job in cron.find_comment('wxtofly'):
        cron.remove(job)
        cron.write()

    import wxtofly.run
    command = 'python3 {0}'.format(os.path.normpath(sys.modules['wxtofly.run'].__file__))
    logger.debug("Creating CRONTAB job: {0}".format(command))

    job = cron.new(command=command, comment='wxtofly')
    if hours:
        job.hour.on(*hours)
    else:
        job.hour.every(1)
    job.minute.on(0)
    job.env['PYTHONPATH'] = get_pythonpath()
    cron.write()

    log_debug(logger)

def get_cron_start_hour(cycle_hour, utc_offset):
    hour = cycle_hour + utc_offset + 1
    if hour < 0:
        hour += 24
    if hour >= 24:
        hour -= 24
    return int(hour)

def update_cron_schedule(jobs, logger=logging.getLogger()):
    logger.debug("Updating cron schedule")
    utc_offset = time.localtime().tm_gmtoff / 3600
    logger.debug("Local time UTC offset: {0}".format(utc_offset))
    hours = set()
    for job in jobs.values():
        job_hours = list(get_cron_start_hour(cycle_hour, utc_offset) for cycle_hour in job.region.grib_source.model_cycles)
        logger.debug("GRIB cycle times: {0}".format(job.region.grib_source.model_cycles))
        logger.debug("CRON start times: {0}".format(job_hours))
        hours.update(job_hours)
    schedule_wxtofly_run(list(hours), logger=logger)