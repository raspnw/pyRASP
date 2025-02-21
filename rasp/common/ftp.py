import os
import urllib.parse
import ftplib
import logging
import netrc

class FTPError(Exception):
    pass

class FTPHelper(ftplib.FTP):
    def __init__(self, server, root_path, logger=logging.getLogger()):
        self.logger = logger
        self.logger.debug("Creating FTP helper")
        self.server = server
        self.ftp_root_path = root_path.strip('/')
        netrc_path =os.path.expanduser('~/.netrc')
        if not os.path.exists(netrc_path):
            raise FTPError(".netrc file does not exists")
        user_netrc = netrc.netrc(netrc_path)
        if not server in user_netrc.hosts:
            raise FTPError("No .netrc entry for {0}".format(server))
        self.username = user_netrc.hosts[server][0]
        self.password = user_netrc.hosts[server][2]
        self.logger.debug("server: {0}".format(self.server))
        self.logger.debug("username: {0}".format(self.username))
        return super().__init__(host=self.server, user=self.username, passwd=self.password)

    def rel_path_exists(self, rel_url):
        rel_url = rel_url.lstrip('/')
        cur_dir = super().pwd()
        try:
            dirname = urllib.parse.urljoin("{0}/".format(self.ftp_root_path), rel_url)
            self.logger.debug("Checking FTP path {0} exists".format(dirname))
            self.cwd(dirname)
            self.cwd(cur_dir)
            self.logger.debug("True")
            return True
        except:
            self.logger.debug("False")
            return False

    def rel_rmtree(self, rel_url):
        pathname = urllib.parse.urljoin("{0}/".format(self.ftp_root_path), rel_url)
        for name, info in self.mlsd(pathname):
            if info['type'] == 'dir':
                self.rel_rmtree("{0}/{1}".format(rel_url, name))
            elif info['type'] == 'file':
                self.delete("{0}/{1}".format(pathname, name))
        self.rmd(pathname)

    def rel_list_dir(self, rel_url):
        pathname = urllib.parse.urljoin("{0}/".format(self.ftp_root_path), rel_url)
        return [name for name, info in self.mlsd(pathname) if info['type'] == 'dir']

    def cdw(self, pathname):
        self.logger.debug("CDW {0}".format(pathname))
        super().cwd(pathname)

    def pwd(self):
        dirname = super().pwd()
        self.logger.debug("PWD: {0}".format(dirname))
        return dirname

    def mkd(self, dirname):
        self.logger.debug("MKD {0}".format(dirname))
        try:
            super().mkd(dirname)
        except ftplib.error_perm as e:
            code = int(e.args[0][:3])
            if code == 550:
                pass
            else:
                raise


    def storbinary(self, cmd, fb):
        self.logger.debug("{0}".format(cmd))
        super().storbinary(cmd, fb)

    def cdw_root(self):
        self.cdw('/' + self.ftp_root_path)

    def makedirs(self, rel_url):
        self.logger.debug("making FTP path {0}/{1}".format(self.ftp_root_path, rel_url))
        rel_url = rel_url.lstrip('/')
        parts = rel_url.split('/')
        cur_dir = self.pwd()
        self.cdw_root()
        for dir in parts:
            if not self.rel_path_exists(dir):
                self.mkd(dir)
            self.cwd(dir)
        self.cwd(cur_dir)


    def upload(self, path, rel_url):
        self.logger.debug("Uploading {0} to {1}/{2}".format(path, self.ftp_root_path, rel_url))
        cur_dir = self.pwd()
        rel_url = rel_url.lstrip('/')
        parts = rel_url.split('/')
        rel_url_path = '/'.join(parts[:-1])
        url_filename = parts[-1]
        if len(parts) > 1:
            if not self.rel_path_exists(rel_url_path):
                self.makedirs(rel_url_path)
            self.cdw_root()
            self.cdw(rel_url_path)
        else:
            self.cdw_root()
        with open(path, 'rb') as fb:
            self.storbinary('STOR {0}'.format(url_filename), fb)
        self.cdw(cur_dir)



