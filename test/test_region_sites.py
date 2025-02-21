import os
import sys

from rasp.region import Region

if __name__ == '__main__':
    region = Region(sys.argv[1])
    sites = region.get_sites()
    for site in sites:
        print(str(site))
