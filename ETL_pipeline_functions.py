import numpy as np
import pandas as pd
import requests, json, csv
from datetime import datetime, timedelta
import time

def last_date(activities_file):

    with open(activities_file, 'r') as f:
        lines = f.read().splitlines()
        first_line = lines[0].split(',')
        last_line = lines[-1].split(',')
        last_line_dict = dict(list(zip(first_line, last_line)))
        last_date = last_line_dict['start_date']
        f.close()

    return last_date

def iso_8601_to_unix(date_string):

    iso_8601_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    date_tuple = iso_8601_date.timetuple()
    unix_date = int(time.mktime(date_tuple))

    return unix_date

def strava_token_exchange(credentials_file):

    with open(credentials_file, 'r') as r:
        api_credentials = json.load(r)
        client_id = api_credentials['client_id']
        client_secret = api_credentials['client_secret']
        refresh_token = api_credentials['refresh_token']
        r.close()

    req = requests.post("https://www.strava.com/oauth/token?client_id={}&client_secret={}&refresh_token={}&grant_type=refresh_token".format(client_id, client_secret, refresh_token)).json()
    api_credentials['access_token'] = req['access_token']
    api_credentials['refresh_token'] = req['refresh_token']

    with open(credentials_file, 'w') as w:
        json.dump(api_credentials, w)
        w.close()

    access_token = api_credentials['access_token']

    return access_token

def geocode_key_getter(credentials_file):

    with open(credentials_file, 'r') as r:
        key = json.load(r)['key']
        r.close() 

    return key

def request_location(geocode_key, latlng):

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    req = requests.get("{}?latlng={},{}&key={}".format(url, latlng[0], latlng[1], geocode_key)).json()

    address_components_nested = req['results'][0]['address_components']
    component_names = list(map(lambda x: x['short_name'], address_components_nested))
    component_types = list(map(lambda x: x['types'][0], address_components_nested))
    address_components = dict(list(zip(component_types, component_names))) 

    location = address_components.get('postal_town', 'missing')

    return location

def request_activities(strava_access_token, geocode_key, start_date):

    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": "Bearer {}".format(strava_access_token)}
    params = {'after': start_date}
    req = requests.get(url, headers = headers, params = params).json()

    activities = []

    for activity in req:
        activity_info = {}
        activity_info['activity_id'] = activity['id']
        activity_info['start_date'] = activity['start_date_local']
        activity_info['activity_name'] = activity['name']
        activity_info['activity_type'] = activity['type']
        activity_info['distance'] = activity['distance']
        activity_info['time'] = activity['elapsed_time']

        latlng = activity.get('start_latlng')
        if latlng:
            activity_info['location'] = request_location(geocode_key, latlng)
        else:
            activity_info['location'] = 'missing'

        activity_info['elevation_gain'] = activity.get('total_elevation_gain', 0)
        activity_info['average_speed'] = activity.get('average_speed', 0)
        activity_info['max_speed'] = activity.get('max_speed', 0)
        activity_info['average_hr'] = activity.get('average_heartrate', 0)
        activity_info['max_hr'] = activity.get('max_heartrate', 0)
        activity_info['average_cadence'] = activity.get('average_cadence', 0)
        activity_info['kudos'] = activity.get('kudos_count', 0)
        activity_info['suffer_score'] = activity.get('suffer_score', 0)
        activities.append(activity_info)

    return activities

def request_splits(strava_access_token, activity_ids):

    url = "https://www.strava.com/api/v3/activities"
    headers = {"Authorization": "Bearer {}".format(strava_access_token)}

    activity_splits = []

    for activity_id in activity_ids:
        req = requests.get("{}/{}/laps".format(url, activity_id), headers = headers).json()
        for split in req:
            split_info = {}
            split_info['activity_id'] = activity_id
            split_info['split_index'] = split['split']
            split_info['split_distance'] = split['distance']
            split_info['split_time'] = split['elapsed_time']
            split_info['split_elevation_gain'] = split.get('total_elevation_gain', 0)
            split_info['split_average_speed'] = split.get('average_speed', 0)
            split_info['split_max_speed'] = split.get('max_speed', 0)
            split_info['split_average_hr'] = split.get('average_heartrate', 0)
            split_info['split_max_hr'] = split.get('max_heartrate', 0)
            split_info['split_average_cadence'] = split.get('average_cadence', 0)
            activity_splits.append(split_info)

    return activity_splits

def request_zones(strava_access_token, activity_ids):

    url = "https://www.strava.com/api/v3/activities"
    headers = {"Authorization": "Bearer {}".format(strava_access_token)}

    activity_zones = []

    for activity_id in activity_ids:
        req = requests.get("{}/{}/zones".format(url, activity_id), headers = headers).json()
        if req:
            distribution_types = list(map(lambda x: x['type'], req))
            distribution_buckets_nested = list(map(lambda x: x['distribution_buckets'], req))
            distribution_buckets = [list(map(lambda y: y['time'], x)) for x in distribution_buckets_nested]
            distributions = list(zip(distribution_types, distribution_buckets))
            for distribution in distributions:
                for i in range(len(distribution[1])):
                    zone_info = {}
                    zone_info['activity_id'] = activity_id
                    zone_info['zone_type'] =  distribution[0]
                    zone_info['zone_index'] = i + 1
                    zone_info['zone_time'] = distribution[1][i]
                    activity_zones.append(zone_info)

    return activity_zones

def append_requests(requests, file_name):

    with open(file_name, 'r') as r:
        lines = r.read().splitlines()
        headers = lines[0].split(',')
        r.close()

    with open(file_name, 'a', newline = '') as a:
        csv_writer = csv.DictWriter(a, fieldnames = headers)
        csv_writer.writerows(requests)
        a.close()

    return print("{} appended".format(file_name))