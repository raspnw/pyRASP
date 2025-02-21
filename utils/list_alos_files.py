import os
import ftplib
import sys

server = 'ftp.eorc.jaxa.jp'
port = 21
directory = 'pub/ALOS/ext1/AW3D30/release_v1903'
username = 'jiri@securitay.com'
password = 'aw3d30'

filename = 'alos.txt'

def ftp_walk(ftp, dir, f):
    dirs = []
    files = []
    for item in ftp.mlsd(dir):
        if item[1]['type'] == 'dir':
            dirs.append(item[0])
        elif item[1]['type'] == 'file':
            files.append(item[0])
    if files:
        for file in files:
            print('{0}/{1}'.format(dir, file))
            f.write('{0}/{1}\n'.format(dir, file))
    else:
        pass
    for subdir in sorted(dirs):
        ftp_walk(ftp, '{}/{}'.format(dir, subdir), f)

ftp = ftplib.FTP()
ftp.connect(server, port)
ftp.login("", "")
with open(os.path.join(os.path.dirname(__file__), filename), 'wt+') as f:
    ftp_walk(ftp, directory, f)