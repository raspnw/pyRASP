import os
import logging
import sys
import datetime

from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

geog_files_url = 'http://www2.mmm.ucar.edu/wrf/src/wps_files/'

page = requests.get(geog_files_url).text
soup = BeautifulSoup(page, 'html.parser')
for node in soup.find_all('a'):
    href = node.get('href')
    if href.find('.tar.') > 0:
        parts = href.split('.')
        print("{0}: {1}".format(parts[0], urljoin(geog_files_url, href)))
