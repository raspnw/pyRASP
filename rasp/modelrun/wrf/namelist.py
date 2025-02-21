import os
import shutil
import glob
import datetime
from netCDF4 import Dataset

import rasp
from rasp.modelrun.namelistbase import NamelistBase, NamelistSectionBase

class MetgridData(object):
    def __init__(self, path):
        #read metgrid file
        logger=rasp.modelrun.get_logger()
        logger.debug("Reading metgrid file %s", path)
        nc = Dataset(path, 'r')
        self.num_metgrid_levels = nc.dimensions['num_metgrid_levels'].size
        self.num_metgrid_soil_levels = nc.NUM_METGRID_SOIL_LEVELS
        self.num_land_cat = nc.NUM_LAND_CAT
        nc.close()


class TimeControlNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.run_days = self.section_dict['run_days']
        self.run_hours = self.section_dict['run_hours']
        self.run_minutes = self.section_dict['run_minutes']
        self.run_seconds = self.section_dict['run_seconds']

        self.start_datetimes = self.__get_datetimes('start')
        self.end_datetimes = self.__get_datetimes('end')

        self.interval_seconds = self.section_dict['interval_seconds']
        self.history_interval = self.get_array('history_interval')
        self.adjust_output_times = self.get_array('adjust_output_times')
        self.frames_per_outfile = self.get_array('frames_per_outfile')
        self.restart = self.section_dict['restart']
        self.input_from_file = self.get_array('input_from_file')
        self.fine_input_stream = self.get_opt_value('fine_input_stream')
        self.io_form_history = self.section_dict['io_form_history']
        self.io_form_restart = self.section_dict['io_form_restart']
        self.io_form_input = self.section_dict['io_form_input']
        self.io_form_boundary = self.section_dict['io_form_boundary']
        self.io_form_auxinput2 = self.section_dict.get('io_form_auxinput2')
        self.iofields_filename = self.get_array('fine_input_stream')
        self.ignore_iofields_warning = self.get_opt_value('ignore_iofields_warning', default=True)

        self.debug_level = self.get_opt_value('debug_level', 0)
        
    def set_dictionary_values(self):
        self.section_dict['run_days'] = self.run_days
        self.section_dict['run_hours'] = self.run_hours
        self.section_dict['run_minutes'] = self.run_minutes
        self.section_dict['run_seconds'] = self.run_seconds

        self.__set_times('start', self.start_datetimes)
        self.__set_times('end', self.end_datetimes)

        self.section_dict['interval_seconds'] = self.interval_seconds
        self.section_dict['history_interval'] = self.history_interval
        self.section_dict['adjust_output_times'] = self.adjust_output_times
        self.section_dict['frames_per_outfile'] = self.frames_per_outfile
        self.section_dict['restart'] = self.restart
        self.section_dict['input_from_file'] = self.input_from_file

        if self.fine_input_stream != None:
            self.section_dict['fine_input_stream'] = self.fine_input_stream
        elif 'fine_input_stream' in self.section_dict:
            self.section_dict.pop('fine_input_stream', None)

        self.section_dict['io_form_history'] = self.io_form_history
        self.section_dict['io_form_restart'] = self.io_form_restart
        self.section_dict['io_form_input'] = self.io_form_input
        self.section_dict['io_form_boundary'] = self.io_form_boundary

        if self.io_form_auxinput2 != None:
            self.section_dict['io_form_auxinput2'] = self.io_form_auxinput2
        elif 'io_form_auxinput2' in self.section_dict:
            self.section_dict.pop('io_form_auxinput2', None)

        self.section_dict['debug_level'] = self.debug_level

        if self.iofields_filename:
            self.section_dict['iofields_filename'] = self.iofields_filename
            self.section_dict['ignore_iofields_warning'] = self.ignore_iofields_warning

    def __get_datetimes(self, start_end):
        datetimes = []
        for y, m, d, hr, min, sec in zip(
            self.get_array('{0}_year'.format(start_end)),
            self.get_array('{0}_month'.format(start_end)),
            self.get_array('{0}_day'.format(start_end)),
            self.get_array('{0}_hour'.format(start_end)),
            self.get_array('{0}_minute'.format(start_end)),
            self.get_array('{0}_second'.format(start_end))):
            datetimes.append(datetime.datetime(y, m, d, hr, min, sec))
        return datetimes


    def __set_times(self, start_end, datetimes):
        self.section_dict['{0}_year'.format(start_end)] = []
        self.section_dict['{0}_month'.format(start_end)] = []
        self.section_dict['{0}_day'.format(start_end)] = []
        self.section_dict['{0}_hour'.format(start_end)] = []
        self.section_dict['{0}_minute'.format(start_end)] = []
        self.section_dict['{0}_second'.format(start_end)] = []
        for dt in datetimes:
            self.section_dict['{0}_year'.format(start_end)].append(dt.year)
            self.section_dict['{0}_month'.format(start_end)].append(dt.month)
            self.section_dict['{0}_day'.format(start_end)].append(dt.day)
            self.section_dict['{0}_hour'.format(start_end)].append(dt.hour)
            self.section_dict['{0}_minute'.format(start_end)].append(dt.minute)
            self.section_dict['{0}_second'.format(start_end)].append(dt.second)

class PhysicsNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.num_land_cat = self.get_opt_value('num_land_cat')

    def set_dictionary_values(self):
        self.set_opt_value('num_land_cat', self.num_land_cat)

class DomainsNamelistSection(NamelistSectionBase):
    def __init__(self, section_dict):
        super().__init__(section_dict)
        self.max_dom = self.section_dict['max_dom']
        self.e_we = self.get_array('e_we')
        self.e_sn = self.get_array('e_sn')
        self.e_vert = self.get_array('e_vert')
        self.dx = self.get_array('dx')
        self.dy = self.get_array('dy')
        self.grid_id = self.get_array('grid_id')
        self.parent_id = self.get_array('parent_id')
        self.i_parent_start = self.get_array('i_parent_start')
        self.j_parent_start = self.get_array('j_parent_start')
        self.parent_grid_ratio = self.get_array('parent_grid_ratio')
        self.parent_time_step_ratio = self.get_array('parent_time_step_ratio')

        self.p_top_requested = self.get_opt_value('p_top_requested')
        self.num_metgrid_soil_levels = self.get_opt_value('num_metgrid_soil_levels')
        self.feedback = self.section_dict['feedback']
        self.smooth_option = self.get_opt_value('smooth_option')
        self.num_metgrid_levels = self.section_dict['num_metgrid_levels']

        self.eta_levels = self.get_array('eta_levels')

        self.time_step = self.get_opt_value('time_step')
        self.time_step_fract_num = self.get_opt_value('time_step_fract_num')
        self.time_step_fract_den = self.get_opt_value('time_step_fract_den')

        self.use_adaptive_time_step = self.get_opt_value('use_adaptive_time_step', False)
        self.step_to_output_time = self.get_opt_value('step_to_output_time')
        self.target_cfl = self.get_opt_value('target_cfl')
        self.target_hcfl = self.get_opt_value('target_hcfl')
        self.max_step_increase_pct = self.get_opt_value('max_step_increase_pct')
        self.starting_time_step = self.get_opt_value('starting_time_step')
        self.starting_time_step_den = self.get_opt_value('starting_time_step_den')
        self.max_time_step = self.get_opt_value('max_time_step')
        self.max_time_step_den = self.get_opt_value('max_time_step_den')
        self.min_time_step = self.get_opt_value('min_time_step')
        self.min_time_step_den = self.get_opt_value('min_time_step_den')
        self.adaptation_domain = self.get_opt_value('adaptation_domain')

    def set_dictionary_values(self):
        self.section_dict['max_dom'] = self.max_dom
        self.section_dict['e_we'] = self.e_we
        self.section_dict['e_sn'] = self.e_sn
        self.section_dict['e_vert'] = self.e_vert
        self.section_dict['dx'] = self.dx
        self.section_dict['dy'] = self.dy
        self.section_dict['grid_id'] = self.grid_id
        self.section_dict['parent_id'] = self.parent_id
        self.section_dict['i_parent_start'] = self.i_parent_start
        self.section_dict['j_parent_start'] = self.j_parent_start
        self.section_dict['parent_grid_ratio'] = self.parent_grid_ratio
        self.section_dict['parent_time_step_ratio'] = self.parent_time_step_ratio

        self.set_opt_value('p_top_requested', self.p_top_requested)
        self.set_opt_value('num_metgrid_soil_levels', self.num_metgrid_soil_levels)
        self.section_dict['feedback'] = self.feedback
        self.set_opt_value('smooth_option', self.smooth_option)
        self.section_dict['num_metgrid_levels'] = self.num_metgrid_levels
        self.set_opt_value('eta_levels', self.eta_levels)

        self.set_opt_value('time_step', self.time_step)
        self.set_opt_value('time_step_fract_num', self.time_step_fract_num)
        self.set_opt_value('time_step_fract_den', self.time_step_fract_den)

        self.section_dict['use_adaptive_time_step'] = self.use_adaptive_time_step
        self.set_opt_value('step_to_output_time', self.step_to_output_time)
        self.set_opt_value('target_cfl', self.target_cfl)
        self.set_opt_value('target_hcfl', self.target_hcfl)
        self.set_opt_value('max_step_increase_pct', self.max_step_increase_pct)
        self.set_opt_value('starting_time_step', self.starting_time_step)
        self.set_opt_value('starting_time_step_den', self.starting_time_step_den)
        self.set_opt_value('max_time_step', self.max_time_step)
        self.set_opt_value('max_time_step_den', self.max_time_step_den)
        self.set_opt_value('min_time_step', self.min_time_step)
        self.set_opt_value('min_time_step_den', self.min_time_step_den)
        self.set_opt_value('adaptation_domain', self.adaptation_domain)

