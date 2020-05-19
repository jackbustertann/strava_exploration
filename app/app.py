#------ Importing Libaries ------

# data import and storage
import numpy as np
import pandas as pd
import json
# postgresql wrapper for python
import psycopg2
# plotly
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
# dash
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
# modelling
from sklearn.neighbors import KernelDensity

#------ PostgreSQL Queries ------

# creating a connection to Heroku postgresql database
with open('.secret/postgres_credentials.json', 'r') as r:
    postgres_credentials = json.load(r)
    host = postgres_credentials['host']
    database = postgres_credentials['database']
    user = postgres_credentials['user']
    password = postgres_credentials['password']

conn = psycopg2.connect(host=host, database=database, user=user, password=password)

# query for first figure, first tab

## calculating weights for 6-week moving averages
### simple moving average
simple_weights = [1/6 for i in range(1,7)] 
### linearly weighted moving average
linear_weights = [(7-i)/21 for i in range(1,7)] 
### exponentially weighted moving average
exp_factor = np.exp(2/7)
norm_constant = sum([exp_factor ** -i for i in range(1,7)])
exp_weights = [exp_factor ** -i / norm_constant for i in range(1,7)] 
### all weights
all_weights = [(i, 1/6, (7-i)/21, exp_factor ** -i / norm_constant) for i in range(1,7)] 
values = str(all_weights)[1:-1]

## executing query
df_1 = pd.read_sql_query("""
WITH sub_1a AS(
SELECT
    date_trunc('week', MIN(timestamp)) AS min_date,
    date_trunc('week', MAX(timestamp)) AS max_date
FROM activities),
sub_1b AS(
SELECT 
    generate_series(min_date, max_date, '7 day'::interval) AS week
FROM sub_1a),
sub_1c AS(
SELECT 
    date_trunc('week', timestamp) AS week,
    SUM(distance) AS total_distance
FROM activities
GROUP BY 1),
week_distances AS(
SELECT
    b.week,
    coalesce(total_distance, 0) AS total_distance
FROM sub_1c c
RIGHT JOIN sub_1b b
ON c.week = b.week),

week_stds AS(
SELECT 
    week,
    total_distance,
    STDDEV(total_distance) OVER(ORDER BY week ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING) AS moving_std
FROM week_distances),

weights (index, simple_weight, linear_weight, exp_weight) AS (VALUES {}),

past_six_weeks_a AS(
SELECT 
    a.week,
    a.total_distance,
    a.moving_std,
    CAST(EXTRACT(EPOCH FROM a.week - b.week) / (3600 * 24 * 7) AS int) AS weeks_before,
    b.total_distance AS before_distance
FROM week_stds a
JOIN week_stds b
ON CAST(EXTRACT(EPOCH FROM a.week - b.week) / (3600 * 24 * 7) AS int) BETWEEN 1 AND 6
ORDER BY 1, 2),

past_six_weeks_b AS(
SELECT 
    week,
    total_distance,
    moving_std,
    before_distance,
    simple_weight,
    linear_weight,
    exp_weight
FROM past_six_weeks_a a
JOIN weights b
ON a.weeks_before = b.index),

moving_averages AS(
SELECT 
    week,
    total_distance,
    moving_std,
    SUM(before_distance * simple_weight) AS simple_moving_avg,
    SUM(before_distance * linear_weight) AS linear_moving_avg,
    SUM(before_distance * exp_weight) AS exp_moving_avg
FROM past_six_weeks_b
WHERE EXTRACT(WEEK FROM week) = 1 OR EXTRACT(YEAR FROM week) > 2018
GROUP BY 1, 2, 3)

SELECT 
    week,
    ROUND(total_distance::numeric, 1) AS total_distance,
    ROUND(simple_moving_avg::numeric, 1) AS moving_avg,
    ROUND((simple_moving_avg - moving_std)::numeric, 1) AS lower_bound,
    ROUND((simple_moving_avg + moving_std)::numeric, 1) AS upper_bound
FROM moving_averages
""".format(values), conn)

# storing tick values and text
y_tickvals_1 = list(range(0, 90, 10))
y_ticktext_1 = [str(y) + 'km' for y in y_tickvals_1]

# query for second figure, first tab

