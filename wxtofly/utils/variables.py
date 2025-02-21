import os
import json
import tempfile

import wxtofly
import rasp
from rasp.postprocess.publish.publishqueue import add_to_queue

def create_variables_js(local_path, logger=wxtofly.get_logger()):
    variables_configuration = rasp.postprocess.variables.get_configuration()

    variables_json = {}
    for name, config in variables_configuration.variables.items():
        variables_json[name] = {
            'title': config.title,
            'description': config.description,
            }

    with open(local_path, 'wt+') as f:
        f.write('var raspVariables = ')
        json.dump(variables_json, f, indent=2)

def upload_variables_js(logger=wxtofly.get_logger()):
    tmp_path = os.path.join(tempfile.gettempdir(), 'rasp.variables.js')
    create_variables_js(tmp_path)
    add_to_queue(tmp_path, 'js/rasp.variables.js')

