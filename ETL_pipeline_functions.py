import numpy as np
import pandas as pd
import requests, json, csv
from datetime import datetime, timedelta
import time

def last_date():
    with open('activities.csv', 'r') as f:
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

def strava_token_exchange():
    with open('.secret/strava_api_credentials.json', 'r') as api_credentials_file:
        api_credentials = json.load(api_credentials_file)
        client_id = api_credentials['client_id']
        client_secret = api_credentials['client_secret']
        refresh_token = api_credentials['refresh_token']
        api_credentials_file.close()

    req = requests.post("https://www.strava.com/oauth/token?client_id={}&client_secret={}&refresh_token={}&grant_type=refresh_token".format(client_id, client_secret, refresh_token)).json()
    api_credentials['access_token'] = req['access_token']
    api_credentials['refresh_token'] = req['refresh_token']

    with open('.secret/strava_api_credentials.json', 'w') as api_credentials_file:
        json.dump(api_credentials, api_credentials_file)
        api_credentials_file.close()
        
    return api_credentials

def ds_key_getter():
    with open('.secret/ds_api_credentials.json', 'r') as ds_credentials_file:
        ds_key = json.load(ds_credentials_file)['key']
        ds_credentials_file.close() 
    return ds_key

def request_activities(start_date, access_token):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": "Bearer {}".format(access_token)}
    params = {'after': start_date}
    req = requests.get(url, headers = headers, params = params).json()
    activities = []
    for activity in req:
        activity_info = {}
        activity_info['activity_name'] = activity['name']
        activity_info['activity_id'] = activity['id']
        activity_info['activity_type'] = activity['type']
        activity_info['distance'] = activity.get('distance', 0)
        activity_info['time'] = activity.get('elapsed_time', 0)
        activity_info['elevation_gain'] = activity.get('total_elevation_gain', 0)
        activity_info['kudos'] = activity.get('kudos_count', 0)
        activity_info['start_date'] = activity.get('start_date', 0)
        activity_info['average_speed'] = activity.get('average_speed', 0)
        activity_info['max_speed'] = activity.get('max_speed', 0)
        activity_info['average_cadence'] = activity.get('average_cadence', 0)
        activity_info['average_hr'] = activity.get('average_heartrate', 0)
        activity_info['max_hr'] = activity.get('max_heartrate', 0)
        activity_info['suffer_score'] = activity.get('suffer_score', 0)
        activities.append(activity_info)
    return activities

def request_weather(activity_ids, access_token):

    strava_url = "https://www.strava.com/api/v3/activities"
    strava_headers = {"Authorization": "Bearer {}".format(access_token)}


    ds_url = "https://api.darksky.net/forecast"
    ds_key = ds_key_getter()
    exclude_blocks = "minutely,hourly,daily,alerts"

    weather_list = []
    for activity_id in activity_ids:

        strava_req = requests.get("{}/{}".format(strava_url, activity_id), headers = strava_headers).json()

        time, lat_lon = strava_req['start_date'], strava_req.get('start_latlng')

        if lat_lon is None:
            continue
        else:
            ds_req = requests.get("{}/{}/{},{},{}?exclude={}".format(ds_url, ds_key, lat_lon[0], lat_lon[1], time, exclude_blocks), params= {'units': 'si'}).json()
            ds_current = ds_req.get('currently')
            if ds_current is None:
                continue
            else:
                weather_info = {}
                weather_info['activity_id'] = activity_id
                weather_info['temp'] = ds_current.get('temperature', 0)
                weather_info['wind_speed'] = ds_current.get('windSpeed', 0)
                weather_info['weather'] = ds_current.get('icon', 'unknown')
                weather_list.append(weather_info)
    return weather_list

def request_splits(activity_ids, access_token):
    url = "https://www.strava.com/api/v3/activities"
    headers = {"Authorization": "Bearer {}".format(access_token)}
    activity_splits = []
    for activity_id in activity_ids:
        req = requests.get("{}/{}/laps".format(url, activity_id), headers = headers).json()
        for split in req:
            split_info = {}
            split_info['activity_id'] = activity_id
            split_info['split_index'] = split['split']
            split_info['split_time'] = split.get('elapsed_time', 0)
            split_info['split_distance'] = split.get('distance', 0)
            split_info['split_elevation_gain'] = split.get('total_elevation_gain', 0)
            split_info['split_average_speed'] = split.get('average_speed', 0)
            split_info['split_max_speed'] = split.get('max_speed', 0)
            split_info['split_average_hr'] = split.get('average_heartrate', 0)
            split_info['split_max_hr'] = split.get('max_heartrate', 0)
            split_info['split_average_cadence'] = split.get('average_cadence', 0)
            activity_splits.append(split_info)
    return activity_splits

def request_zones(activity_ids, access_token):
    url = "https://www.strava.com/api/v3/activities"
    headers = {"Authorization": "Bearer {}".format(access_token)}
    activity_zones = []
    for activity_id in activity_ids:
        req = requests.get("{}/{}/zones".format(url, activity_id), headers = headers).json()
        if len(req) > 0:
            zone_info = {}
            zone_info['activity_id'] = activity_id
            time_distributions = list(map(lambda x: list(map(lambda x: x['time'], x['distribution_buckets'])), req))
            distribution_types = list(map(lambda x: x['type'], req))
            distributions = list(zip(distribution_types, time_distributions))
            for distribution in distributions:
                i = 1
                for zone in distribution[1]:
                    zone_info["{}_zone_{}_time".format(distribution[0], i)] = zone
                    i += 1
            activity_zones.append(zone_info)
            if 'heartrate' not in distribution_types:
                for i in range(1,6):
                    zone_info['heartrate_zone_{}_time'.format(i)] = 0
            elif 'pace' not in distribution_types:
                for i in range(1,7):
                    zone_info['pace_zone_{}_time'.format(i)] = 0
        else:
            continue
    return activity_zones

def append_requests(requests, file_name):
    n = len(requests)

    with open(file_name, 'r') as r:
        request_fields = next(csv.reader(r))
        r.close()
    with open(file_name, 'a', newline = '') as a:
        csv_writer = csv.DictWriter(a, fieldnames = request_fields)
        csv_writer.writerows(requests)
        a.close()

    print("{} appended".format(file_name))
    return n