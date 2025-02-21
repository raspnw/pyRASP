import os
import logging
import sys
import json
import time
import platform
import psutil
import cpuinfo
import tempfile
from socket import gethostname

from rasp import configuration
from rasp.postprocess.publish.utils import publish_file

def get_heartbeat_info():

    heartbeat = {}
    heartbeat['timestamp'] = time.time()

    statvfs = os.statvfs(configuration.base_path)
    f_bused = statvfs.f_blocks - statvfs.f_bfree
    heartbeat['disk'] = {}
    heartbeat['disk']['usage'] = round(100 * f_bused / (f_bused + statvfs.f_bavail))
    heartbeat['disk']['total'] = statvfs.f_blocks * statvfs.f_frsize
    heartbeat['disk']['available'] = statvfs.f_bavail * statvfs.f_frsize
    heartbeat['disk']['used'] = statvfs.f_blocks - f_bused

    svmem = psutil.virtual_memory()
    heartbeat['memory'] = {}
    heartbeat['memory']['total'] = svmem.total
    heartbeat['memory']['usage'] = round(svmem.percent)

    heartbeat['cpu'] = {}
    heartbeat['cpu']['model'] = cpuinfo.get_cpu_info()['brand']
    heartbeat['cpu']['count'] = os.cpu_count()
    
    heartbeat['os'] = {}
    heartbeat['os']['system'] = platform.system()
    if heartbeat['os']['system'] == 'Linux':
        distname,version,id = platform.linux_distribution()
        heartbeat['os']['distname'] = distname
        heartbeat['os']['version'] = version
        heartbeat['os']['id'] = id
    elif heartbeat['os']['system'] == 'Windows':
        release, version, csd, ptype = platform.win32_ver()
        heartbeat['os']['release'] = release
        heartbeat['os']['version'] = version
    heartbeat['os']['timezone'] = time.strftime("%Z", time.localtime())

    return heartbeat

def upload_heartbeat_json():
    heartbeat = get_heartbeat_info()
    json_path = os.path.join(tempfile.gettempdir(), 'heartbeat.json')
    with open(json_path, 'wt') as f:
        json.dump(heartbeat, f)

    publish_file(json_path, '/json/heartbeat/{0}.json'.format(gethostname()), logging.getLogger())

if __name__ == "__main__":
    upload_heartbeat_json()