## executing query
df_2 = pd.read_sql_query("""
WITH run_types (run_type) AS (VALUES ('S'), ('M'), ('L'), ('I')),
sub_1a AS(
SELECT
    date_trunc('month', MIN(timestamp)) AS min_date,
    date_trunc('month', MAX(timestamp)) AS max_date
FROM activities),
sub_1b AS(
SELECT 
    generate_series(min_date, max_date, '1 month'::interval) AS month
FROM sub_1a),
sub_1c AS(
SELECT 
    month,
    run_type
FROM sub_1b
CROSS JOIN run_types),
sub_1d AS(
SELECT
    date_trunc('month', timestamp) AS month, 
    run_type, 
    COUNT(*) AS n_runs
FROM activities 
WHERE run_type NOT IN ('WU', 'WD')
GROUP BY 1, 2
ORDER BY 1, 2),
sub_1e AS(
SELECT 
    b.month,
    b.run_type,
    coalesce(n_runs, 0) AS n_runs
FROM sub_1d a
RIGHT JOIN sub_1c b
ON a.month = b.month AND a.run_type = b.run_type)
SELECT 
    month,
    run_type,
    n_runs,
    RANK() OVER(PARTITION BY month ORDER BY n_runs) AS rt_rank
FROM sub_1e
WHERE EXTRACT(YEAR FROM month) > 2018
ORDER BY 1, 2;
""", conn)

## subsetting dataframe by run type
df_S = df_2.loc[df_2['run_type'] == 'S']
df_M = df_2.loc[df_2['run_type'] == 'M']
df_L = df_2.loc[df_2['run_type'] == 'L']
df_I = df_2.loc[df_2['run_type'] == 'I']

## storing run type marker postions
### short runs
x_markers_S = list(df_S.month)[::len(list(df_S.month))-1]
y_markers_S = list(df_S.n_runs)[::len(list(df_S.n_runs))-1]
### mid runs
x_markers_M = list(df_M.month)[::len(list(df_M.month))-1]
y_markers_M = list(df_M.n_runs)[::len(list(df_M.n_runs))-1]
### long runs
x_markers_L = list(df_L.month)[::len(list(df_L.month))-1]
y_markers_L = list(df_L.n_runs)[::len(list(df_L.n_runs))-1]
### intervals
x_markers_I = list(df_I.month)[::len(list(df_I.month))-1]
y_markers_I = list(df_I.n_runs)[::len(list(df_I.n_runs))-1]

# query for third figure, first tab

## executing query
df_3 = pd.read_sql_query("""
WITH zones (zone) AS (VALUES (1), (2), (3), (4), (5)),
weeks AS(
SELECT 
    generate_series(date_trunc('week', MIN(timestamp)), date_trunc('week', MAX(timestamp)), '1 week'::interval) AS week
FROM activities),
weeks_and_zones AS(
SELECT
    week,
    zone
FROM weeks
CROSS JOIN zones),
sub_1 AS(
SELECT 
    date_trunc('week', timestamp) AS week, 
    zone_index AS zone, 
    SUM(b.time) AS time
FROM activities a 
RIGHT JOIN activity_zones b 
ON a.id = b.activity_id 
WHERE zone_type = 'heartrate'
GROUP BY 1, 2),
sub_2 AS (
SELECT 
    b.week,
    b.zone,
    coalesce(time, 0) AS time
FROM sub_1 a
RIGHT JOIN weeks_and_zones b
ON a.week = b.week AND a.zone = b.zone),
sub_3 AS(
SELECT
    week,
    zone,
    time,
    SUM(time) OVER(PARTITION BY zone ORDER BY week) AS moving_sum_zone,    
    SUM(time) OVER(ORDER BY week) AS moving_sum_month
FROM sub_2),
sub_4 AS(
SELECT 
    a.week,
    a.zone,
    a.time,
    a.moving_sum_zone - b.moving_sum_zone AS moving_sum_zone,
    a.moving_sum_month - b.moving_sum_month AS moving_sum_month
FROM sub_3 a
JOIN sub_3 b
ON CAST(EXTRACT(EPOCH FROM a.week - b.week) / (3600 * 24 * 7) AS int) = 6 AND a.zone = b.zone
ORDER BY 1, 2)
SELECT 
    week,
    zone,
    time,
    ROUND((moving_sum_zone/moving_sum_month * 100)::numeric, 1) AS moving_percentage
FROM sub_4
WHERE EXTRACT(WEEK FROM week) = 1 OR EXTRACT(YEAR FROM week) > 2018;;
""", conn)

## subsetting dataframe by HR zone
df_z1 = df_3.loc[df_3['zone'] == 1]
df_z2 = df_3.loc[df_3['zone'] == 2]
df_z3 = df_3.loc[df_3['zone'] == 3]
df_z4 = df_3.loc[df_3['zone'] == 4]
df_z5 = df_3.loc[df_3['zone'] == 5]

## storing tick values and text
y_tickvals_3 = list(range(0, 120, 20))
y_ticktext_3 = [str(y) + '%' for y in y_tickvals_3]

# query for third and fourth figures, second tab

