import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import pandas as pd
import numpy as np
import json
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from datetime import datetime as dt
from astroplan import Observer
import plotly.graph_objs as go
import plotly.express as px
import re
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import time
from functools import wraps
import os
import requests
import settings


COLUMNS_NAMES_MAPPER = {
    'name': 'Name', 
    'ra': 'RA [h]', 
    'dec': 'Dec [deg]',
    'observations_number': 'Obs num',
    'magnitude': 'Mag',
    'importance': 'Imp',
    'days_from_last_observations': 'Last [d]',
    'cadence': 'Cad [d]',
    'priority': 'Priority'
}

# df = pd.read_csv('./gaia_targets_test.csv')
df = pd.read_json(requests.get(settings.DB_ADDRESS).content)
df = df.rename(columns=COLUMNS_NAMES_MAPPER)

additional_columns = ['Alt UT', 'Alt UT+3', 'Alt UT+6']
offsets = [0, 3, 6]

columns = list(df.columns)
columns.extend(additional_columns)

columns = [{"name": i, "id": i} for i in columns]


for c in columns:
    if 'Alt UT' in c['name']:
        c['format'] = {'specifier': '.1f'} 
        c['type'] = 'numeric'
    elif c['name'] in ['RA [h]', 'Dec [deg]']:
        c['format'] = {'specifier': '.5f'} 
        c['type'] = 'numeric'


app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = dash.Dash(__name__)

style_data_conditional = [
    {
        'if': {
            'filter_query': '{Alt UT} < 30',
            'column_id': 'Alt UT',
        },
        'backgroundColor': 'tomato',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT+3} < 30',
            'column_id': 'Alt UT+3',
        },
        'backgroundColor': 'tomato',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT+6} < 30',
            'column_id': 'Alt UT+6',
        },
        'backgroundColor': 'tomato',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT} >= 30',
            'column_id': 'Alt UT',
        },
        'backgroundColor': '#1aff66',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT+3} >= 30',
            'column_id': 'Alt UT+3',
        },
        'backgroundColor': '#1aff66',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT+6} >= 30',
            'column_id': 'Alt UT+6',
        },
        'backgroundColor': '#1aff66',
        'color': 'black',
    },
]



controls = dbc.FormGroup(
    [
        dbc.FormGroup(
            [
               dbc.Label("Longitude [E]: "), 
               dbc.Input(id="longitude", type="number", value=37.0, min=0, max=359),
            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label('Latitiude [N]: '),
                dbc.Input(id="latitude", type="number", value=37.0, min=-90, max=90),

            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label('Date: '),
                dbc.Input(id='date-picker', type='Date', value=dt.today().date())

            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label('UT Start: '),
                dbc.Input(id="ut", type="number", value=22, min=0, max=23),

            ]
        ),
    ],
    # body=True,
)

row1 = html.Tr([html.Td("Sunset [UT]:"), html.Td(id="sunset", children="")])
row2 = html.Tr([html.Td("Sunrise [UT]:"), html.Td(id="sunrise", children="")])
row3 = html.Tr([html.Td("Moon phase [%]:"), html.Td(id="moon_phase", children="")])
row4 = html.Tr([html.Td("Moon Alt/Az [deg]:"), html.Td(id="moon_altaz", children="")])
row5 = html.Tr([html.Td("LST:"), html.Td(id="LST", children="")])

table_body = [html.Tbody([row1, row2, row3, row4, row5])]

table = dbc.Table(table_body, bordered=False)

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(controls, width={'size': 2, 'offset': 2}),
                dbc.Col(dcc.Graph(id='graph'), width={'size': 3}),
                dbc.Col(table, width={'size': 3, 'offset': 0}),
            ],
            align='center',
        ),
        dbc.Row(
            [

            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    dash_table.DataTable(
                    id='table',
                    columns=columns,
                    # data=df.to_dict('records'),
                    sort_action="native",
                    filter_action="native",
                    sort_mode="multi",
                    style_cell={
                        'height': 'auto',
                        'minWidth': '110px', 'width': '110px', 'maxWidth': '110px',
                        'whiteSpace': 'normal'
                        },
                    style_data_conditional=style_data_conditional,
                    ), width={'size': 8, 'offset': 2}
                ),
            ],
            align='center', 
        ),
        html.Div(id='temp', style={'display': 'none'}, children=[]),
        html.Div(id='intermediate-value', style={'display': 'none'}),
        html.Div(id='main-data', style={'display': 'none'}, children=[]),
    ],
    fluid=True,
)


