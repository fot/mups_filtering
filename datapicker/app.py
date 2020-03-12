import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_daq as daq

import pandas as pd
from datetime import datetime, timedelta
import requests
import plotly.graph_objects as go
import numpy as np
import json
# from textwrap import dedent as d
import sys
from os.path import expanduser
import urllib

home = expanduser("~")
addthispath = '../mups_filtering'
sys.path.append(addthispath)
import mups_filtering as mups

tab10 = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1','#ff9da7', '#9c755f', '#bab0ac']

domain = ''
base_url_constructor = domain + '/maude/mrest/FLIGHT/msid.json?m={}&ts={}&tp={}&ap=t'

datetime_now = datetime.strptime('2017:010', '%Y:%j') #datetime.today() - timedelta(days=355)
datetime_past =datetime.strptime('2017:001', '%Y:%j') #datetime.today() - timedelta(days=365)
one_sec = timedelta(seconds=1)

external_stylesheets = ['maude_style.css']
markdown_text = "No Points Selected"


def get_start_stop_time(starttime, stoptime):
    if len(starttime) == 8:
        starttime = datetime.strptime(starttime, '%Y:%j')
        stoptime = datetime.strptime(stoptime, '%Y:%j')

    elif len(starttime) == 11:

        starttime = datetime.strptime(starttime, '%Y:%j:%H')
        stoptime = datetime.strptime(stoptime, '%Y:%j:%H')

    elif len(starttime) == 14:
        starttime = datetime.strptime(starttime, '%Y:%j:%H:%M')
        stoptime = datetime.strptime(stoptime, '%Y:%j:%H:%M')

    elif len(starttime) == 17:
        starttime = datetime.strptime(starttime, '%Y:%j:%H:%M:%S')
        stoptime = datetime.strptime(stoptime, '%Y:%j:%H:%M:%S')

    elif len(starttime) == 21:
        starttime = datetime.strptime(starttime, '%Y:%j:%H:%M:%S.%f')
        stoptime = datetime.strptime(stoptime, '%Y:%j:%H:%M:%S.%f')

    else:
        starttime = datetime_past.strftime('%Y:%j:%H:%M:%S.%f')[:-3]
        stoptime = datetime_now.strftime('%Y:%j:%H:%M:%S.%f')[:-3]

    return starttime, stoptime


def query_maude(msid, t1, t2):
    url = base_url_constructor.format(msid.lower(), t1, t2)
    print(url)
    jsondata = requests.get(url).json()
    data = pd.DataFrame({'date': pd.to_datetime(jsondata['data-fmt-1']['times'], format='%Y%j%H%M%S%f'),
                         'telemetry': jsondata['data-fmt-1']['values']})

    if len(data['telemetry']) > 0:

        data['telemetry'] = data['telemetry'].astype("float64")

        returned_last_time = data['date'][len(data['date']) - 1]
        queried_last_time = datetime.strptime(t2, '%Y%j.%H%M%S%f')

        if (queried_last_time - returned_last_time) > timedelta(seconds=328):
            t1_new = returned_last_time + timedelta(seconds=.001)
            t1_new = t1_new.strftime('%Y%j.%H%M%S%f')[:-3]
            new_data = query_maude(msid, t1_new, t2)

            data = data.append(new_data)

    return data


time_axis_format = [
        dict(dtickrange=[None, 1000], value="%H:%M:%S.%L\n%Y:%j"),
        dict(dtickrange=[1000, 60000], value="%H:%M:%S\n%Y:%j"),
        dict(dtickrange=[60000, 86400000], value="%H:%M\n%Y:%j"),
        dict(dtickrange=[86400000, "M12"], value="%e %b\n%Y:%j"),
        dict(dtickrange=["M12", None], value="%Y")
    ]


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll',
    }
}

