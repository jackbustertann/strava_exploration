# importing libaries

import numpy as np
import pandas as pd
import requests, json, csv
from datetime import datetime, timedelta
import time
import re

# timestamp functions

def last_timestamp(activities_file):

    with open(activities_file, 'r') as f:
        lines = f.read().splitlines()
        first_line = lines[0].split(',')
        last_line = lines[-1].split(',')
        last_line_dict = dict(list(zip(first_line, last_line)))
        last_timestamp = last_line_dict['timestamp']
        f.close()

    return last_timestamp

def sql_timestamp_formatter(timestamp_iso_string):

    timestamp_datetime = datetime.strptime(timestamp_iso_string, "%Y-%m-%dT%H:%M:%SZ")
    timestamp_sql = timestamp_datetime.strftime('%Y-%m-%d %H:%M:%S')
    return timestamp_sql

def timestamp_to_unix(timestamp_string):

    timestamp_datetime = datetime.strptime(timestamp_string, "%Y-%m-%d %H:%M:%S")
    datetime_tuple = timestamp_datetime.timetuple()
    unix_timestamp = int(time.mktime(datetime_tuple))

    return unix_timestamp

# API credentials functions

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

# Strava activities endpoint functions

def request_activities(strava_access_token, start_date = False):

    url = "https://www.strava.com/api/v3/" + "athlete/activities"
    headers = {"Authorization": "Bearer {}".format(strava_access_token)}
    params = {}

    if start_date:
        params['after'] = start_date

    response = requests.get(url, headers = headers, params = params).json()

    return response

def clean_activity(activity):

    clean_activity = {}

    clean_activity['id'] = activity['id']
    clean_activity['timestamp'] = sql_timestamp_formatter(activity['start_date_local'])
    clean_activity['activity_name'] = activity['name']
    clean_activity['activity_type'] = activity['type']
    clean_activity['distance'] = activity.get('distance', 0) / 1000
    clean_activity['time'] = activity.get('elapsed_time', 0)
    clean_activity['latlng'] = activity.get('start_latlng', [])
    clean_activity['elevation_gain'] = activity.get('total_elevation_gain', 0)
    clean_activity['average_speed'] = activity.get('average_speed', 0) * 3.6
    clean_activity['max_speed'] = activity.get('max_speed', 0) * 3.6
    clean_activity['average_hr'] = activity.get('average_heartrate', 0)
    clean_activity['max_hr'] = activity.get('max_heartrate', 0)
    clean_activity['average_cadence'] = activity.get('average_cadence', 0)
    clean_activity['kudos'] = activity.get('kudos_count', 0)

    if activity.get('suffer_score', None):
        clean_activity['suffer_score'] = activity['suffer_score']
    else:
        clean_activity['suffer_score'] = 0

    return clean_activity

def request_location(geocode_key, latlng):

    url = "https://maps.googleapis.com/maps/api/" + "geocode/json"
    response = requests.get("{}?latlng={},{}&key={}".format(url, latlng[0], latlng[1], geocode_key)).json()

    return response

def clean_location(location):

    address_components_nested = location['results'][0]['address_components']
    component_names = list(map(lambda x: x['short_name'], address_components_nested))
    component_types = list(map(lambda x: x['types'][0], address_components_nested))
    address_components = dict(list(zip(component_types, component_names))) 
    clean_location = address_components.get('postal_town', 'missing')

    return clean_location

def get_run_type(activity):

    key_words_int = ['Intervals', 'Yasso', 'Track']
    key_words_wu = ['WU', 'test']

    for key_word in key_words_int:
        if key_word in activity['activity_name']:
            return 'I'
    for key_word in key_words_wu:
        if key_word in activity['activity_name']:
            return 'WU'
    if 'WD' in activity['activity_name']:
            return 'WD'

    elif activity['distance'] < 8:
        return 'S'
    elif activity['distance'] < 16:
        return 'M'
    else:
        return 'L'  

def get_position(activity):

    pos_pattern = re.compile('.*\(\d?:?\d{2}:\d{2}\s-\s(\d+)\w+\)')
    pos_pattern_match = re.findall(pos_pattern, activity['activity_name'])

    if pos_pattern_match:
        return int(pos_pattern_match[0])
    else:
        return 0

def get_event_type(activity):

    if ('PR' in activity['activity_name']) & (activity['run_type'] == 'S') :
        return 'PR'
    elif activity['position'] > 0:
        return 'R'
    else:
        return 'W'

def HHMMSS_to_seconds(time_HHMMSS):

    time_tuple = [0] * 3
    time_tuple_raw = [int(x) for x in time_HHMMSS.split(':')]
    time_tuple[-len(time_tuple_raw):] = time_tuple_raw
    time_seconds = (time_tuple[0] * 3600) + (time_tuple[1] * 60) + time_tuple[2]

    return time_seconds

def get_chip_time(activity):

    time_pattern = re.compile('.*\((\d?:?\d{2}:\d{2})\s-\s\d+\w+\)')
    time_pattern_match = re.findall(time_pattern, activity['activity_name'])

    if time_pattern_match:
        return HHMMSS_to_seconds(time_pattern_match[0])
    else:
        return activity['time']

