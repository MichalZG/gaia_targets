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

# pd.options.display.float_format = '{:.2f}'.format

df = pd.read_csv('./gaia_targets_test.csv')
additional_columns = ['Alt UT', 'Alt UT+3', 'Alt UT+6']
offsets = [0, 3, 6]

columns = list(df.columns)
columns.extend(additional_columns)

columns = [{"name": i, "id": i} for i in columns]

for c in columns:
    if 'Alt UT' in c['name']:
        c['format'] = {'specifier': '.1f'} 

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
            'filter_query': '{Alt UT} > 30',
            'column_id': 'Alt UT',
        },
        'backgroundColor': '#1aff66',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT+3} > 30',
            'column_id': 'Alt UT+3',
        },
        'backgroundColor': '#1aff66',
        'color': 'black',
    },
    {
        'if': {
            'filter_query': '{Alt UT+6} > 30',
            'column_id': 'Alt UT+6',
        },
        'backgroundColor': '#1aff66',
        'color': 'black',
    },
]



controls = dbc.Form(
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


app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(controls, width={'size': 2, 'offset': 3}),
                dbc.Col(dcc.Graph(id='graph'), width={'size': 4}),
            ],
            align='center',
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
        html.Div(id='intermediate-value', style={'display': 'none'}),
    ],
    fluid=True,
)


@app.callback(
    [Output('intermediate-value', 'children'),
     Output('intermediate-value', 'data-altaz')],
    [Input('longitude', 'value'),
     Input('latitude', 'value'),
     Input('date-picker', 'value'),
     Input('ut', 'value')]
    )
def clean_data(longitude, latitude, date, ut):
    date = dt.strptime(re.split('T| ', date)[0], '%Y-%m-%d')
    date = date.replace(hour=int(ut))

    observer = get_observer(longitude, latitude)
    
    full_df = df.copy()
    altaz_df = df.copy()
    for i, (column_name, offset) in enumerate(zip(additional_columns, offsets)):
        alt_tab = []
        az_tab = []
        for j in range(len(df.index)):
            alt, az = get_alt(observer, date, offset, full_df.at[j, 'RA'], full_df.at[j, 'Dec'])
            alt_tab.append(alt)
            az_tab.append(az)

        full_df[column_name] = np.array(alt_tab)
        altaz_df['Alt'+str(i)] = np.array(alt_tab)
        altaz_df['Az'+str(i)] = np.array(az_tab)

    full_df['RA'] = full_df['RA'].map("{:,.5f}".format)
    full_df['Dec'] = full_df['Dec'].map("{:,.5f}".format)
    return full_df.to_json(date_format='iso', orient='split'), altaz_df.to_json(orient='split')


@app.callback(
    Output('graph', 'figure'),
    [Input('intermediate-value', 'data-altaz')],
)
def set_graph(data):
    data = pd.read_json(data, orient='split')
    fig = px.scatter_polar(data, r="Alt0", theta="Az0", range_r=[90, 0], hover_name='Name')

    return fig

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

    return round(target_altaz.alt.value, 1), round(target_altaz.az.value, 1)
    

if __name__ == '__main__':
    app.run_server(debug=True)