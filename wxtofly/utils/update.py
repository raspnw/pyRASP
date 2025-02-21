import os
import logging
import shutil

import wxtofly
import rasp
from rasp.common.download import download_file
from rasp.common.logging import log_exception
from rasp.region import Region


def update_jobs_json(jobs_json_path, logger=wxtofly.get_logger()):
    wxtofly_configuration = wxtofly.get_configuration()
    publish_configuration = rasp.postprocess.publish.get_configuration()
    """ function downloads jobs.json file from server if available """
    logger.debug("Updating jobs JSON configuration")
    try:
        if (publish_configuration.method == 'copy'):
            src = os.path.join(publish_configuration.copy.root_path, wxtofly_configuration.web.jobs_path)
            logger.debug('copying {0} to {1}'.format(src, jobs_json_path))
            shutil.copyfile(src, jobs_json_path)
        else:
            download_file(wxtofly_configuration.web.jobs_url, jobs_json_path, logger=logger)
    except Exception as e:
        logger.warning("Unable to download {0}: {1}".format(wxtofly_configuration.web.jobs_url, e))
        log_exception(None, e, logger)

def update_sites_json(region, logger=wxtofly.get_logger()):
    wxtofly_configuration = wxtofly.get_configuration()
    """ function downloads site files from server if available """
    logger.debug("Updating site files")
    for site_file_name in region.configuration.site_files:
        update_region_file(region.name, site_file_name)

def update_region_file(region_name, filename, logger=wxtofly.get_logger()):
    region_path = Region.get_region_path(region_name)
    wxtofly_configuration = wxtofly.get_configuration()
    try:
        logger.debug("Updating region {0} file {1}".format(region_name, filename))
        download_file(
            wxtofly_configuration.web.get_region_url(region_name, filename), 
            os.path.join(region_path, filename), logger=logger)
    except Exception as e:
        logger.warning("Unable to update {0}: {1}".format(filename, e))

def update_region_files(region_name, logger=wxtofly.get_logger()):
    region_path = Region.get_region_path(region_name)

    if not os.path.exists(region_path):
        logger.debug("Creating region path {0}".format(region_path))
        os.makedirs(region_path)

    for filename in ['namelist.wps', 'region.yaml', 'namelist.input']:
        update_region_file(region_name, filename)