## executing query
df_4 = pd.read_sql_query("""
SELECT
    CAST(timestamp::date AS TEXT) AS date,
    location,
    split_index,
    ((1/b.average_speed) * 3600)::int AS split_time,
    b.average_hr AS average_hr,
    (AVG(b.average_hr) OVER(PARTITION BY location, split_index))::int AS total_average_hr
FROM activities a
RIGHT JOIN activity_splits b
ON a.id = b.activity_id
WHERE event_type = 'PR' AND split_index <= 5 AND timestamp::date != '2019-11-09'
ORDER BY 1, 3;
""", conn)

### converting seconds in MM:SS format for tick text
def seconds_to_MMSS(total_seconds):
    minutes = total_seconds // 60
    seconds = total_seconds - (minutes * 60)
    return '{}:{:02}'.format(minutes, seconds)

### storing tick values and text
x_tickvals_4 = list(range(180, 270, 15))
x_ticktext_4 = [seconds_to_MMSS(x) for x in x_tickvals_4]
y_tickvals_4 = list(np.arange(0, 1, 0.02))
y_ticktext_4 = ['Split ' + str(i) if i <= 5 else ' ' for i in range(1, 9)]

# query for first figure, second tab

## executing query
df_5 = pd.read_sql_query("""
WITH sub_1 AS(
SELECT
    timestamp,
    location,
    chip_time,
    position,
    MIN(chip_time) OVER(PARTITION BY location ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS best_time
FROM activities
WHERE event_type = 'PR' AND timestamp::date != '2019-11-09')
SELECT 
    ROW_NUMBER() OVER(PARTITION BY location ORDER BY timestamp) AS n,
    CAST(timestamp::date AS TEXT) AS date,
    location,
    chip_time,
    position,
    coalesce(best_time, chip_time) - chip_time AS time_diff
FROM sub_1
ORDER BY 1;
""", conn)

## re-formatting times from seconds to MM:SS format
df_5['chip_time'] = df_5['chip_time'].map(lambda x: seconds_to_MMSS(x))

### storing tick values and text
y_tickvals_5 = list(range(-80, 40, 20))
y_ticktext_5 = [str(-y) + 's' for y in y_tickvals_5]

# query for second figure, second tab
df_6 = pd.read_sql_query("""
SELECT
    EXTRACT(YEAR FROM timestamp)::int AS year,
    location,
    MIN(chip_time) AS best_time
FROM activities a
WHERE event_type = 'PR'
GROUP BY 1, 2
ORDER BY 1, 2;
""", conn)

### storing tick values and text
#### x-axis
x_tickvals_6 = list(range(6))
x_ticktext_6 = [''] + list(range(1,6))
#### y-axis
y_tickvals_6 = [121, 136, 152, 167, 183, 198]
y_ticktext_6 = [str(y) + ' BPM' for y in y_tickvals_6]

## re-formatting times from seconds to MM:SS format
df_6['best_time'] = df_6['best_time'].apply(lambda x: seconds_to_MMSS(x))

#------ Dash App ------

