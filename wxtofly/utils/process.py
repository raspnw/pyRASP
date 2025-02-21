import os
import psutil
import sys

def kill_all(logger):
    my_pid = os.getpid()
    my_proc_name = os.path.basename(sys.executable)

    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'username', 'exe', 'cmdline', 'create_time'])
            if pinfo['name'] == my_proc_name and my_pid != pinfo['pid']:
                logger.warning("Killing process: {0}".format(pinfo['cmdline']))
                proc.kill()
            if pinfo['name'] == 'wrf.exe':
                logger.warning("Killing process: {0}".format(pinfo['cmdline']))
                proc.kill()
        except psutil.NoSuchProcess:
            pass
