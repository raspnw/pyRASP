from wxtofly import logger as wxtofly_logger
from rasp.modelrun import logger as modelrun_logger
from rasp.common.logging import start_file_log, stop_file_log

if __name__ == '__main__':
    wxtofly_log = start_file_log(wxtofly_logger, 'wxtofly.log.csv')
    run_log = start_file_log(modelrun_logger, 'run.log.csv')
    wxtofly_logger.debug('wxtofly debug')
    wxtofly_logger.info('wxtofly info')
    modelrun_logger.debug('run debug')
    modelrun_logger.info('run info')
    stop_file_log(wxtofly_logger, wxtofly_log)
    stop_file_log(modelrun_logger, run_log)