def timeit(func):
    @wraps(func)
    def _time_it(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            end = time.time() - start
            logfile.info(f"funtion <{func.__name__}> - total time: {end}s")
    return _time_it



"""
Functions fired ones on page start/refresh
"""

@app.callback(
    Output('main-data', 'children'),
    [Input('temp', 'children')]
)
@timeit
def refresh_data(_):
    try:
        df = pd.read_json(requests.get(settings.DB_ADDRESS).content)
        df = df.rename(columns=COLUMNS_NAMES_MAPPER)
    except:
        return []
    return df.to_json(orient='split')

@app.callback(
    Output('date-picker', 'value'),
    [Input('temp', 'children')]
)
@timeit
def refresh_date(_):
    return dt.today().date()

"""
Callbacks functions
"""

@app.callback(
    Output('intermediate-value', 'children'),
    [Input('main-data', 'children'),
     Input('longitude', 'value'),
     Input('latitude', 'value'),
     Input('date-picker', 'value'),
     Input('ut', 'value')]
    )
@timeit
def clean_data(main_data, longitude, latitude, date, ut):
    date = dt.strptime(re.split('T| ', date)[0], '%Y-%m-%d')
    date = date.replace(hour=int(ut))
    observer = get_observer(longitude, latitude)

    if not main_data:
        raise PreventUpdate
    full_df = pd.read_json(main_data, orient='split')
    # full_df = df.copy()
    for i, (column_name, offset) in enumerate(zip(additional_columns, offsets)):

        date_off = Time(date) + offset*u.hour
        altaz_frame = observer.altaz(date_off)

        full_df[column_name], full_df['Az'+str(i)] = get_altaz(
                full_df['RA [h]'], full_df['Dec [deg]'], altaz_frame)

    return full_df.to_json(date_format='iso', orient='split')


@app.callback(
    Output('graph', 'figure'),
    [Input('table', 'derived_virtual_data')],
)
@timeit
def set_graph(data):
    if not data:
        raise PreventUpdate
    data = pd.DataFrame(data)
    fig = px.scatter_polar(data, r="Alt UT", theta="Az0", range_r=[90, 0], hover_name='Name')

    return fig


@app.callback(
    Output('table', 'data'),
    [Input('intermediate-value', 'children')]
)
@timeit
def set_table_data(data):
    if not data:
        raise PreventUpdate
    data = pd.read_json(data, orient='split')
    return data.to_dict(orient='records')


@app.callback(
    [Output('sunset', 'children'),
     Output('sunrise', 'children'),
     Output('moon_phase', 'children'),
     Output('moon_altaz', 'children'),
     Output('LST', 'children')],
    [Input('longitude', 'value'),
     Input('latitude', 'value'),
     Input('date-picker', 'value'),
     Input('ut', 'value'),
     ]
    )
@timeit
def set_info(longitude, latitude, date, ut):
    observer = get_observer(longitude, latitude)
    date = dt.strptime(re.split('T| ', date)[0], '%Y-%m-%d')
    date = Time(date.replace(hour=int(ut)))

    sunset = observer.sun_set_time(date).strftime('%d-%m-%Y %H:%M:%S')
    sunrise = observer.sun_rise_time(date).strftime('%d-%m-%Y %H:%M:%S')
    moon_phase = observer.moon_phase(date + 1*u.day)
    moon_altaz = observer.moon_altaz(date + 1*u.day)
    moon_alt = str(round(moon_altaz.alt.deg, 0))
    moon_az = str(round(moon_altaz.az.deg, 0))
    lst = observer.local_sidereal_time(date)

    return sunset, sunrise, 100 - int(moon_phase.value / np.pi * 100), ", ".join([moon_alt, moon_az]), str(lst)


@timeit
def get_observer(longitude, latitude):
    location = EarthLocation.from_geodetic(longitude*u.deg, latitude*u.deg, 100*u.m)
    observer = Observer(location=location, name="Observer")

    return observer

@timeit
def get_altaz(ra, dec, altaz_frame):
    c = SkyCoord(ra * u.hour, dec * u.deg)
    target_altaz = c.transform_to(altaz_frame)

    return np.round(target_altaz.alt.value, 1), np.round(target_altaz.az.value, 1)
    

if __name__ == '__main__':

    import logging
    logging.basicConfig(filename='debug.log',level=logging.DEBUG)
    logfile = logging.getLogger('file')

    debug = False
    if os.environ.get('DASH_DEBUG', "0") == "1":
        debug = True

    app.run_server(host="0.0.0.0", port=8050, debug=debug)
