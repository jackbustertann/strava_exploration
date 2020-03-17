import numpy as np
import pandas as pd
import requests, json, csv
from datetime import datetime, timedelta
import time

def week_ago():
    now = datetime.now()
    last_week = now - timedelta(weeks = 1)
    return last_week

def iso_8601_to_unix(iso_8601_date):
    date_tuple = iso_8601_date.timetuple()
    unix_date = int(time.mktime(date_tuple))
    return unix_date

def token_exchange():
    api_credentials_file = open('.secret/strava_api_credentials.json', 'r')
    api_credentials = json.load(api_credentials_file)
    client_id = api_credentials['client_id']
    client_secret = api_credentials['client_secret']
    refresh_token = api_credentials['refresh_token']
    api_credentials_file.close()
    req = requests.post("https://www.strava.com/oauth/token?client_id={}&client_secret={}&refresh_token={}&grant_type=refresh_token".format(client_id, client_secret, refresh_token)).json()
    api_credentials['access_token'] = req['access_token']
    api_credentials['refresh_token'] = req['refresh_token']
    api_credentials_file = open('.secret/strava_api_credentials.json', 'w')
    json.dump(api_credentials, api_credentials_file)
    api_credentials_file.close()
    return api_credentials

def request_activities(start_date):
    url = "https://www.strava.com/api/v3/athlete/activities"
    access_token = token_exchange()['access_token']
    headers = {"Authorization": "Bearer {}".format(access_token)}
    params = {'after': start_date}
    req = requests.get(url, headers = headers, params = params).json()
    activities = []
    for activity in req:
        activity_info = {}
        activity_info['activity_name'] = activity['name']
        activity_info['activity_id'] = activity['id']
        activity_info['activity_type'] = activity['type']
        activity_info['distance'] = activity.get('distance', np.nan)
        activity_info['time'] = activity.get('elapsed_time', np.nan)
        activity_info['elevation_gain'] = activity.get('total_elevation_gain', np.nan)
        activity_info['kudos'] = activity.get('kudos_count', np.nan)
        activity_info['start_date'] = activity.get('start_date', np.nan)
        activity_info['average_speed'] = activity.get('average_speed', np.nan)
        activity_info['max_speed'] = activity.get('max_speed', np.nan)
        activity_info['average_cadence'] = activity.get('average_cadence', np.nan)
        activity_info['average_hr'] = activity.get('average_heartrate', np.nan)
        activity_info['max_hr'] = activity.get('max_heartrate', np.nan)
        activity_info['suffer_score'] = activity.get('suffer_score', np.nan)
        activities.append(activity_info)
    return activities

def request_weather(activity_ids):
    strava_url = "https://www.strava.com/api/v3/activities"
    access_token = token_exchange()['access_token']
    headers = {"Authorization": "Bearer {}".format(access_token)}
    weather_list = []
    for activity_id in activity_ids:
        strava_req = requests.get("{}/{}".format(strava_url, activity_id), headers = headers).json()

        ds_url = "https://api.darksky.net/forecast"
        ds_credentials_file = open('.secret/ds_api_credentials.json', 'r') 
        ds_key = json.load(ds_credentials_file)['key']
        ds_credentials_file.close()
        exclude_blocks = "minutely,hourly,daily,alerts"
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
                weather_info['temp'] = ds_current.get('temperature', np.nan)
                weather_info['wind_speed'] = ds_current.get('windSpeed', np.nan)
                weather_info['weather'] = ds_current.get('icon', np.nan)
                weather_list.append(weather_info)
    return weather_list

def request_splits(activity_ids):
    url = "https://www.strava.com/api/v3/activities"
    access_token = token_exchange()['access_token']
    headers = {"Authorization": "Bearer {}".format(access_token)}
    activity_splits = []
    for activity_id in activity_ids:
        req = requests.get("{}/{}/laps".format(url, activity_id), headers = headers).json()
        for split in req:
            split_info = {}
            split_info['activity_id'] = activity_id
            split_info['split_index'] = split['split']
            split_info['split_time'] = split.get('elapsed_time', np.nan)
            split_info['split_distance'] = split.get('distance', np.nan)
            split_info['split_elevation_gain'] = split.get('total_elevation_gain', np.nan)
            split_info['split_average_speed'] = split.get('average_speed', np.nan)
            split_info['split_max_speed'] = split.get('max_speed', np.nan)
            split_info['split_average_hr'] = split.get('average_heartrate', np.nan)
            split_info['split_max_hr'] = split.get('max_heartrate', np.nan)
            split_info['split_average_cadence'] = split.get('average_cadence', np.nan)
            activity_splits.append(split_info)
    return activity_splits

def request_zones(activity_ids):
    url = "https://www.strava.com/api/v3/activities"
    access_token = token_exchange()['access_token']
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
    with open(file_name, 'r') as r, open(file_name, 'a', newline = '') as a:
        request_fields = next(csv.reader(r))
        csv_writer = csv.DictWriter(a, fieldnames = request_fields, restval = 0)
        csv_writer.writerows(requests)
    return print("{} appended".format(file_name))