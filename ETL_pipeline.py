import numpy as np
import pandas as pd
import requests, json, csv
from datetime import datetime, timedelta
import time
import re
import psycopg2
import ETL_pipeline_functions

def ETL_pipeline():
    # storing credentials for Strava and Google Geocoding API's
    strava_access_token = ETL_pipeline_functions.strava_token_exchange('.secret/strava_api_credentials.json')
    geocode_key = ETL_pipeline_functions.geocode_key_getter('.secret/geocode_api_credentials.json')

    # storing most recent date from request log file
    timestamp = ETL_pipeline_functions.last_timestamp('data/request_log.csv')
    # converting date to unix format
    unix_time = ETL_pipeline_functions.timestamp_to_unix(timestamp)

    # making requests to activities endpoint for Strava API
    activities = ETL_pipeline_functions.processed_activities(strava_access_token, geocode_key, unix_time)

    # storing number of activities
    n = len(activities)

    # checking for activities
    if n:
        # storing ids for activities
        activity_ids = list(map(lambda activity: activity['id'], activities))

        # making requests to laps endpoint for Strava API
        splits = ETL_pipeline_functions.processed_splits(strava_access_token, activity_ids)

        # making requests to zones endpoint for Strava API
        zones = ETL_pipeline_functions.processed_zones(strava_access_token, activity_ids)

        # creating connection to postgresSQL database
        with psycopg2.connect(host="localhost", database="running_data", user="jacktann", password="Buster#19") as conn:
            for activity in activities:
                ETL_pipeline_functions.commit(conn, ETL_pipeline_functions.insert_statement("activities", activity))

            for zone in zones:
                ETL_pipeline_functions.commit(conn, ETL_pipeline_functions.insert_statement("activity_zones", zone))

            for split in splits:
                ETL_pipeline_functions.commit(conn, ETL_pipeline_functions.insert_statement("activity_splits", split))

    # exception handling for no activities
    else:
        return print("no activities to append")
    
    # storing current date
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # logging requests to a csv file
    with open('data/request_log.csv', 'a', newline = '') as a:
        csv_writer = csv.writer(a)
        csv_writer.writerow([date, n])
    
    return print("ETL pipeline complete")

ETL_pipeline()