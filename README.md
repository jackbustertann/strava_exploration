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
- **Pace zones** - ordinal variable ranging from 1 to 6 used to bin speeds (based on 5k race time of 17:30). 
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
- **Event type** - nominal variable used to distinguish races from workouts. <br/><br/>
- **Suffer score** - an integer value proportional to training load (based on heart rate and time). <br/><br/>
- **Chip time** - time elapsed between crossing start line and finish line (races only). 

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
- Converting heart rate zone distributions from wide to long format.

## EDA

<img src="/images/weekly_milage.png"/> <br/><br/>

<img src="/images/running_habits.png"/> <br/><br/>

<img src="/images/running_intensity.png"/> <br/><br/>

<img src="/images/days_of_week.png"/> <br/><br/>

## Web App

Technologies used to build web app:

- **Plotly**: to create visualisations. <br/><br/>
- **Dash**: to turn visualisations into interactive dashboards. <br/><br/>
- **Heroku**: to migrate PostgreSQL database to cloud and deploy Python app to the web. <br/><br/>

The two dashboards included in the app are:

- **Trends** - How has my training evolved over time? <br/><br/>
  - How has my weekly distance changed over time? 
  - How have my running habits changed over time
  - How has the intensity of my training changed over time? <br/><br/>
- **Parkrun Performance** - How do my Parkrun performances compare across different dates at a given location? <br/><br/>
  - Are my finish times getting faster?
  - How is my pace distributed during a race?
  - How quickly do I fatigue during a race? <br/><br/>
  
Web app URL: 
https://strava-exploration.herokuapp.com/ 

## Conclusions

- The intensity of my training has generally decreased since April last year. This demonstrates that I have made a conscious effort to reduce the intensity of my training post Marathon to enable a more sustained period of injury-free running. This is reflected in the gradual increase in my weekly running distance since December last year compared with my previous two, more short-lived, training cycles between January 2018 and June 2018, and June 2018 and December 2018. <br/><br/>
- I tend to experience brief periods of decline in my Parkrun performance after setting a PB at an event. This demonstrates that it is unrealistic to expect sustained periods of peak fitness throughout the year. This shows that training in extended blocks of 8-10 weeks is a more effective strategy for improving my race performances in the long run compared with trying to improve upon my times at each event.

## Limitations and Possible Extensions

- Analysis of heart rate evolution for Parkruns had to be aggregrated over each km split due to the noiseness of the raw signal, especially for later splits. This is likely to be a result of an increasing divergence between my actual heart rate and my measured heartrate at higher intensities. To overcome this problem a chest-based heart rate strap could be used to control for some of the factors contributing to these inaccuracies, such as: time delay, wrist movement and outside temperature.  <br/><br/>
- There were extended periods during both years where I did not participate in Parkrun events, mostly due to other race commitments within the club. This means I cannnot solely rely on Parkrun times as a proxy for current fitness levels. To reduce the sparsity in this data I could incorperate my finish times from other races, adjusting for differences in elevation gain and distance. Alternatively, to account for other contributing factors to fitness such as weekly training distance and intensity, I could attempt to train a linear model that outputs a real-time estimate of my fitness level.
