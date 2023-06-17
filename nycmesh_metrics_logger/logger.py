#%%
import pandas as pd
from datetime import date
import itertools
from influxdb import InfluxDBClient
from datetime import datetime
import os
import datetime

import nycmesh_metrics_logger.config as config
from nycmesh_metrics_logger.uisp_client import devices_to_df, get_device_history, get_uisp_devices

influx_client = InfluxDBClient(
    os.environ.get('DATABASE_HOST'),
    8086, 
    username=os.environ.get('DATABASE_USERNAME'), 
    password=os.environ.get('DATABASE_PASSWORD'), 
    database=config.database)

def get_60_ghz_interface(history):
    for interface in history['interfaces']:
        if interface['id'] == 'main':
            return interface

def get_device_histories(interval='day', device_limit=None):
    
    devices = get_uisp_devices()
    device_df = devices_to_df(devices)

    df = device_df[device_df['has60GhzRadio']==True]
    if device_limit is not None:
        df = df.head(device_limit)

    histories = []
    
    for device_id, device_name in zip(df['id'], df['name']):
        history = get_device_history(device_id, interval)
        
        history['name'] = device_name
        histories.append(history)

    return histories

def create_device_metrics(history):
    points = []
    for transmit_bytes in get_60_ghz_interface(history)['transmit']:

        utc_time = datetime.datetime.utcfromtimestamp(transmit_bytes['x']/1000)
        formatted_time = utc_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        point = {
            "measurement": "devices",
            "time": formatted_time,
            "tags": {
                "name": history['name'],
                },
            "fields": {
                "outage": 1 if transmit_bytes['y'] == 0 else 0
            }
        }
        points.append(point)
 
    return points

def log_devices(histories):

    print(f'Loaded {len(histories)} histories')

    # get flat timeseries for all devices
    nested_metrics = []
    for history in histories:
        try:
            nested_metrics.append(create_device_metrics(history))
        except:
            pass

    metrics = list(itertools.chain.from_iterable(nested_metrics))

    influx_client.write_points(metrics)


if __name__ == '__main__':
    histories = get_device_histories()
    log_devices(histories)
