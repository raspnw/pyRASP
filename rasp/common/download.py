import os
import logging
import urllib.parse
import requests
from requests.auth import HTTPBasicAuth
import ftplib
from bs4 import BeautifulSoup

import rasp.configuration

class DownloadException(Exception):
    pass


def download_filelist(url):
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    return [node.get('href') for node in soup.find_all('a')]


def download_file(url, path, username=None, password=None, logger=logging.getLogger()):
    url_parts = urllib.parse.urlparse(url)
    if url_parts.scheme == 'ftp':
        download_file_ftp(url, path, username=username, password=password, logger=logger)
    elif url_parts.hostname == 'e4ftl01.cr.usgs.gov':
        download_file_srtm_30m(url, path, username, password, logger=logger)
    else:
        download_file_http(url, path, username=username, password=password, logger=logger)

def download_file_srtm_30m(url, path, username, password, logger=logging.getLogger()):
    logger.debug("Downloading {0}".format(url))
    if not username or not password:
        raise DownloadException("Error downloading {0}: username and password are required".format(url))
    logger.debug("Basic auth: {0}/{1}".format(username, password))
    auth = HTTPBasicAuth(username, password)
    with requests.Session() as s:
        r = s.get(url, allow_redirects=False)
        r.next.prepare_auth(auth=auth)
        r = s.send(r.next, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r:
                    f.write(chunk)
            logger.debug("Successfully downloaded {0} to {1}".format(url, path))
        else:
            raise DownloadException("Error downloading {0}. Status code: {1}".format(url, r.status_code))

def download_file_http(url, path, username=None, password=None, logger=logging.getLogger()):
    logger.debug("Downloading {0}".format(url))
    auth = None
    if username and password:
        logger.debug("Basic auth: {0}/{1}".format(username, password))
        auth = HTTPBasicAuth(username, password)
    r = requests.get(url, proxies = rasp.configuration.network.proxies, stream = True, auth=auth)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in r:
                f.write(chunk)
        logger.debug("Successfully downloaded {0} to {1}".format(url, path))
    else:
        raise DownloadException("Error downloading {0}. Status code: {1}".format(url, r.status_code))

def download_file_ftp(url, path, username='', password='', logger=logging.getLogger()):
    logger.debug("Downloading {0}".format(url))
    url_parts = urllib.parse.urlparse(url)

    url_path_parts = url_parts.path.split('/')
    ftp_path = "/".join(url_path_parts[:-1])
    ftp_filename = url_path_parts[-1]

    logger.debug("FTP path: {0}".format(ftp_path))
    logger.debug("FTP filename: {0}".format(ftp_filename))

    ftp = ftplib.FTP(url_parts.netloc) 
    ftp.login(user=username, passwd=password)
    ftp.cwd(ftp_path)
    with open(path, 'wb') as f:
        ftp.retrbinary("RETR " + ftp_filename, f.write)
    ftp.quit()

    logger.debug("Successfully downloaded {0} to {1}".format(url, path))