app.layout = html.Div(children=[

    html.Div([
        html.H1(children='MAUDE Dash Plot'),
        ],
        id="header",
        className="row flex-display",
        style={"margin-bottom": "25px"},
    ),
    # html.H4(children='{} Timeseries Data'.format(msid.upper())),

    html.Div(className='row', children=[
        html.Div([
            html.P(
                "MSID",
                className="control_label"
                ),

            dcc.Input(
                    id="msid", 
                    type="text",
                    debounce=True, 
                    value='pm2thv1t',
                ),
        ], className='two columns'),


        html.Div([
            html.P(
                "Start Time",
                className="control_label"
                ),

            dcc.Input(
                    id="starttime", 
                    type="text",
                    debounce=True, 
                    value=datetime_past.strftime('%Y:%j:%H:%M:%S.%f')[:-3],
                ),
        ], className='two columns'),


        html.Div([
            html.P(
                "Stop Time",
                className="control_label"
                ),

            dcc.Input(
                    id="stoptime",
                    type="text",
                    debounce=True,
                    value=datetime_now.strftime('%Y:%j:%H:%M:%S.%f')[:-3],
                ),
        ], className='two columns'),


        html.Div([

            html.Button('Update Telemetry', id='update_telemetry'),

        ], className='two columns', style={"margin-top": "35px"}),


        html.Div([

            html.Button('Clear Selected Points', id='clear_selection'),

        ], className='two columns', style={"margin-top": "35px"}),


        html.Div([

            html.P(
                "Select Data",
                className="control_label",
                id='toggle-switch-output'
            ),

            daq.ToggleSwitch(
                id='data-toggle',
                size=50,
                value=False
            ),

        ], className='two columns'),


    ], style={"margin-bottom": "25px"}),


    html.Div([

        html.Div([
            dcc.Graph(id='maudeplot',
                      style={'height': 800},
                      config={'displayModeBar': True})
        ])

    ]),


    html.Div([

        html.Div([

            html.P(markdown_text, id='selection-data'),

        ], className='twelve columns', style={'margin-top': '25px', 'margin-left': '0px'}),


        html.Div([

            html.Button('Prepare Data For Download', id='update-link'),

        ], className='twelve columns', style={"margin-top": "35px"}),


        html.Div([

            html.A('Download Data', id='download-link', download="selection_data.json", href="", target="_blank"),

        ], className='twelve columns', style={"margin-top": "35px"}),

    ]),


    html.Div([

        html.Div([
            dcc.Markdown("""
                **Zoom and Relayout Data Preview**
            """),
            html.Pre(id='relayout-data', style=styles['pre']),
        ], className='six columns', style={'margin-top': '25px', 'margin-left': '0px', 'overflowY': 'scroll',
                                           'height': 500}),

        html.Div([
            dcc.Markdown("""
                **Telemetry Data Preview**
            """),
            html.Pre(id='telemetry-data', style=styles['pre']),

        ], className='six columns', style={'margin-top': '25px', 'margin-bottom': '25px', 'margin-left': '35px',
                                           'margin-right': '0px'}),

    ]),

    html.Div([

        # html.P('     \n      ', id='bottomspace', style={'margin-top': '25px', 'margin-bottom': '25px'}),
        # html.Br(),

        html.Div([

            html.Button('Just a Button', id='nothing-link'),

        ], className='twelve columns', style={"margin-top": "35px"}),
        html.Br(),
        html.P('     \n      ', id='bottomspace', style={'margin-top': '25px', 'margin-bottom': '25px'}),

    ]),

    # Hidden div inside the app that stores the telemetry data
    html.Div(id='data_store', style={'display': 'none'}),
    html.Div(id='selected_store', style={'display': 'none'}),

])




@app.callback(
    Output('download-link', 'href'),
    [
        Input('update-link', 'n_clicks')
    ],
    [
        State('selected_store', 'children'),
        State('data_store', 'children'),
        State('msid', 'value'),
        State('starttime', 'value'),
        State('stoptime', 'value'),
    ])
