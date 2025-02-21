import os

import wxtofly
from wxtofly.utils.geocode import GeoCode

geocode_country = GeoCode(os.path.join(wxtofly.data_path, 'countries.json'), name_property='ADMIN')
geocode_states = {}
geocode_areas = {}

def get_state_geocode(country):
    if country in geocode_states:
        return geocode_states[country]

    if country == 'USA':
        geocode_states[country] = GeoCode(os.path.join(wxtofly.data_path, 'us_states.json'), name_property='NAME')

    return geocode_states.get(country)
        

def get_area_geocode(state):
    if state in geocode_areas:
        return geocode_areas[state]

    if state == 'WA':
        geocode_areas[state] = GeoCode(os.path.join(wxtofly.data_path, 'WA_DNR_Regions.geojson'), name_property='JURISDICT_LABEL_NM')

    return geocode_areas.get(state)


def create_sites_geojson(sites, domains, logger=wxtofly.get_logger()):

    logger.debug('creating sites geojson for domains: {0}'.format(domains))
    geojson = {'type':'FeatureCollection', 'features':[]}

    for domain in domains:
        logger.debug('adding sites for domain d{0:02}'.format(domain))
        for site in filter(lambda x: x.domain_id == domain, sites):
            logger.debug('  site: {0}'.format(site.name))
            feature = {
                'type': 'Feature',
                'properties': {
                    'name': site.name,
                    'domain_id': site.domain_id,
                    'country': site.country,
                    'state': site.state,
                    'area': site.area },
                'geometry': {
                    'type': 'Point',
                    'coordinates': [] } }
            feature['geometry']['coordinates'] = [site.longitude, site.latitude]

            if feature['properties']['country'] is None:
                feature['properties']['country'] = geocode_country.get_name(site.latitude, site.longitude, '')

            if feature['properties']['state'] is None and not feature['properties']['country'] is None:
                geocode = get_state_geocode(feature['properties']['country'])
                if not geocode is None:
                    feature['properties']['state'] = geocode.get_name(site.latitude, site.longitude, '')

            if feature['properties']['area'] is None and not feature['properties']['state'] is None:
                geocode = get_area_geocode(feature['properties']['state'])
                if not geocode is None:
                    feature['properties']['area'] = geocode.get_name(site.latitude, site.longitude, '')

            geojson['features'].append(feature)

    return geojson