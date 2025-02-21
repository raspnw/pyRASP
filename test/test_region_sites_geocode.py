import os
from rasp.region import Region
from wxtofly.utils.geocode import SitesGeoCode
from wxtofly import data_path

if __name__ == '__main__':
    region = Region('WA4')
    sites = region.get_sites(ignore_out_of_bounds=True)

    sites_geocode = SitesGeoCode()
    sites_geocode.add_geocode('state', os.path.join(data_path, 'us_states.json'), 'NAME', default='Other')
    sites_geocode.add_geocode('area', os.path.join(data_path, 'WA_DNR_Regions.geojson'), 'JURISDICT_LABEL_NM', default='Other')
    sites_geocode.create_geojson(sites, os.path.join(region.base_path, 'sites.geojson'))