def update_download_link(n_clicks, stored_selection_data, stored_telemetry, msid, starttime, stoptime):

    if stored_selection_data is not None:
        save_data = json.loads(stored_selection_data)
        save_data['msid'] = msid.lower()
        save_data['starttime'] = starttime
        save_data['stoptime'] = stoptime
    else:
        save_data = {'curve_1': [], 'curve_2': []}

    if stored_telemetry is not None:
        stored_telemetry = pd.read_json(stored_telemetry, orient='split')
        stored_telemetry['date'] = [dt_date.strftime('%Y:%j:%H:%M:%S.%f')[:-3] for dt_date in stored_telemetry['date']]
        stored_telemetry = stored_telemetry.to_dict(orient='list')

        for key in stored_telemetry:
            save_data[key] = stored_telemetry[key]

    save_data['msid'] = msid.lower()
    save_data['starttime'] = starttime
    save_data['stoptime'] = stoptime
    save_data = json.dumps(save_data)

    return "data:text/csv;charset=utf-8," + urllib.parse.quote(save_data)


@app.callback(
        Output('data_store', 'children'), 
        [
            Input('update_telemetry', 'n_clicks')
        ],
        [
            State('msid', 'value'), 
            State('starttime', 'value'), 
            State('stoptime', 'value'),
        ]
    )
def update_data(n_clicks, msid, starttime, stoptime):
    t1, t2 = get_start_stop_time(starttime, stoptime)
    t1 = t1.strftime('%Y%j.%H%M%S%f')[:-3]
    t2 = t2.strftime('%Y%j.%H%M%S%f')[:-3]

    df = query_maude(msid, t1, t2)
    if len(df['telemetry']) > 0:
        df['corrected_telemetry'] = mups.nearest_weighted_median_value_signal_correction(df['telemetry'].tolist(), num_points=3)
    else:
        df['corrected_telemetry'] = []

    return df.to_json(date_format='iso', orient='split')


@app.callback(
        Output('maudeplot', 'figure'), 
        [
            Input('update_telemetry', 'n_clicks'),
            Input('maudeplot', 'selectedData'),
            Input('data_store', 'children'),
            Input('selected_store', 'children'),
            Input('data-toggle', 'value')

        ],
        [
            State('msid', 'value')
        ]
    )
def update_plot(n_clicks, selectedData, jsondata, previously_selected, toggle, msid):

    if jsondata is not None:

        df = pd.read_json(jsondata, orient='split')
        df['date'] = pd.to_datetime(df['date'])

        if previously_selected is None:
            previously_selected_1 = []
            previously_selected_2 = []
        else:
            previously_selected = json.loads(previously_selected)
            previously_selected_1 = previously_selected['curve_1']
            previously_selected_2 = previously_selected['curve_2']

        selected_1 = previously_selected_1
        selected_2 = previously_selected_2

        if len(df['telemetry']) > 0:
                return {
                    'data': [
                    {'type': 'scatter',
                              'x': df['date'],
                              'y': df['telemetry'] ,
                              'line':{'color':'#dddddd'},
                              'name': 'Reference Data (Original Signal)'
                              },
                              {'type': 'scattergl',
                              'x': df['date'],
                              'y': df['telemetry'],
                              'mode': 'markers',
                              'marker': {'size': 2, 'opacity': 0.5, 'color': tab10[0]},
                              'customdata': df.index,
                              'selectedpoints': selected_1,
                              'selected': {'marker': {'size': 6, 'opacity': 0.5, 'color': tab10[0]}},
                              'name':'Uncorrected Telemetry'
                              },
                              {'type': 'scattergl',
                              'x': df['date'],
                              'y': df['corrected_telemetry'],
                              'mode': 'markers',
                              'marker': {'size': 2, 'opacity': 0.8, 'color': tab10[1]},
                              'customdata': df.index,
                              'selectedpoints': selected_2,
                              'selected': {'marker': {'size': 6, 'opacity': 0.5, 'color': tab10[1]}},
                              'name': 'Corrected Telemetry'
                               }
                              ],
                    'layout': {'legend': {'orientation': 'h'},
                               'dragmode': 'select',
                               'clickmode': 'event+select',
                               'uirevision': jsondata,
                               'yaxis':{'title': msid.upper(),
                                        # 'fixedrange':True,
                                        # 'rangeslider':{'visible': False}
                                        },
                               'xaxis':{'tickformatstops':time_axis_format,
                                        # 'range': [t1_plot, t2_plot ],
                                        # 'fixedrange':True,
                                        # 'rangeslider':{'visible': True}
                                        }}
                    }
    else:

        return {'data': [], 'layout': {'yaxis': {'title':'No Data', }}}


