import logging
import datetime

import rasp
from rasp.postprocess.publish import get_configuration as get_publish_configuration
from rasp.common.ftp import FTPHelper
import wxtofly

def cleanup_ftp_server(region, history_days=0, logger=wxtofly.get_logger()):
    """ function removes old forecast entries from FTP server """
    logger.debug("Removing old forecast data for region {0}".format(region.name))

    wxtofly_configuration = wxtofly.get_configuration()

    ftp_path = wxtofly_configuration.web.get_region_rel_path(region.name, 'windgrams')
    ftp_remove_old_forecast(ftp_path, history_days=history_days, logger=logger)

    for d in range(1, region.max_dom + 1):
        ftp_path = wxtofly_configuration.web.get_region_rel_path(region.name, 'plots/d{0:02}'.format(d))
        ftp_remove_old_forecast(ftp_path, history_days=history_days, logger=logger)


def ftp_remove_old_forecast(ftp_path, history_days=0, logger=wxtofly.get_logger()):
    """ function removes old forecast entries from FTP server """

    logger.debug("Removing old forecast data in path {0}".format(ftp_path))
    max_date = datetime.date.today()
    max_date -= datetime.timedelta(days=history_days)

    publish_configuration = get_publish_configuration()
    with FTPHelper(
        publish_configuration.ftp.server,
        publish_configuration.ftp.root_path) as ftp:

        if ftp.rel_path_exists(ftp_path):
            for dirname in ftp.rel_list_dir(ftp_path):
                try:
                    dir_date = datetime.datetime.strptime(dirname, wxtofly.get_configuration().upload_date_format).date()
                except Exception as e:
                    logger.error("Unable to parse directory name {0} in {0}/{1}: {2}".format(ftp_path, dirname, e))
                    continue

                if dir_date < max_date:
                    rm_path = "{0}/{1}".format(ftp_path, dirname)
                    logger.debug("Removing FTP directory {0}".format(rm_path))
                    try:
                        ftp.rel_rmtree(rm_path)
                    except Exception as e:
                        logger.warning("Unable to remove {0}: {1}".format(rm_path, e))