class InputNamelist(NamelistBase):
    """
    Input namelist object
    loads data from namelist.input file
    """

    def __init__(self, path, logger=rasp.modelrun.get_logger()): 
        super().__init__(path, logger)
        self.timecontrol = TimeControlNamelistSection(self.namelist['time_control'])
        self.domains = DomainsNamelistSection(self.namelist['domains'])
        self.physics = PhysicsNamelistSection(self.namelist['physics'])
    def save(self):
        self.timecontrol.set_dictionary_values()
        self.domains.set_dictionary_values()
        self.physics.set_dictionary_values()
        super().save()


def set_time_step(namelist, logger=rasp.modelrun.get_logger()):
    configuration = rasp.modelrun.get_configuration()
    # set time step
    if configuration.wrf.use_adaptive_timestep == True:
        logger.debug("Setting adaptive time step")
        namelist.domains.use_adaptive_time_step = True
        namelist.timecontrol.adjust_output_times = True
        namelist.domains.step_to_output_time = True
        namelist.domains.target_cfl = [1.2] * namelist.domains.max_dom
        namelist.domains.target_hcfl = [0.84] * namelist.domains.max_dom
        namelist.domains.max_step_increase_pct = [5] + [51] * (namelist.domains.max_dom - 1)
        namelist.domains.starting_time_step = [-1] * namelist.domains.max_dom
        namelist.domains.starting_time_step_den = [0] * namelist.domains.max_dom
        namelist.domains.max_time_step = [-1] * namelist.domains.max_dom
        namelist.domains.max_time_step_den = [0] * namelist.domains.max_dom
        namelist.domains.min_time_step = [-1] * namelist.domains.max_dom
        namelist.domains.min_time_step_den = [0] * namelist.domains.max_dom
        namelist.domains.adaptation_domain = 1
        logger.debug("use_adaptive_time_step: {0}".format(namelist.domains.use_adaptive_time_step))
    else:
        logger.debug("Setting fixed time step")
        namelist.domains.use_adaptive_time_step = False
        logger.debug("dx = {0}".format(namelist.domains.dx[0]))
        namelist.domains.time_step = int(configuration.wrf.time_step_to_dx_to_ratio * namelist.domains.dx[0] // 1000)
        namelist.domains.time_step_fract_den = 1
        namelist.domains.time_step_fract_num = 0
        logger.debug("use_adaptive_time_step: {0}".format(namelist.domains.use_adaptive_time_step))
        logger.debug("time_step: {0}".format(namelist.domains.time_step))

def create_input_namelist(region, wps_namelist, work_path, iofields=None, logger=rasp.modelrun.get_logger()):
    logger.debug("Preparing namelist.input for current run")
    namelist_path = os.path.join(work_path, 'namelist.input')
    if os.path.exists(namelist_path):
        os.remove(namelist_path)

    logger.debug("Copying region template namelist.input to {0}".format(namelist_path))
    shutil.copy(os.path.join(region.base_path, 'namelist.input'), namelist_path)

    namelist = InputNamelist(namelist_path)
    
    configuration = rasp.modelrun.get_configuration()

    if configuration.wrf.debug_level > 0:
        namelist.timecontrol.debug_level = configuration.wrf.debug_level
        logger.debug("debug_level: {0}".format(namelist.timecontrol.debug_level))


    logger.debug("Setting start and end date/times")

    namelist.timecontrol.run_days = 0
    namelist.timecontrol.run_hours = 0
    namelist.timecontrol.run_minutes = 0
    namelist.timecontrol.run_seconds = 0

    namelist.timecontrol.start_datetimes = wps_namelist.share.start_datetimes
    namelist.timecontrol.end_datetimes = wps_namelist.share.end_datetimes

    namelist.timecontrol.history_interval = [configuration.wrf.history_interval] * wps_namelist.share.max_dom
    namelist.timecontrol.frames_per_outfile = [1] * wps_namelist.share.max_dom
    namelist.timecontrol.restart = False

    if configuration.wrf.iofields and len(configuration.wrf.iofields) > 0:
        logger.debug("Setting iofields")
        iofields_file_path = os.path.join(work_path, 'iofields_list.txt')
        with open(iofields_file_path, "wt") as f:
            iofields_content = "+:h:0:{0}".format(",".join(configuration.wrf.iofields))
            logger.debug("iofields: {0}".format(iofields_content))
            f.write("{0}\n".format(iofields_content))
        namelist.timecontrol.iofields_filename = [iofields_file_path] * wps_namelist.share.max_dom
        namelist.timecontrol.ignore_iofields_warning = False
        logger.debug("iofields_filename: {0}".format(namelist.timecontrol.iofields_filename))
        logger.debug("ignore_iofields_warning: {0}".format(namelist.timecontrol.ignore_iofields_warning))


    logger.debug("Setting domains")
    namelist.domains.max_dom = wps_namelist.share.max_dom
    namelist.domains.e_we = wps_namelist.geogrid.e_we
    namelist.domains.e_sn = wps_namelist.geogrid.e_sn
    if not (namelist.domains.eta_levels is None):
        namelist.domains.e_vert = [len(namelist.domains.eta_levels)] * namelist.domains.max_dom
    #namelist.domains.p_top_requested = 5000
    namelist.domains.grid_id = list(range(1, namelist.domains.max_dom + 1))
    namelist.domains.parent_id = list(range(namelist.domains.max_dom))
    namelist.domains.i_parent_start = wps_namelist.geogrid.i_parent_start
    namelist.domains.j_parent_start = wps_namelist.geogrid.j_parent_start
    namelist.domains.parent_grid_ratio = wps_namelist.geogrid.parent_grid_ratio
    namelist.domains.parent_time_step_ratio = wps_namelist.geogrid.parent_grid_ratio

    dx = wps_namelist.geogrid.dx
    dy = wps_namelist.geogrid.dy
    namelist.domains.dx = [dx]
    namelist.domains.dy = [dy]

    for i in range(1, namelist.domains.max_dom):
        dx = dx / namelist.domains.parent_grid_ratio[i]
        dy = dy / namelist.domains.parent_grid_ratio[i]
        namelist.domains.dx.append(dx)
        namelist.domains.dy.append(dy)

    logger.debug("max_dom: {0}".format(namelist.domains.max_dom))
    logger.debug("e_we: {0}".format(namelist.domains.e_we))
    logger.debug("e_sn: {0}".format(namelist.domains.e_sn))
    logger.debug("e_vert: {0}".format(namelist.domains.e_vert))
    #logger.debug("p_top_requested: {0}".format(namelist.domains.p_top_requested))
    logger.debug("dx: {0}".format(namelist.domains.dx))
    logger.debug("dy: {0}".format(namelist.domains.dy))
    logger.debug("grid_id: {0}".format(namelist.domains.grid_id))
    logger.debug("parent_id: {0}".format(namelist.domains.parent_id))
    logger.debug("i_parent_start: {0}".format(namelist.domains.i_parent_start))
    logger.debug("j_parent_start: {0}".format(namelist.domains.j_parent_start))
    logger.debug("parent_grid_ratio: {0}".format(namelist.domains.parent_grid_ratio))
    logger.debug("parent_time_step_ratio: {0}".format(namelist.domains.parent_time_step_ratio))

    logger.debug("Setting namelist.input values from metgrid file")
    #find one of d01 metgrid data files and 
    #parse it to obtain num_metgrid_levels
    for file_path in glob.glob(os.path.join(work_path, "met_em.d01.*.nc")):
        logger.debug("Found metgrid file {0}".format(file_path))
        metgrid_data = MetgridData(file_path)
        namelist.domains.num_metgrid_levels = metgrid_data.num_metgrid_levels
        logger.debug("num_metgrid_levels: {0}".format(namelist.domains.num_metgrid_levels))
        namelist.domains.num_metgrid_soil_levels = metgrid_data.num_metgrid_soil_levels
        logger.debug("num_metgrid_soil_levels: {0}".format(namelist.domains.num_metgrid_soil_levels))
        namelist.physics.num_land_cat = metgrid_data.num_land_cat
        logger.debug("num_land_cat: {0}".format(namelist.physics.num_land_cat))
        break

    logger.debug("Setting interval_seconds to {0} hours".format(region.grib_source.interval_hours))
    namelist.timecontrol.interval_seconds = region.grib_source.interval_hours * 60 * 60

    logger.debug("Setting up default two-way nested run")
    namelist.domains.feedback = 1
    #namelist.domains.smooth_option = 2
    namelist.timecontrol.input_from_file = [True] * wps_namelist.share.max_dom
    namelist.timecontrol.fine_input_stream = None
    #[0] * wps_namelist.share.max_dom

    logger.debug("Setting up file formats")
    namelist.domains.io_form_history = namelist.format_netCDF
    namelist.domains.io_form_restart = namelist.format_netCDF
    namelist.domains.io_form_input = namelist.format_netCDF
    namelist.domains.io_form_boundary = namelist.format_netCDF

    set_time_step(namelist)

    namelist.save()
    return namelist