def engineer_activity(activity, geocode_key):

    engineered_activity = activity.copy()

    if activity['latlng']:
        engineered_activity['location'] = clean_location(request_location(geocode_key, engineered_activity['latlng']))
    else:
        engineered_activity['location'] = 'missing'
    ## binning activities based on distances
    engineered_activity['run_type'] = get_run_type(engineered_activity)
    ## extracting race positions from activity names
    engineered_activity['position'] = get_position(engineered_activity)
    ## extracting event types from activity names
    engineered_activity['event_type'] = get_event_type(engineered_activity)
    ## extracting race chip times from activity names
    engineered_activity['chip_time'] = get_chip_time(engineered_activity)

    # dropping redundant features
    engineered_activity.pop('latlng', None)
    engineered_activity.pop('activity_name', None)
    
    return engineered_activity

def processed_activities(strava_access_token, geocode_key, start_date = False):

    processed_activities = []

    activities_response = request_activities(strava_access_token, start_date)
    if activities_response:
        clean_activities = [clean_activity(activity) for activity in activities_response]
        engineered_activities = [engineer_activity(activity, geocode_key) for activity in clean_activities]

        for activity in engineered_activities:
            if activity['activity_type'] == 'Run':
                activity.pop('activity_type', None)
                processed_activities.append(activity)
            else:
                continue
    
    return processed_activities
    

# Strava splits endpoint functions

def request_splits(strava_access_token, activity_id):

    base_url = "https://www.strava.com/api/v3"
    end_point = "activities/{}/laps".format(activity_id)
    url = base_url + "/" + end_point
    headers = {"Authorization": "Bearer {}".format(strava_access_token)}

    response = requests.get(url, headers = headers).json()

    return response

def clean_splits(activity_splits, activity_id):
    
    cleaned_splits = []

    for split in activity_splits:
        cleaned_split = {}
        cleaned_split['activity_id'] = activity_id
        cleaned_split['split_index'] = split['split']
        cleaned_split['distance'] = split['distance'] / 1000
        cleaned_split['time'] = split['elapsed_time']
        cleaned_split['elevation_gain'] = split.get('total_elevation_gain', 0)
        cleaned_split['average_speed'] = split.get('average_speed', 0) * 3.6
        cleaned_split['max_speed'] = split.get('max_speed', 0) * 3.6
        cleaned_split['average_hr'] = split.get('average_heartrate', 0)
        cleaned_split['max_hr'] = split.get('max_heartrate', 0)
        cleaned_split['average_cadence'] = split.get('average_cadence', 0)

        cleaned_splits.append(cleaned_split)
    
    return cleaned_splits

def processed_splits(strava_access_token, activity_ids):

    processed_splits = []

    for activity_id in activity_ids:
        splits_response = request_splits(strava_access_token, activity_id)
        cleaned_splits = clean_splits(splits_response, activity_id)
        processed_splits += cleaned_splits
    
    return processed_splits

# Strava zones endpoint functions

def request_zones(strava_access_token, activity_id):

    base_url = "https://www.strava.com/api/v3"
    end_point = "activities/{}/zones".format(activity_id)
    url = base_url + "/" + end_point
    headers = {"Authorization": "Bearer {}".format(strava_access_token)}

    response = requests.get(url, headers = headers).json()

    return response

def clean_zones(activity_zones, activity_id):

    distribution_types = list(map(lambda x: x['type'], activity_zones))
    distribution_buckets_nested = list(map(lambda x: x['distribution_buckets'], activity_zones))
    distribution_buckets = [list(map(lambda y: y['time'], x)) for x in distribution_buckets_nested]
    distributions = list(zip(distribution_types, distribution_buckets))

    cleaned_zones = []

    for distribution in distributions:
        for i in range(len(distribution[1])):
            cleaned_zone = {}
            cleaned_zone['activity_id'] = activity_id
            cleaned_zone['zone_type'] =  distribution[0]
            cleaned_zone['zone_index'] = i + 1
            cleaned_zone['time'] = distribution[1][i]
            cleaned_zones.append(cleaned_zone)

    return cleaned_zones

def processed_zones(strava_access_token, activity_ids):

    processed_zones = []

    for activity_id in activity_ids:
        zones_response = request_zones(strava_access_token, activity_id)
        cleaned_zones = clean_zones(zones_response, activity_id)
        processed_zones += cleaned_zones
    
    return processed_zones

# appending requests to csv file

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

# executing sql statements

def commit(conn, sql_statement):
    cur = conn.cursor()
    cur.execute(sql_statement)
    conn.commit()
    cur.close()
    return print("statement committed")

def fetch(conn, sql_statement):
    cur = conn.cursor()
    cur.execute(sql_statement)
    output = cur.fetchall()
    cur.close()
    return output

def insert_statement(table_name, record):
    columns = ', '.join(list(record.keys()))
    values = str(tuple(record.values()))
    statement = """INSERT INTO {} ({}) VALUES {};""".format(table_name, columns, values)
    return statement