# importing libaries
## data import and storage
import numpy as np
import pandas as pd
import json
## postgresql wrapper for python
import psycopg2
## plotly libaries
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
## dash libaries
import dash
import dash_core_components as dcc
import dash_html_components as html

# setting style for app using CSS style sheet
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# initiating app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# creating a connection to postgresql database
with open('.secret/postgres_credentials.json', 'r') as r:
    postgres_credentials = json.load(r)
    user = postgres_credentials['user']
    password = postgres_credentials['password']

conn = psycopg2.connect(host="localhost", database="running_data", user=user, password=password)

# SQL queries
## SQL query for first figure
### calculating weights for 6-week moving averages
simple_weights = [1/6 for i in range(1,7)] 

linear_weights = [(7-i)/21 for i in range(1,7)] 

exp_factor = np.exp(2/7)
norm_constant = sum([exp_factor ** -i for i in range(1,7)])
exp_weights = [exp_factor ** -i / norm_constant for i in range(1,7)] 

all_weights = [(i, 1/6, (7-i)/21, exp_factor ** -i / norm_constant) for i in range(1,7)] 
values = str(all_weights)[1:-1]

### executing query
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

### storing tick values and labels
max_y_1 = int(np.ceil(df_1.total_distance.max() / 10) * 10)
y_tickvals_1 = list(range(0, max_y_1 + 10,10))
y_ticktext_1 = [str(y) + 'km' for y in y_tickvals_1]

## SQL query for second figure
### executing SQL query
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

### subsetting dataframe by run type
df_S = df_2.loc[df_2['run_type'] == 'S']
df_M = df_2.loc[df_2['run_type'] == 'M']
df_L = df_2.loc[df_2['run_type'] == 'L']
df_I = df_2.loc[df_2['run_type'] == 'I']

### storing marker positions
x_markers_S = list(df_S.month)[::len(list(df_S.month))-1]
y_markers_S = list(df_S.n_runs)[::len(list(df_S.n_runs))-1]

x_markers_M = list(df_M.month)[::len(list(df_M.month))-1]
y_markers_M = list(df_M.n_runs)[::len(list(df_M.n_runs))-1]

x_markers_L = list(df_L.month)[::len(list(df_L.month))-1]
y_markers_L = list(df_L.n_runs)[::len(list(df_L.n_runs))-1]

x_markers_I = list(df_I.month)[::len(list(df_I.month))-1]
y_markers_I = list(df_I.n_runs)[::len(list(df_I.n_runs))-1]

## SQL query for third figure
### executing SQL query
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

### subsetting dataframe by HR zone
df_z1 = df_3.loc[df_3['zone'] == 1]
df_z2 = df_3.loc[df_3['zone'] == 2]
df_z3 = df_3.loc[df_3['zone'] == 3]
df_z4 = df_3.loc[df_3['zone'] == 4]
df_z5 = df_3.loc[df_3['zone'] == 5]

### storing tick values and text
y_tickvals_3 = list(range(0, 120, 20))
y_ticktext_3 = [str(y) + '%' for y in y_tickvals_3]

