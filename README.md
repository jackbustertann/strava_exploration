# Strava Data Exploration

## Motivation

The motivation for this project was to create a series of interactive dashboards using my personal running data to inform my training ahead of future running events. 

## Data Collection

**Data Overview**

The dataset used for this project consists of performance metrics collected using my Garmin Forerunner 235 watch for running activities spanning from August 2018 - Present. This includes a combination aggregate level information, such as total time elapsed and average heart rates, along with more granular information for each lap and heart rate zone. Also, for completeness, the locations for each activity (with coordinates) were collected using requests to the Google Geocoding API. <br/> 

Glossary of important termonology:

- **Cadence** - number of strides per minute (SPM). <br/><br/>
- **HR zones** - ordinal variable ranging from 1 to 5 used to bin heart rates (based on [HRR methodology](https://fellrnr.com/wiki/Heart_Rate_Reserve))
. <br/><br/>
  -**zone 1** ("Endurance") - < 136 BPM (i.e. < 50% HRR)
<br/><br/>
  -**zone 2** ("Moderate") - 136 - 152 BPM (i.e. 50% - 60% HRR)
<br/><br/>
  -**zone 3** ("Tempo") - 152 - 167 BPM (i.e. 50% - 60% HRR)
<br/><br/>
  -**zone 4** ("Threshold") - 167 - 182 BPM (i.e. 50% - 60% HRR)
<br/><br/>
  -**zone 5** ("Anaerobic") - > 182 BPM (i.e. > 90% HRR)
<br/><br/>
- **Pace zones** - ordinal variable ranging from 1 to 6 used to bin speeds (based on 5k race pace of 17:30). 
<br/><br/>
  -**zone 1** ("Active Recovery") - > 4:58/km 
<br/><br/>
  -**zone 2** ("Endurance") - 4:16/km - 4:58/km
<br/><br/>
  -**zone 3** ("Tempo") - 3:50/km - 4:16/km
<br/><br/>
  -**zone 4** ("Threshold") - 3:35/km - 3:50/km
<br/><br/>
  -**zone 5** ("VO2 Max") - 3:22/km - 3:35/km
<br/><br/>
  -**zone 6** ("Anaerobic") - < 3:22/km 
<br/><br/>
- **Run type** - nominal variable used to group activities according to distance and intensity. <br/><br/>
- **Event type** - nominal variable used to group races and workouts. <br/><br/>
- **Suffer score** - an integer value proportional to training load (based on heart rate and time). <br/><br/>
- **Chip time** - time elapsed after crossing start line (only relevant for races). 

**ETL Pipeline**

<img src="/images/ETL_pipeline.png" width="500"/> <br/><br/>

<img src="/images/ETL_pipeline_2.png" width = "500"/> <br/><br/>

**Database Schema**

<img src="/images/database_schema.png"/> <br/><br/>

## Data Cleaning

The cleaning process for this project involved:

- Imputing missing values with zeroes. <br/><br/>
- Converting dates from ISO-8601 format to PostgreSQL timestamps. <br/><br/>
- Extracting run types, event types, positions and chip times from activity names. <br/><br/>
- Converting hr zone distributions from wide to long format.

## EDA

<img src="/images/weekly_milage.png"/> <br/><br/>

<img src="/images/running_habits.png"/> <br/><br/>

<img src="/images/running_intensity.png"/> <br/><br/>

<img src="/images/days_of_week.png"/> <br/><br/>

