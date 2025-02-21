import logging
wxtofly_setup_logger = None

def get_logger():
    global wxtofly_setup_logger
    if wxtofly_setup_logger is None:
        wxtofly_setup_logger = logging.getLogger('wxtofly.setup')
    return wxtofly_setup_logger
