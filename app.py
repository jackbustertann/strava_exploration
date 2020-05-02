import numpy as np
import pandas as pd
import psycopg2	
import ETL_pipeline_functions

import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html

# setting style using CSS style sheet

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# creating a connection to postgresql database

conn = psycopg2.connect(host="localhost", database="running_data", user="jacktann", password="Buster#19")

# dataframe for first graph

simple_weights = [1/6 for i in range(1,7)] 

linear_weights = [(7-i)/21 for i in range(1,7)] 

exp_factor = np.exp(2/7)
norm_constant = sum([exp_factor ** -i for i in range(1,7)])
exp_weights = [exp_factor ** -i / norm_constant for i in range(1,7)] 

all_weights = [(i, 1/6, (7-i)/21, exp_factor ** -i / norm_constant) for i in range(1,7)] 
values = str(all_weights)[1:-1]

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

max_y = int(np.ceil(df_1.total_distance.max() / 10) * 10)
y_tickvals = list(range(0, max_y + 10,10))
y_ticktext = [str(y) + 'km' for y in y_tickvals]

# creating layout using dash core and dash html components

app.layout = html.Div(children=[

    html.H1(children='Strava Data Exploration'),

    html.H2(children='1) How is my weekly distance changing over time?'), 

    html.Div(children='''
        A line graph showing the 6-week moving average of my running distance for each week between January 2019 and Present.
    '''),

    dcc.Graph(
        id='weekly-distance',
        figure={
            'data': [

                go.Scatter(
                    name='Week Distance',
                    x=df_1.week,
                    y=df_1.total_distance,
                    mode='markers',
                    marker = {'color': 'darkblue'},
                    hovertemplate='<b>%{y:}km</b>'
                ),

                go.Scatter(
                    name='6-Week Moving Average',
                    x = df_1.week, 
                    y = df_1.moving_avg, 
                    mode='lines',  
                    line = {'color': 'grey'}, 
                    hovertemplate='<b>%{y:}km</b>'),

                go.Scatter(
                    name='Upper Bound',
                    x = df_1.week, 
                    y = df_1.upper_bound, 
                    mode = 'lines', 
                    line = {'color': 'rgba(204, 204, 204, 0)'}, 
                    fill = None,
                    hoverinfo='skip'),

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
                yaxis={'title': {'text': '<b>Distance</b>', 'font': {'size': 15}, 'standoff': 30}, 'tickmode': 'array', 'tickvals': y_tickvals, 'ticktext': y_ticktext},
                margin={'l': 60, 'b': 40, 't': 20, 'r': 10},
                hovermode='x',
                showlegend=False,
                annotations=[
                    {'x': df_1.week[0],'y': df_1.moving_avg[0], 'xref': 'x', 'yref': 'y', 'text': 'Marathon Training<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                    {'x': df_1.week[14],'y': df_1.moving_avg[14], 'xref': 'x', 'yref': 'y', 'text': 'Marathon Week', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                    {'x': df_1.week[41],'y': df_1.moving_avg[41], 'xref': 'x', 'yref': 'y', 'text': 'DS Course<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': -40, 'font': {'size': 8}},
                    {'x': df_1.week[56],'y': df_1.moving_avg[56], 'xref': 'x', 'yref': 'y', 'text': 'DS Course<br>Ends', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}},
                    {'x': df_1.week[64],'y': df_1.moving_avg[64], 'xref': 'x', 'yref': 'y', 'text': 'Lockdown<br>Starts', 'showarrow': True, 'arrowhead': 0, 'ax': 0, 'ay': 40, 'font': {'size': 8}}
                    ]
            )
        }
    )
])

# running server

if __name__ == '__main__':
    app.run_server(debug=True)