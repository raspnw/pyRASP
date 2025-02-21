import os
import logging
import json
import re
#from rasp.modelrun import configuration

tasks = []
tasks.append({'path': 'D:\\wxtofly\\WPSV4.0\\WPS\\geogrid\\GEOGRID.TBL.ARW', 'version': '4.0'})
tasks.append({'path': 'D:\\wxtofly\\v3\\sources\\WPSV3.9.1\\WPS\\geogrid\\GEOGRID.TBL.ARW', 'version': '3.9.1'})

data_json = { 'geog': [] }
for task in tasks:
    geog_json = {}
    data_json['geog'].append(geog_json)
    geog_json['version'] = task['version']
    geog_json['categories'] = []

    with open(task['path'], 'rt') as fin:

        section = None
        in_section = False
        options = None
        default_option = None
        section_dict = None

        for line in fin:
            if not in_section: 
                match = re.match(r'^name\s*=\s*(\w+)', line)
                if match:
                    section = match.group(1)
                    in_section = True
                    section_dict = {'name': section, 'options':[]}
                    geog_json['categories'].append(section_dict)
                    options = {}
                continue

            if in_section:
                if re.match(r'^={5,}', line):
                    if default_option: 
                        if default_option in options:
                            section_dict['default'] = options[default_option]
                        else:
                            section_dict['default'] = 'default'
                        default_option = None
                    options = None
                    section_dict = None
                    in_section = False
                    section = None
                    continue

                match = re.match(r'^\s+rel_path\s*=\s*(\w+):(\w+)/?', line)
                if match:
                    section_dict['options'].append({'id': match.group(1), 'dirname': match.group(2)})
                    if match.group(1) == 'default':
                        default_option = match.group(2)
                    else:
                        options[match.group(2)] = match.group(1)

with open('D:\\wxtofly\\v3\\rasp-web\\beta\\json\\geog.json', 'wt') as fout:
    json.dump(data_json, fout, indent=1)