# setting app style
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# initiating app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# setting app layout
app.layout = html.Div(children=[
    ## app header
    html.H1(children='Strava Data Exploration', style = {'textAlign': 'center'}),
    html.H3(children='Jack Tann', style = {'textAlign': 'center'}
    ),
    ## tabs
    dcc.Tabs([
        ## first tab
        dcc.Tab(label='Trends', children=[
            ### container for first figure 
            html.Div(children = [
                #### header
                html.H3(children='How has my weekly distance changing over time?'), 
                #### figure
                dcc.Graph(
                    id='weekly-distance',
                    figure={
                        'data': [
                            ##### weekly distance markers
                            go.Scatter(
                                name='Week Distance',
                                x=df_1.week,
                                y=df_1.total_distance,
                                mode='markers',
                                marker = {'color': 'darkblue'},
                                hovertemplate='<b>%{y:}km</b>'),
                            ##### 6-week moving average line
                            go.Scatter(
                                name='6-Week Moving Average',
                                x = df_1.week, 
                                y = df_1.moving_avg, 
                                mode='lines',  
                                line = {'color': 'grey'}, 
                                hovertemplate='<b>%{y:}km</b>'),
                            ##### upper bound line for shading
                            go.Scatter(
                                name='Upper Bound',
                                x = df_1.week, 
                                y = df_1.upper_bound, 
                                mode = 'lines', 
                                line = {'color': 'rgba(204, 204, 204, 0)'}, 
                                fill = None,
                                hoverinfo='skip'),
                            ##### lower bound line for shading
                            go.Scatter(
                                name='Lower Bound',
                                x = df_1.week, 
                                y = df_1.lower_bound, 
                                mode = 'lines', 
                                line = {'color': 'rgba(204, 204, 204, 0)'}, 
                                fill = 'tonexty', 
                                hoverinfo='skip')],
                        'layout': go.Layout(
                            xaxis={'title': {'text': '<b>Date</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False},
                            yaxis={'title': {'text': '<b>Distance</b>', 'font': {'size': 15}, 'standoff': 30}, 'tickmode': 'array', 'tickvals': y_tickvals_1, 'ticktext': y_ticktext_1, 'zeroline': False},
                            margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                            hovermode='x',
                            showlegend=False,
                            ##### annotations for key events
                            annotations=[
                                {'x': df_1.week[0],'y': df_1.moving_avg[0], 'xref': 'x', 'yref': 'y', 'text': 'Marathon Training<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                                {'x': df_1.week[14],'y': df_1.moving_avg[14], 'xref': 'x', 'yref': 'y', 'text': 'Marathon Week', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                                {'x': df_1.week[41],'y': df_1.moving_avg[41], 'xref': 'x', 'yref': 'y', 'text': 'DS Course<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': -40, 'font': {'size': 8}},
                                {'x': df_1.week[56],'y': df_1.moving_avg[56], 'xref': 'x', 'yref': 'y', 'text': 'DS Course<br>Ends', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                                {'x': df_1.week[64],'y': df_1.moving_avg[64], 'xref': 'x', 'yref': 'y', 'text': 'Lockdown<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}}]
                            )
                        }
                    )
                ],
                style = {'width': '96%', 'textAlign': 'center', 'margin': 'auto'}),
            ### container for second and third figures
            html.Div(children = [
                #### container for second figure
                html.Div(children = [
                    ##### header
                    html.H3(children='How have my running habits changing over time?'), 
                    ##### figure
                    dcc.Graph(
                        id='running-habits',
                        figure={
                            'data': [
                                ###### run type lines
                                ####### short runs
                                go.Scatter(
                                    name = 'Short run',
                                    x=df_S.month, 
                                    y=df_S.n_runs, 
                                    mode = 'lines', 
                                    line = dict(shape = 'spline', width = 15, color = 'rgba(0, 82, 204, 0.5)'),
                                    hovertemplate='<b>%{y:} runs</b>'),
                                ####### mid runs
                                go.Scatter(
                                    name = 'Mid run',
                                    x=df_M.month, 
                                    y=df_M.n_runs,
                                    mode = 'lines', 
                                    line = dict(shape = 'spline', width = 15, color = 'rgba(204, 0, 0, 0.5)'),
                                    hovertemplate='<b>%{y:} runs</b>'),
                                ####### long runs
                                go.Scatter(
                                    name = 'Long run',
                                    x=df_L.month, 
                                    y=df_L.n_runs,
                                    mode = 'lines', 
                                    line = dict(shape = 'spline', width = 15, color = 'rgba(0, 153, 51, 0.5)'),
                                    hovertemplate='<b>%{y:} runs</b>'),
                                ####### intervals
                                go.Scatter(
                                    name = 'Intervals',
                                    x=df_I.month, 
                                    y=df_I.n_runs,
                                    mode = 'lines', 
                                    line = dict(shape = 'spline', width = 15, color = 'rgba(204, 0, 204, 0.5)'),
                                    hovertemplate='<b>%{y:} runs</b>'),
                                ###### run type markers
                                ####### short runs
                                go.Scatter(
                                    x = x_markers_S, 
                                    y = y_markers_S, 
                                    mode = 'markers + text', 
                                    text = ['', list(df_S.n_runs)[-1]], 
                                    textfont = dict(color = 'white'), 
                                    marker = dict(size = 25, color = 'rgb(0, 82, 204)'), 
                                    showlegend = False, 
                                    hoverinfo = 'skip'),
                                ####### mid runs
                                go.Scatter(
                                    x = x_markers_M, 
                                    y = y_markers_M, 
                                    mode = 'markers + text', 
                                    text = ['', list(df_M.n_runs)[-1]], 
                                    textfont = dict(color = 'white'), 
                                    marker = dict(size = 25, color = 'rgb(204, 0, 0)'), 
                                    showlegend = False, 
                                    hoverinfo = 'skip'),
                                ####### long runs
                                go.Scatter(
                                    x = x_markers_L, 
                                    y = y_markers_L, 
                                    mode = 'markers + text', 
                                    text = ['', list(df_L.n_runs)[-1]],  
                                    textfont = dict(color = 'white'), 
                                    marker = dict(size = 25, color = 'rgb(0, 153, 51)'), 
                                    showlegend = False, 
                                    hoverinfo = 'skip'),
                                ####### intervals
                                go.Scatter(
                                    x = x_markers_I, 
                                    y = y_markers_I, 
                                    mode = 'markers + text', 
                                    text = ['', list(df_I.n_runs)[-1]], 
                                    textfont = dict(color = 'white'), 
                                    marker = dict(size = 25, color = 'rgb(204, 0, 204)'), 
                                    showlegend = False, 
                                    hoverinfo = 'skip')],
                            'layout': go.Layout(
                                xaxis={'title': {'text': '<b>Date</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False},
                                yaxis={'title': {'text': '<b>Number of Runs</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False},
                                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                                hovermode='x')
                            }
                        )
                    ],
                    style = {'textAlign': 'center', 'width': '55%', 'display': 'inline-block'}),
                #### container for third figure
                html.Div(children = [
                    ##### header
                    html.H3(children='''
                        How has the intensity of my training changed over time?
                    '''), 
                    ##### figure
                    dcc.Graph(
                        id='running-intensity',
                        figure={
                            'data': [
                                ###### 6-week moving average lines
                                ####### HR zone 1
                                go.Scatter(
                                    name = 'Zone 1', 
                                    x=df_z1.week, 
                                    y=df_z1.moving_percentage,
                                    mode='lines', 
                                    stackgroup = 1, 
                                    line_color = 'rgba(255, 230, 230, 0)',
                                    hoverinfo = 'x+y',
                                    hovertemplate='<b>%{y:}%</b>'),
                                ####### HR zone 2
                                go.Scatter(
                                    name = 'Zone 2', 
                                    x=df_z2.week, 
                                    y=df_z2.moving_percentage,
                                    mode='lines', 
                                    stackgroup = 1, 
                                    line_color = 'rgba(255, 153, 153, 0)',
                                    hoverinfo = 'x+y',
                                    hovertemplate='<b>%{y:}%</b>'),
                                ####### HR zone 3
                                go.Scatter(
                                    name = 'Zone 3', 
                                    x=df_z3.week, 
                                    y=df_z3.moving_percentage,
                                    mode='lines', 
                                    stackgroup = 1, 
                                    line_color = 'rgba(255, 77, 77, 0)',
                                    hoverinfo = 'x+y',
                                    hovertemplate='<b>%{y:}%</b>'),
                                ####### HR zone 4
                                go.Scatter(
                                    name = 'Zone 4', 
                                    x=df_z4.week, 
                                    y=df_z4.moving_percentage,
                                    mode='lines', 
                                    stackgroup = 1, 
                                    line_color = 'rgba(255, 0, 0, 0)',
                                    hoverinfo = 'x+y',
                                    hovertemplate='<b>%{y:}%</b>'),
                                ####### HR zone 5
                                go.Scatter(
                                    name = 'Zone 5', 
                                    x=df_z5.week, 
                                    y=df_z5.moving_percentage,
                                    mode='lines', 
                                    stackgroup = 1, 
                                    line_color = 'rgba(179, 0, 0, 0)',
                                    hoverinfo = 'x+y',
                                    hovertemplate='<b>%{y:}%</b>')],
                            'layout': go.Layout(
                                xaxis={'title': {'text': '<b>Date</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False, 'zeroline': False},
                                yaxis={'title': {'text': '<b>Percentage of Time</b>', 'font': {'size': 15}, 'standoff': 30}, 'range': (0, 100), 'tickvals': y_tickvals_3, 'ticktext': y_ticktext_3, 'showgrid': False, 'zeroline': False},
                                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                                hovermode='x')
                            }
                        )
                    ],
                    style = {'textAlign': 'center', 'width': '45%', 'display': 'inline-block'})
                ], 
                style = {'width': '96%', 'margin': 'auto'})]),
        ## second tab
        dcc.Tab(label='Parkrun Performance', children=[
            ### container for tab
            html.Div(children = [
                #### container for dropdown headers
                html.Div(children = [
                    ##### container for location header
                    html.Div(children = [
                        ###### header
                        html.H6(children='Choose a Location:')],
                        style={'width': '15%', 'display': 'inline-block'}),
                    ##### container for date header
                    html.Div(children = [
                        ###### header
                        html.H6(children='Choose an Event:')],
                        style={'width': '15%', 'display': 'inline-block'})]),
                #### container for dropdowns
                html.Div(children = [       
                    ##### container for location dropdown   
                    html.Div(children = [
                        ###### dropdown
                        dcc.Dropdown(
                            id='location-dropdown',
                            options=[{'label': 'Panshanger', 'value': 'Hertford'}, {'label': 'Ellenbrook', 'value': 'Hatfield'}],
                            value='Hatfield',
                            style = {'width': '150px'})],
                        style={'width': '15%', 'display': 'inline-block'}),
                    ##### container for date dropdown
                    html.Div(children = [
                        ###### dropdown
                        dcc.Dropdown(
                            id = 'date-dropdown',
                            style = {'width': '150px', 'display': 'inline-block'})
                        ],
                        style={'width': '15%', 'display': 'inline-block'})]),
                ### header for first and second figures
                html.H3(children="Are my finish times getting faster?", style = {'textAlign': 'center'}),
                ### container for first figure
                html.Div(children = [
                    #### figure
                    dcc.Graph(id='pr-times')],
                    style = {'width': '75%', 'display': 'inline-block'}),
                ### container for second figure
                html.Div(children = [
                    ### figure
                    dcc.Graph(id='year-bests')
                    ],
                    style = {'width': '25%', 'display': 'inline-block'}),
                ### container for third figure
                html.Div(children = [
                    #### header 
                    html.H3(children='How is my pace distributed during a race?'),
                    #### figure
                    dcc.Graph(id='km-splits')],
                    style = {'width': '60%', 'display': 'inline-block', 'textAlign': 'center'}),
                ### container for fourth figure
                html.Div(children = [
                    #### header
                    html.H3(children="How quickly do I fatigue during a race?"),
                    #### figure
                    dcc.Graph(id='hr-evolution')],
                    style = {'width': '40%', 'display': 'inline-block', 'textAlign': 'center'})
                ], 
                style = {'width': '96%', 'margin': 'auto'})])
            ])
        ]
    )

# app callbacks 

## callback for date dropdown
@app.callback(
    [Output('date-dropdown', 'options'),
    Output('date-dropdown', 'value')],
    [Input('location-dropdown', 'value')])

def update_dropdown(selected_location):
    ### filtering data on location
    df_5_location = df_5.loc[df_5.location == selected_location]
    ### storing dates for location
    all_dates = list(df_5_location.date)
    reduced_dates = [date for date in all_dates if int(date.split('-')[0]) > 2018]
    dropdown_options = [{'label': date, 'value': date} for date in reduced_dates]
    ### setting a default value
    dropdown_value = reduced_dates[-1]

    return dropdown_options, dropdown_value

## callback for first figure, second tab
@app.callback(
    Output('pr-times', 'figure'),
    [Input('location-dropdown', 'value'),
    Input('date-dropdown', 'value')])

def update_figure(selected_location, selected_date):
    ### offsetting line length for lollipops
    df_5['adjusted_time_diff'] = df_5.time_diff.map(lambda x: x - 1.5 if x > 0 else (x + 1.5 if x < 0 else 0))

    ### filtering dataframe on location
    df_5_location = df_5.loc[df_5.location == selected_location]
    ### subsetting dataframe on position
    first_pos = df_5_location.loc[df_5_location['position'] == 1] 
    second_pos = df_5_location.loc[df_5_location['position'] == 2] 
    third_pos = df_5_location.loc[df_5_location['position'] == 3] 
    other_pos = df_5_location.loc[df_5_location['position'] >= 4] 

    ### figure data
    data = []

    ### position markers
    position_markers = [
        #### first position
        go.Scatter(
            name = '1st',
            x = first_pos.n, 
            y = first_pos.time_diff, 
            mode = 'markers',
            marker = {'size': 15, 'color': 'rgb(255, 215, 0)'},
            customdata = first_pos,
            hovertemplate = 'Date: %{customdata[1]}<br>Finish time: %{customdata[3]}'),
        #### second position
        go.Scatter(
            name = '2nd',
            x = second_pos.n, 
            y = second_pos.time_diff, 
            mode = 'markers',
            marker = {'size': 15, 'color': 'silver'},
            customdata = second_pos,
            hovertemplate = 'Date: %{customdata[1]}<br>Finish time: %{customdata[3]}'),
        #### third position
        go.Scatter(
            name = '3rd',
            x = third_pos.n, 
            y = third_pos.time_diff, 
            mode = 'markers',
            marker = {'size': 15, 'color': 'rgb(205, 127, 50)'},
            customdata = third_pos,
            hovertemplate = 'Date: %{customdata[1]}<br>Finish time: %{customdata[3]}'),
        #### fourth position
        go.Scatter(
            name = 'Other',
            x = other_pos.n, 
            y = other_pos.time_diff, 
            mode = 'markers',
            marker = {'size': 15, 'color': 'grey'},
            customdata = other_pos,
            hovertemplate = 'Date: %{customdata[1]}<br>Finish time: %{customdata[3]}')]

    ### event lines
    event_lines = []
    #### creating line for each event
    for i in range(len(df_5_location)):
            event_lines.append(go.Scatter(
                x = [list(df_5_location.n)[i], list(df_5_location.n)[i]], 
                y = [0, list(df_5_location.adjusted_time_diff)[i]], 
                mode = 'lines',
                line = {'width': 3, 'color': 'grey'},
                hoverinfo = 'skip',
                showlegend = False))

    ### filtering dataframe on date   
    df_date = df_5.loc[df_5.date == selected_date]
    ### highlighted event line
    event_line = [go.Scatter(
        x = [list(df_date.n)[0], list(df_date.n)[0]], 
        y = [0, list(df_date.adjusted_time_diff)[0]], 
        mode = 'lines',
        line = {'width': 3, 'color': 'black'},
        hoverinfo = 'skip',
        showlegend = False)]

    ### appending figure components to data
    data += position_markers + event_lines + event_line

    return {
            'data': data,
            'layout': go.Layout(
                xaxis={'title': {'text': '<b>Event Number</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False, 'zeroline': False},
                yaxis={'title': {'text': '<b>Time off PB</b>', 'font': {'size': 15}, 'standoff': 30}, 'range': (-80, 20), 'tickvals': y_tickvals_5, 'ticktext': y_ticktext_5, 'showgrid': False, 'zeroline': False},
                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                hovermode='x'
            )
        }

## callback for second figure, second tab
@app.callback(
    Output('year-bests', 'figure'),
    [Input('location-dropdown', 'value')])

def update_figure(selected_location):
    ### filter dataframe on location
    df_6_location = df_6.loc[df_6['location'] == selected_location]
    ### table data
    data = [
        go.Table(
            header=dict(values=['Year', 'Best Time'], align='center', fill = {'color': 'grey'}, font = {'color': 'white', 'size': 14}),
            cells=dict(values=[df_6_location.year, df_6_location.best_time], align='center', fill = {'color': 'lightgrey'}, height = 30),
            columnwidth = [5,5])
    ]

    return {
        'data': data
    }

## callback for third figure, second tab
@app.callback(
    Output('km-splits', 'figure'),
    [Input('location-dropdown', 'value'),
    Input('date-dropdown', 'value')])

def update_figure(selected_location, selected_date):
    ### filtering dataframe on location
    df_4_location = df_4[df_4.location == selected_location]

    ### figure data
    data = []

    ### calculating kdes for split times
    split_kdes = []
    for i in range(1, 6):
        split_paces = np.array(df_4_location.loc[df_4_location['split_index'] == i]['split_time']).reshape(-1, 1)
        kde = KernelDensity(kernel='gaussian', bandwidth=5).fit(split_paces)
        split_range = np.array(range(180, 256)).reshape(-1,1)
        split_kde = list(np.exp(kde.score_samples(split_range)))
        split_kdes.append(split_kde)

    ### ridge lines (with fill)
    ridges = [
        #### fifth split
        go.Scatter(
            x = [180, 255], 
            y = [0.08, 0.08], 
            mode = 'lines', 
            line = {'color': 'rgba(0, 153, 204, 0)'},
            hoverinfo = 'skip'),
        go.Scatter(
            x = list(range(180, 256)), 
            y = [0.08 + i for i in split_kdes[4]], 
            line = {'color': 'rgb(0, 153, 204)'}, 
            fill = 'tonexty', 
            hoverinfo = 'skip'),
        #### fourth split
        go.Scatter(
            x = [180, 255], 
            y = [0.06, 0.06], 
            mode = 'lines', 
            line = {'color': 'rgba(0, 153, 204, 0)'},
            hoverinfo = 'skip'),
        go.Scatter(
            x = list(range(180, 256)), 
            y = [0.06 + i for i in split_kdes[3]], 
            line = {'color': 'rgb(0, 153, 204)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip'),
        #### third split
        go.Scatter(
            x = [180, 255], 
            y = [0.04, 0.04], 
            mode = 'lines', 
            line = {'color': 'rgba(0, 153, 204, 0)'},
            hoverinfo = 'skip'),
        go.Scatter(
            x = list(range(180, 256)), 
            y = [0.04 + i for i in split_kdes[2]], 
            line = {'color': 'rgb(0, 153, 204)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip'),
        #### second split
        go.Scatter(
            x = [180, 255], 
            y = [0.02, 0.02], 
            mode = 'lines', 
            line = {'color': 'rgba(0, 153, 204, 0)'},
            hoverinfo = 'skip'),
        go.Scatter(
            x = list(range(180, 256)), 
            y = [0.02 + i for i in split_kdes[1]], 
            line = {'color': 'rgb(0, 153, 204)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip'),
        #### first split
        go.Scatter(
            x = [180, 255], 
            y = [0, 0], 
            mode = 'lines', 
            line = {'color': 'rgba(0, 153, 204, 0)'},
            hoverinfo = 'skip'),
        go.Scatter(
            x = list(range(180, 256)), 
            y = [0 + i for i in split_kdes[0]], 
            line = {'color': 'rgb(0, 153, 204)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip')
        ]
    ### storing split times for selected event
    event_split_times = list(df_4.loc[df_4.date == selected_date]['split_time'])
    ### re-formatting split times from seconds to MM:SS format
    event_split_times_formatted = [seconds_to_MMSS(time) for time in event_split_times]
  
    ### split time markers
    time_markers = []
    for i in range(5):
        time_markers.append(go.Scatter(
            name = 'Split ' + str(i+1),
            x = [event_split_times[i]],
            y = [(i * 0.02) + split_kdes[i][event_split_times[i] - 180]],
            mode = 'markers',
            marker = {'color': 'black', 'size': 8},
            text = event_split_times_formatted[i],
            hoverinfo = 'text'
        ))
    
    ### split time lines
    time_lines = []
    for i in range(5):
        time_lines.append(go.Scatter(
            x = [event_split_times[i], event_split_times[i]],
            y = [i * 0.02, (i * 0.02) + split_kdes[i][event_split_times[i] - 180]],
            mode = 'lines',
            line = {'color': 'black', 'dash': 'dot'},
            hoverinfo = 'skip'
        ))

    ### appending figure components to data
    data += ridges + time_lines + time_markers

    return {
        'data': data,
        'layout': go.Layout(
            xaxis={'title': {'text': '<b>Split Time</b>', 'font': {'size': 15}, 'standoff': 30}, 'tickvals': x_tickvals_4, 'ticktext': x_ticktext_4, 'showgrid': False, 'zeroline': False},
            yaxis={'tickvals': y_tickvals_4, 'ticktext': y_ticktext_4, 'showgrid': False, 'zeroline': False},
            margin={'l': 60, 'b': 40, 't': 20, 'r': 20},
            hovermode='x',
            showlegend = False
        )
        }

## callback for fourth figure, second tab
@app.callback(
    Output('hr-evolution', 'figure'),
    [Input('location-dropdown', 'value'),
    Input('date-dropdown', 'value')])

def update_figure(selected_location, selected_date):
    ### filtering dataframe on location
    df_4_location = df_4.loc[df_4.location == selected_location]

    ### figure data
    data = []

    ### background shading for hr zones
    hr_zones = [
        #### hr zone 1
        go.Scatter(
            x = [0, 5], 
            y = [121, 121], 
            mode = 'lines', 
            line = {'color': 'rgba(255, 230, 230, 0)'},
            hoverinfo = 'skip',
            showlegend = False),
        go.Scatter(
            x = [0, 5], 
            y = [136, 136], 
            mode = 'lines', 
            line = {'color': 'rgba(255, 230, 230, 0)'},
            fill = 'tonexty',
            hoverinfo = 'skip',
            showlegend = False),
        #### hr zone 2
        go.Scatter(
            x = [0, 5], 
            y = [152, 152], 
            mode = 'lines', 
            line = {'color': 'rgba(255, 153, 153, 0)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip',
            showlegend = False),
        #### hr zone 3
        go.Scatter(
            x = [0, 5], 
            y = [167, 167], 
            mode = 'lines', 
            line = {'color': 'rgba(255, 77, 77, 0)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip',
            showlegend = False),
        #### hr zone 4
        go.Scatter(
            x = [0, 5], 
            y = [183, 183], 
            mode = 'lines', 
            line = {'color': 'rgba(255, 0, 0, 0)'}, 
            fill = 'tonexty',
            hoverinfo = 'skip',
            showlegend = False),
        #### hr zone 5
        go.Scatter(
            x = [0, 5], 
            y = [198, 198], 
            mode = 'lines', 
            line = {'color': 'rgba(179, 0, 0, 0)'},
            fill = 'tonexty',
            hoverinfo = 'skip',
            showlegend = False)
    ]
    
    ### location average line
    total_hrs = [121] + list(df_4_location.total_average_hr)
    total_hr_line = [go.Scatter(
        name = 'Location Average',
        x = list(range(6)), 
        y = total_hrs, 
        mode = 'lines',
        line = {'color': 'grey', 'width': 5, 'dash': 'dot'},
        hovertemplate = '%{y} BPM',
        showlegend = False)]

    ### event line
    df_4_event = df_4_location.loc[df_4_location.date == selected_date]
    event_hrs = [121] + list(df_4_event.average_hr)
    event_hr_line = [go.Scatter(
        name = selected_date,
        x = list(range(6)), 
        y = event_hrs, 
        mode = 'lines',
        line = {'color': 'black', 'width': 5},
        hovertemplate = '%{y} BPM',
        showlegend = False)]

    ### appending figure components to data
    data += hr_zones + total_hr_line + event_hr_line

    return {
        'data': data,
        'layout': go.Layout(
            xaxis={'title': {'text': '<b>Split Number</b>', 'font': {'size': 15}, 'standoff': 30}, 'tickvals': x_tickvals_6, 'ticktext': x_ticktext_6, 'showgrid': False, 'zeroline': False},
            yaxis={'title': {'text': '<b>Average Heart Rate</b>', 'font': {'size': 15}, 'standoff': 30}, 'tickvals': y_tickvals_6, 'ticktext': y_ticktext_6, 'showgrid': False, 'zeroline': False},
            margin={'l': 80, 'b': 40, 't': 20, 'r': 10},
            hovermode='x')
    }

# running server
server = app.server
if __name__ == '__main__':
    app.run_server(debug=True)