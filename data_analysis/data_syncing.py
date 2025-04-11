import pprint
from datetime import date
import json
from intervalsicu import Intervals
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import csv
from fitparse import FitFile
import os
import matplotlib.pyplot as plt
from imusensor.filters.kalman import Kalman
# import datetime
import pytz
import yaml
import boto3
from utils import IntervalsAPI, \
    get_s3_folder_timestamps, get_garmin_file_timestamps, \
        change_timestamp_to_belgian_time, process_s3_folder, \
            plot_imu_garmin_comparison, analyze_frame_rates

import argparse

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def command_line_args():
    parser = argparse.ArgumentParser(description='Data syncing and analysis')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the configuration file')
    return parser.parse_args()

# goal of the file

# pull the data from garmin/ intervals ICU
def download_garmin_data(config):
    intervals_api_file = config['garmin_env_file']
    with open(intervals_api_file, 'r') as f:
        intervals_api_data = json.load(f)
    
    intervals_api = IntervalsAPI(config['intervals_icu_base_url'], 
                                 intervals_api_data['intervals_icu']['athlete_id'], 
                                 intervals_api_data['intervals_icu']['api_key'])
    activities = intervals_api.get_recent_activities(days=30)
    
    bike_event_ids = []
    new_data_downloaded = False

    for act in activities:
        if "ride" in act['type'].lower():
            bike_event_ids.append(act['id'])

    for idx, act in enumerate(activities):
        if "ride" in act['type'].lower():
            event_id = act['id']
            timestamp = act['start_date_local']
            type = act['type']
            # convert the timestamp to YYYYMMDDHHMM
            timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
            timestamp = timestamp.strftime('%Y_%m_%d_%H%M')
            file_name = f"{config['garmin_data_folder']}/{type}_{timestamp}_{event_id}.fit"
            
            if not os.path.exists(file_name):
                intervals_api.download_fit_file(event_id, file_name)
                intervals_api.fit_to_csv(file_name, file_name.replace(".fit", ".csv") )
                
    return new_data_downloaded
        
def download_s3_data(config):
    env_file = config['s3_env_file']
    with open(env_file, 'r') as f:
        env_data = json.load(f)
        
    new_data_downloaded = False
        
    aws_access_key = env_data['accessKey']
    aws_secret_key = env_data['secretKey']
    aws_bucket_name = env_data['bucketName']
    aws_region = env_data['region']

    # get a list of folders in the bucket
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)

    # print the list of folders
    response = s3.list_objects_v2(Bucket=aws_bucket_name)
    for obj in response['Contents']:
        print(obj['Key'])


    local_data_folder = config['s3_data_folder']
    os.makedirs(local_data_folder, exist_ok=True)   
    # check if the s3 files are present in the local data folder
    for obj in response['Contents']:
        if obj['Key'] not in os.listdir(local_data_folder):
            local_file_path = os.path.join(local_data_folder, obj['Key'])
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            s3.download_file(aws_bucket_name, obj['Key'], local_file_path)
            new_data_downloaded = True

    return new_data_downloaded


def match_data(config):
    # get the list of files in the garmin data folder
    garmin_data_folder = config['garmin_data_folder']
    s3_data_folder = os.path.join(config['s3_data_folder'], "data")
    
    s3_folders = [f for f in os.listdir(s3_data_folder) if os.path.isdir(os.path.join(s3_data_folder, f))]
    s3_timestamps = {}

    for folder in s3_folders:
        folder_path = os.path.join(s3_data_folder, folder)
        first_ts, last_ts = get_s3_folder_timestamps(folder_path)
        if first_ts and last_ts:
            s3_timestamps[folder] = {
                'first_timestamp': first_ts,
                'last_timestamp': last_ts
            }

    # Process Garmin files
    garmin_files = [f for f in os.listdir(garmin_data_folder) if f.endswith('.csv')]
    garmin_timestamps = {}

    for file in garmin_files:
        file_path = os.path.join(garmin_data_folder, file)
        first_ts, last_ts = get_garmin_file_timestamps(file_path)
        if first_ts and last_ts:
            # Convert to Belgian time
            first_ts = change_timestamp_to_belgian_time(first_ts)
            last_ts = change_timestamp_to_belgian_time(last_ts)
            garmin_timestamps[file] = {
                'first_timestamp': first_ts,
                'last_timestamp': last_ts
            }

    print (s3_timestamps)
    print (garmin_timestamps)
    # Match S3 folders to Garmin files
    matches = {}
    for garmin_file, garmin_ts in garmin_timestamps.items():
        matching_folders = []
        for s3_folder, s3_ts in s3_timestamps.items():
            # Check if S3 data overlaps with Garmin data
            if (s3_ts['first_timestamp'] <= garmin_ts['last_timestamp'] and 
                s3_ts['last_timestamp'] >= garmin_ts['first_timestamp']):
                matching_folders.append(s3_folder)
        matches[garmin_file] = matching_folders# get the list of files in the s3 data folder
    return matches

def process_garmin_imu_data(config, garmin_file_name, s3_folders):
    # get the list of files in the garmin data folder
    garmin_data_folder = config['garmin_data_folder']
    s3_data_folder = os.path.join(config['s3_data_folder'], "data")
    analysis_data_folder = config['analysis_data_folder']
    
    imu_dfs = []
    for s3_folder in s3_folders:
        imu_data = process_s3_folder(s3_data_folder, s3_folder)
        imu_dfs.append(imu_data)

    # process the garmin file
    garmin_df = pd.read_csv(os.path.join(garmin_data_folder, garmin_file_name))
    garmin_df['timestamp'] = garmin_df['timestamp'].apply(change_timestamp_to_belgian_time)
    garmin_df['timestamp'] = pd.to_datetime(garmin_df['timestamp'])
    
    
    
    save_path = os.path.join(analysis_data_folder, garmin_file_name.replace(".csv", ""), "imu_garmin_comparison.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plot_imu_garmin_comparison(imu_dfs, garmin_df, save_path)
    
    # also the plot of frame rate dropping
    frame_rate_plot_path = os.path.join(analysis_data_folder, garmin_file_name.replace(".csv", ""), "frame_rate_analysis.png")
    os.makedirs(os.path.dirname(frame_rate_plot_path), exist_ok=True)
    analyze_frame_rates(imu_dfs, save_path=frame_rate_plot_path)
    

def perform_analysis(config, matches):
    
    for garmin_file, matching_folders in matches.items():
        print(f"\nGarmin file: {garmin_file}")
        print("Matching S3 folders:")
        if len(matching_folders) != 0:
            for folder in matching_folders:
                print(f"- {folder}")
            process_garmin_imu_data(config, garmin_file, matching_folders)  
        else:
            print("No matching S3 folders found")


def main():
    args = command_line_args()
    if not os.path.exists(args.config):
        raise FileNotFoundError(f"Config file {args.config} not found")
        
    config = load_config(args.config)
        
    new_garmin_data = download_garmin_data(config)
    new_s3_data = download_s3_data(config)
    if new_garmin_data or new_s3_data or config['perform_analysis']:
        matches = match_data(config)
        perform_analysis(config, matches)
    else:
        print("No new data to download")
    
if __name__ == "__main__":
    main()


