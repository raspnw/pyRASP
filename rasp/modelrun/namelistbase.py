import os
import f90nml
from datetime import datetime

class NamelistTemplateException(Exception):
    pass

class NamelistSectionBase(object):
    def __init__(self, section_dict):
        self.section_dict = section_dict

    def get_datetimes(self, datetime_strings, format):
        datetimes = []
        for dt in datetime_strings:
            datetimes.append(datetime.strptime(dt, format))
        return datetimes

    def get_datetime_strings(self, datetimes, format):
        datetime_strings = [None] * len(datetimes)
        for i, dt in enumerate(datetimes):
            datetime_strings[i] = dt.strftime(format)
        return datetime_strings

    def get_array(self, name):
        if name in self.section_dict:
            if isinstance(self.section_dict[name], list):
                return self.section_dict[name]
            else:
                return [ self.section_dict[name] ]
        else:
            return None

    def get_opt_value(self, name, default = None):
        if name in self.section_dict:
            return self.section_dict[name]
        else:
            return default

    def set_opt_value(self, name, value):
        if not value == None:
            self.section_dict[name] = value


class NamelistBase(object):
    def __init__(self, path, logger):

        self.logger = logger
        self.logger.debug("Reading namelist from %s", path)

        self.path = path
        self.namelist = f90nml.read(self.path)

    def save(self):

        if self.path.endswith('.template'):
            raise NamelistTemplateException("Save is not allowed for namelist template files: {0}".format(self.path))

        self.logger.debug("Saving namelist to {0}".format(self.path))

        #save to a temp file and only overwrite when everything works
        temp_path ="{0}.tmp".format(self.path)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        self.namelist.write(temp_path)

        os.remove(self.path)
        os.rename(temp_path, self.path)

    format_netCDF = 2