@app.callback(
    Output('selected_store', 'children'),
    [
        Input('maudeplot', 'selectedData'),
        Input('clear_selection', 'n_clicks_timestamp')
    ],
    [
        State('selected_store', 'children'),
        State('data-toggle', 'value')
    ],
    )
def store_selection_data(selectedData, n_clicks_timestamp, previously_selected, remove_data):

    now = datetime.now().timestamp()
    now_diff = now - 1

    if (n_clicks_timestamp is not None) and (n_clicks_timestamp / 1000. > now_diff):
        return json.dumps({'curve_1': [], 'curve_2': []})

    if selectedData is not None and 'points' in selectedData.keys():
        selected_points_1 = [p['pointIndex'] for p in selectedData['points'] if p['curveNumber'] == 1]
        selected_points_2 = [p['pointIndex'] for p in selectedData['points'] if p['curveNumber'] == 2]

    else:
        selected_points_1 = []
        selected_points_2 = []

    if previously_selected is not None:
        previously_selected = json.loads(previously_selected)

    else:
        previously_selected = {'curve_1': [], 'curve_2': []}

    if remove_data is False:
        if len(selected_points_1) > 0:
            previously_selected['curve_1'] = list(set(previously_selected['curve_1'] + selected_points_1))

        if len(selected_points_2) > 0:
            previously_selected['curve_2'] = list(set(previously_selected['curve_2'] + selected_points_2))

    else:
        if len(selected_points_1) > 0:
            previously_selected['curve_1'] = [sel.item() for sel in np.setdiff1d(previously_selected['curve_1'], selected_points_1)]

        if len(selected_points_2) > 0:
            previously_selected['curve_2'] = [sel.item() for sel in np.setdiff1d(previously_selected['curve_2'], selected_points_2)]

    return json.dumps(previously_selected, indent=2)


@app.callback(
    Output('relayout-data', 'children'),
    [Input('maudeplot', 'selectedData')])
def display_relayout_data(selectedData):
    return json.dumps(selectedData, indent=2)

# @app.callback(
#     Output('relayout-data', 'children'),
#     [Input('selected_store', 'children')])
# def display_relayout_data(s):
#     s = json.loads(s)
#     return json.dumps(s)


@app.callback(
    Output('telemetry-data', 'children'),
    [Input('data_store', 'children')])
def display_telemetry_data(td):
    td = pd.read_json(td, orient='split')
    return str(td.head())


@app.callback(
    Output('selection-data', 'children'),
    [Input('selected_store', 'children'),])
def display_selection_data(previously_selected):
    if previously_selected is None:
        return 'No Points Selected'
    else:
        previously_selected = json.loads(previously_selected)
        curve_1 = len(previously_selected['curve_1'])
        curve_2 = len(previously_selected['curve_2'])
        return f"Number of Points Selected: {curve_1 + curve_2}"


@app.callback(
    Output('toggle-switch-output', 'children'),
    [Input('data-toggle', 'value')])
def update_output(value):
    if value is False:
        s = 'Selecting Data'
    else:
        s = 'Removing Data'
    return s


if __name__ == '__main__':
    app.run_server(debug=True)