# creating layout using dash core and dash html components
app.layout = html.Div(children=[

    ## main header
    html.H1(children='''
        Strava Data Exploration
    '''),

    ## header for first figure
    html.H2(children='''
        1) How has my weekly distance changing over time?
    '''), 

    ## description for first figure
    html.Div(children='''
        A line graph showing the 6-week moving average of my running distance for each week between January 2019 and Present.
    '''),

    ## first figure
    dcc.Graph(
        id='weekly-distance',
        figure={
            'data': [
                ### weekly distance scatter plot
                go.Scatter(
                    name='Week Distance',
                    x=df_1.week,
                    y=df_1.total_distance,
                    mode='markers',
                    marker = {'color': 'darkblue'},
                    hovertemplate='<b>%{y:}km</b>'
                ),
                ### 6-week moving average line
                go.Scatter(
                    name='6-Week Moving Average',
                    x = df_1.week, 
                    y = df_1.moving_avg, 
                    mode='lines',  
                    line = {'color': 'grey'}, 
                    hovertemplate='<b>%{y:}km</b>'),
                ### upper bound line
                go.Scatter(
                    name='Upper Bound',
                    x = df_1.week, 
                    y = df_1.upper_bound, 
                    mode = 'lines', 
                    line = {'color': 'rgba(204, 204, 204, 0)'}, 
                    fill = None,
                    hoverinfo='skip'),
                ### lower bound line
                go.Scatter(
                    name='Lower Bound',
                    x = df_1.week, 
                    y = df_1.lower_bound, 
                    mode = 'lines', 
                    line = {'color': 'rgba(204, 204, 204, 0)'}, 
                    fill = 'tonexty', 
                    hoverinfo='skip')
            ],
            'layout': go.Layout(
                xaxis={'title': {'text': '<b>Date</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False},
                yaxis={'title': {'text': '<b>Distance</b>', 'font': {'size': 15}, 'standoff': 30}, 'tickmode': 'array', 'tickvals': y_tickvals_1, 'ticktext': y_ticktext_1, 'zeroline': False},
                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                hovermode='x',
                showlegend=False,
                ### annotations for key events
                annotations=[
                    {'x': df_1.week[0],'y': df_1.moving_avg[0], 'xref': 'x', 'yref': 'y', 'text': 'Marathon Training<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                    {'x': df_1.week[14],'y': df_1.moving_avg[14], 'xref': 'x', 'yref': 'y', 'text': 'Marathon Week', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                    {'x': df_1.week[41],'y': df_1.moving_avg[41], 'xref': 'x', 'yref': 'y', 'text': 'DS Course<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': -40, 'font': {'size': 8}},
                    {'x': df_1.week[56],'y': df_1.moving_avg[56], 'xref': 'x', 'yref': 'y', 'text': 'DS Course<br>Ends', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                    {'x': df_1.week[64],'y': df_1.moving_avg[64], 'xref': 'x', 'yref': 'y', 'text': 'Lockdown<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}}
                    ]
            )
        }
    ),

    ## header for second figure
    html.H2(children='''
        2) How have my running habits changing over time?
    '''), 

    ## description for second figure
    html.Div(children='''
        A bump chart showing how my runs were distributed between run types for each month between January 2019 and Present.
    '''),

    ## second figure
    dcc.Graph(
        id='running-habits',
        figure={
            'data': [
                ### number of runs per month lines
                #### short run line
                go.Scatter(
                    name = 'Short run',
                    x=df_S.month, 
                    y=df_S.n_runs, 
                    mode = 'lines', 
                    line = dict(shape = 'spline', width = 15, color = 'rgba(0, 82, 204, 0.5)'),
                    hovertemplate='<b>%{y:} runs</b>'),
                #### mid run line
                go.Scatter(
                    name = 'Mid run',
                    x=df_M.month, 
                    y=df_M.n_runs,
                    mode = 'lines', 
                    line = dict(shape = 'spline', width = 15, color = 'rgba(204, 0, 0, 0.5)'),
                    hovertemplate='<b>%{y:} runs</b>'),
                #### long run line
                go.Scatter(
                    name = 'Long run',
                    x=df_L.month, 
                    y=df_L.n_runs,
                    mode = 'lines', 
                    line = dict(shape = 'spline', width = 15, color = 'rgba(0, 153, 51, 0.5)'),
                    hovertemplate='<b>%{y:} runs</b>'),
                #### intervals line
                go.Scatter(
                    name = 'Intervals',
                    x=df_I.month, 
                    y=df_I.n_runs,
                    mode = 'lines', 
                    line = dict(shape = 'spline', width = 15, color = 'rgba(204, 0, 204, 0.5)'),
                    hovertemplate='<b>%{y:} runs</b>'),
                ### start and end markers
                #### short run markers
                go.Scatter(
                    x = x_markers_S, 
                    y = y_markers_S, 
                    mode = 'markers + text', 
                    text = ['', list(df_S.n_runs)[-1]], 
                    textfont = dict(color = 'white'), 
                    marker = dict(size = 25, color = 'rgb(0, 82, 204)'), 
                    showlegend = False, 
                    hoverinfo = 'skip'),
                #### mid run markers
                go.Scatter(
                    x = x_markers_M, 
                    y = y_markers_M, 
                    mode = 'markers + text', 
                    text = ['', list(df_M.n_runs)[-1]], 
                    textfont = dict(color = 'white'), 
                    marker = dict(size = 25, color = 'rgb(204, 0, 0)'), 
                    showlegend = False, 
                    hoverinfo = 'skip'),
                #### long run markers
                go.Scatter(
                    x = x_markers_L, 
                    y = y_markers_L, 
                    mode = 'markers + text', 
                    text = ['', list(df_L.n_runs)[-1]],  
                    textfont = dict(color = 'white'), 
                    marker = dict(size = 25, color = 'rgb(0, 153, 51)'), 
                    showlegend = False, 
                    hoverinfo = 'skip'),
                #### intervals markers
                go.Scatter(
                    x = x_markers_I, 
                    y = y_markers_I, 
                    mode = 'markers + text', 
                    text = ['', list(df_I.n_runs)[-1]], 
                    textfont = dict(color = 'white'), 
                    marker = dict(size = 25, color = 'rgb(204, 0, 204)'), 
                    showlegend = False, 
                    hoverinfo = 'skip')
            ],
            'layout': go.Layout(
                xaxis={'title': {'text': '<b>Date</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False},
                yaxis={'title': {'text': '<b>Number of Runs</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False},
                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                hovermode='x'
            )
        }
    ),

    ## header for third figure
    html.H2(children='''
        3) How has the intensity of my training changed over time?
    '''), 

    ## description for third figure
    html.Div(children='''
        A stacked area chart showing how my time was distributed between heart rate zones for each moving 6-week period between January 2019 and Present.
    '''),

    ## third figure
    dcc.Graph(
        id='running-intensity',
        figure={
            'data': [
                ### 6-week moving average time in zone lines
                #### HR zone 1 line
                go.Scatter(
                    name = 'Zone 1', 
                    x=df_z1.week, 
                    y=df_z1.moving_percentage,
                    mode='lines', 
                    stackgroup = 1, 
                    line_color = 'rgba(255, 230, 230, 0)',
                    hoverinfo = 'x+y',
                    hovertemplate='<b>%{y:}%</b>'),
                #### HR zone 2 line
                go.Scatter(
                    name = 'Zone 2', 
                    x=df_z2.week, 
                    y=df_z2.moving_percentage,
                    mode='lines', 
                    stackgroup = 1, 
                    line_color = 'rgba(255, 153, 153, 0)',
                    hoverinfo = 'x+y',
                    hovertemplate='<b>%{y:}%</b>'),
                #### HR zone 3 line
                go.Scatter(
                    name = 'Zone 3', 
                    x=df_z3.week, 
                    y=df_z3.moving_percentage,
                    mode='lines', 
                    stackgroup = 1, 
                    line_color = 'rgba(255, 77, 77, 0)',
                    hoverinfo = 'x+y',
                    hovertemplate='<b>%{y:}%</b>'),
                #### HR zone 4 line
                go.Scatter(
                    name = 'Zone 4', 
                    x=df_z4.week, 
                    y=df_z4.moving_percentage,
                    mode='lines', 
                    stackgroup = 1, 
                    line_color = 'rgba(255, 0, 0, 0)',
                    hoverinfo = 'x+y',
                    hovertemplate='<b>%{y:}%</b>'),
                #### HR zone 5 line
                go.Scatter(
                    name = 'Zone 5', 
                    x=df_z5.week, 
                    y=df_z5.moving_percentage,
                    mode='lines', 
                    stackgroup = 1, 
                    line_color = 'rgba(179, 0, 0, 0)',
                    hoverinfo = 'x+y',
                    hovertemplate='<b>%{y:}%</b>')
            ],
            'layout': go.Layout(
                xaxis={'title': {'text': '<b>Date</b>', 'font': {'size': 15}, 'standoff': 30}, 'showgrid': False, 'zeroline': False},
                yaxis={'title': {'text': '<b>Percentage of Time</b>', 'font': {'size': 15}, 'standoff': 30}, 'range': (0, 100), 'tickvals': y_tickvals_3, 'ticktext': y_ticktext_3, 'showgrid': False, 'zeroline': False},
                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                hovermode='x'
            )
        }
    )
])

# running server
if __name__ == '__main__':
    app.run_server(debug=True)