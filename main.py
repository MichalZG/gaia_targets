import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
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

df = pd.read_csv('./gaia_targets_test.csv')

additional_columns = ['Alt UT', 'Alt UT+3', 'Alt UT+6']
offsets = [0, 3, 6]

columns = list(df.columns)
columns.extend(additional_columns)

columns = [{"name": i, "id": i} for i in columns]

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = dash.Dash(__name__)


app.layout = html.Div([
    html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.P('Longitude [E]'),
                    dcc.Input(id="longitude", type="number", value=37.0, min=0, max=359),
                ], className='row'),
                html.Div([
                    html.P('Latitiude [N]'),
                    dcc.Input(id="latitude", type="number", value=37.0, min=-90, max=90),
                ], className='row'),
            ]),
            html.Div([
                dcc.DatePickerSingle(
                    id='date-picker',
                    min_date_allowed=dt(2020, 1, 1),
                    max_date_allowed=dt(2044, 12, 31),
                    initial_visible_month=dt.now(),
                    date=str(dt.now()),
                    display_format="D-M-Y",
                    first_day_of_week=1,
                ),
            ], className='date'),
            html.Div([
                dcc.Input(id="ut", type="number", value=22, min=0, max=23),
            ], className='hour'),
        ], className='data'),
    ], className='row'),
    dash_table.DataTable(
        id='table',
        columns=columns,
        # data=df.to_dict('records'),
        sort_action="native",
        filter_action="native",
        sort_mode="multi",
        style_cell={
            'height': 'auto',
            'minWidth': '90px', 'width': '90px', 'maxWidth': '90px',
            'whiteSpace': 'normal'
        }
    ),

    html.Div(id='intermediate-value', style={'display': 'none'}),
], className="main")

@app.callback(
    Output('intermediate-value', 'children'),
    [Input('longitude', 'value'),
     Input('latitude', 'value'),
     Input('date-picker', 'date'),
     Input('ut', 'value')]
    )
def clean_data(longitude, latitude, date, ut):
    
    date = dt.strptime(re.split('T| ', date)[0], '%Y-%m-%d')
    date = date.replace(hour=int(ut))

    observer = get_observer(longitude, latitude)
    
    full_df = df.copy()
    for column_name, offset in zip(additional_columns, offsets):
        alt_tab = []
        for i in range(len(df.index)):
            alt_tab.append(get_alt(observer, date, offset, full_df.at[i, 'RA'], full_df.at[i, 'Dec']))

        full_df[column_name] = np.array(alt_tab)

    return full_df.to_json(date_format='iso', orient='split')

@app.callback(
    Output('table', 'data'),
    [Input('intermediate-value', 'children')]
)
def set_table_data(data):
    data = pd.read_json(data, orient='split')
    return data.to_dict(orient='records')


def get_observer(longitude, latitude):
    location = EarthLocation.from_geodetic(longitude*u.deg, latitude*u.deg, 100*u.m)
    observer = Observer(location=location, name="Observer")

    return observer

def get_alt(observer, date, offset, ra, dec):
    c = SkyCoord(ra, dec, unit="deg")
    date = Time(date) + offset*u.hour
    altaz_frame = observer.altaz(date)
    target_altaz = c.transform_to(altaz_frame)

    return round(target_altaz.alt.value, 1)
    

if __name__ == '__main__':
    app.run_server(debug=True)