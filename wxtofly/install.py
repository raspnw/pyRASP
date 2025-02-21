import sys
import os

import wxtofly
from wxtofly.setup.cron import schedule_heartbeat, schedule_wxtofly_run
from wxtofly.setup.ftplogin import add_ftp_login

logger = wxtofly.get_logger()

logger.info('Configuring .netrc')
add_ftp_login('wxtofly.net', 'olneytj', 'tigermt56&')

logger.info('Scheduling Heartbeat cron job')
schedule_heartbeat()

logger.info('Scheduling WxToFly run job')
schedule_wxtofly_run()
