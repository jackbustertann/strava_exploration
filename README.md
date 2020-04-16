# Strava Data Exploration

## Motivation


## Data Collection

**Data Overview**

The dataset used for this project consists of performance metrics collected using my Garmin Forerunner 235 watch for running activities spanning from January 2018 - Present. This includes a combination aggregate level information, such as total time elapsed and average heart rates, along with more granular information for each lap and heart rate zone. Also, for completeness, the locations for each activity (with coordinates) were collected using requests to the Google Geocoding API.

**ETL Pipeline**

1. Complete an activity using Garmin watch. <br/><br/>
2. Sync watch with Garmin Connect app. <br/><br/>
3. Upload activity to Strava app. <br/><br/>
4. Start CRON task at 10am, every morning. <br/><br/>
5. Extract most recent date from request log file. <br/><br/>
6. Exchange refresh token for new access token (OAuth 2.0). <br/><br/>
7. Make request to activities endpoint for Strava API. <br/><br/>
8. If appropriate, make another request to Google Geocoding API. <br/><br/>
9. Store activity id's from json response. <br/><br/>
10. Make requests to laps and zones endpoints for Strava API. <br/><br/>
11. Clean and format json reponses. <br/><br/>
11. Connect to PostgreSQL database. <br/><br/>
12. Insert data into corresponding tables. <br/><br/>
13. Update request log with request info.

<img src="/images/ETL_pipeline.png" /> <br/><br/>

**Database Schema**

<img src="/images/database_schema.png"/> <br/><br/>

