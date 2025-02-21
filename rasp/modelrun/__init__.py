import os
import logging
from rasp.modelrun.configuration import ModelRunConfiguration
from rasp.common.program import run_program

model_run_configuration = None
model_run_logger = None

def ncdump(path, out_path):
    if not os.path.exists(os.path.dirname(out_path)):
        os.makedirs(os.path.dirname(out_path))

    run_program(
        get_configuration().ncdump_path,
        os.path.dirname(get_configuration().ncdump_path),
        out_path,
        [path],
        logger=get_logger())
    
def get_configuration():
    global model_run_configuration
    if model_run_configuration == None:
        model_run_configuration = ModelRunConfiguration()
    return model_run_configuration

def get_logger():
    global model_run_logger
    if model_run_logger == None:
        model_run_logger = logging.getLogger('rasp.model_run')
    return model_run_logger
