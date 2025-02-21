import os
import logging

import rasp
from rasp import configuration_path
from rasp.configuration import BaseConfiguration, BaseSectionConfiguration

postprocess_logger = None
postprocess_configuration = None

class NCLConfiguration(BaseSectionConfiguration):
    def __init__(self, config_dict):
        super().__init__(config_dict)

        self.root_path = self.get_path('root_path')
        self.script_path = self.get_path('script_path')
        self.drjack_lib = self.get_path('drjack_lib')
        self.rangs_path = self.get_path('rangs_path', optional=True)
        self.colormap_path = self.get_path('colormap_path')

#class TilesConfiguration(BaseSectionConfiguration):
#    def __init__(self, config_dict):
#        super().__init__(config_dict)

#        self.max_tasks = self.get_value('max_tasks', optional=True, default=os.cpu_count())
#        self.ncl_colormap = self.get_value('ncl_colormap')

#        zoom = self.get_section('zoom')
#        self.zoom_min = zoom.get_value('min')
#        self.zoom_max = zoom.get_value('max')

class PostProcessConfiguration(BaseConfiguration):
    def __init__(self):
        super().__init__(os.path.join(configuration_path, 'postprocess.yaml'))

        self.ncl = NCLConfiguration(self.config_dict['ncl'])
        #self.tiles = TilesConfiguration(self.config_dict['tiles'])
        
def get_configuration():
    global postprocess_configuration
    if postprocess_configuration == None:
        postprocess_configuration = PostProcessConfiguration()
    return postprocess_configuration

def get_logger():
    global postprocess_logger
    if postprocess_logger == None:
        postprocess_logger = logging.getLogger('rasp.postprocess')
    return postprocess_logger