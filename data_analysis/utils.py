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
import boto3

class IntervalsAPI:
    def __init__(self, base_url, athlete_id, api_key):
        self.base_url = base_url
        self.athlete_id = athlete_id
        self.api_key = api_key
        self.auth = HTTPBasicAuth('API_KEY', api_key)
        self.records_to_store = [
            'enhanced_speed', 'enhanced_altitude', 'cadence', 'power',
            'heart_rate', 'timestamp', 'position_lat', 'position_long'
        ]

    def _make_request(self, url):
        """Helper method to make HTTP requests with error handling"""
        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    def get_all_activities(self):
        """Get all activities from Intervals.icu"""
        events_url = f"{self.base_url}/athlete/{self.athlete_id}/events.csv"
        return self._make_request(events_url)

    def get_recent_activities(self, days=30):
        """
        Fetches activities from the current day up to 'days' days prior.
        
        Parameters:
        - days (int): Number of days to look back from today. Default is 30.
        
        Returns:
        - list: A list of activity dictionaries within the specified date range.
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        activities_url = f"{self.base_url}/athlete/{self.athlete_id}/activities?oldest={start_date_str}&newest={end_date_str}"
        
        response = self._make_request(activities_url)
        return response.json() if response else []

    def download_fit_file(self, activity_id, save_path):
        """
        Downloads the FIT file for a given activity ID from Intervals.icu.
        
        Parameters:
        - activity_id (str): The ID of the activity whose FIT file is to be downloaded.
        - save_path (str): The file path where the FIT file will be saved.
        """
        fit_file_url = f"{self.base_url}/activity/{activity_id}/fit-file"
        
        response = self._make_request(fit_file_url)
        if response:
            with open(save_path, 'wb') as fit_file:
                fit_file.write(response.content)
            print(f"FIT file successfully downloaded and saved to {save_path}")
            return True
        return False

    def fit_to_csv(self, fit_file_path, csv_file_path):
        """
        Converts a FIT file to a CSV file.
        
        Parameters:
        - fit_file_path: str, path to the input FIT file.
        - csv_file_path: str, path to the output CSV file.
        """
        try:
            fitfile = FitFile(fit_file_path)
            
            with open(csv_file_path, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                headers_written = False
                
                for record in fitfile.get_messages('record'):
                    record_data = {}
                    
                    for data in record:
                        if data.name in self.records_to_store:
                            record_data[data.name] = data.value
                    
                    if not headers_written:
                        headers = record_data.keys()
                        csv_writer.writerow(headers)
                        headers_written = True
                    
                    csv_writer.writerow(record_data.values())
            
            print(f"Conversion complete. CSV file saved as '{csv_file_path}'")
            return True
        except Exception as e:
            print(f"An error occurred during FIT to CSV conversion: {e}")
            return False
        


def convert_millis_to_datetime(millis):
    dt = datetime.fromtimestamp(millis/1000)
    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_time

def get_s3_folder_timestamps(folder_path):
    """Get first and last timestamp from accelerometer.csv in an S3 folder"""
    acc_file = os.path.join(folder_path, "accelerometer.csv")
    if not os.path.exists(acc_file):
        return None, None
    
    df = pd.read_csv(acc_file)
    if len(df) == 0:
        return None, None
        
    df['timestamp'] = df['timestamp'].apply(convert_millis_to_datetime)
    first_timestamp = df['timestamp'].iloc[0]
    last_timestamp = df['timestamp'].iloc[-1]
    return first_timestamp, last_timestamp

def get_garmin_file_timestamps(file_path):
    """Get first and last timestamp from a Garmin CSV file"""
    df = pd.read_csv(file_path)
    if len(df) == 0:
        return None, None
        
    first_timestamp = df['timestamp'].iloc[0]
    last_timestamp = df['timestamp'].iloc[-1]
    return first_timestamp, last_timestamp

def change_timestamp_to_belgian_time(timestamp):
    """Convert timestamp to Belgian time (Europe/Brussels)"""
    # Parse the timestamp
    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    
    # Make it UTC aware
    utc = pytz.UTC
    dt = utc.localize(dt)
    
    # Convert to Belgian time (Europe/Brussels timezone)
    belgian_tz = pytz.timezone('Europe/Brussels')
    belgian_time = dt.astimezone(belgian_tz)
    
    return belgian_time.strftime('%Y-%m-%d %H:%M:%S')


def get_kalman_orientation(row, kalman_filter):
    kalman_filter.computeAndUpdateRollPitch(row['x_acc'], row['y_acc'], row['z_acc'], row['x_gyro'], row['y_gyro'], 10)
    roll = kalman_filter.roll
    pitch = kalman_filter.pitch
    return roll, pitch

def process_s3_folder(s3_data_folder, s3_folder):
    # imu_data = []
    csv_files = sorted([f for f in os.listdir(os.path.join(s3_data_folder, s3_folder)) if f.endswith('.csv') ])
    acc_df = pd.read_csv(os.path.join(os.path.join(s3_data_folder, s3_folder), csv_files[0]))
    gyro_df = pd.read_csv(os.path.join(os.path.join(s3_data_folder, s3_folder), csv_files[1]))
    # mag_df = pd.read_csv(os.path.join(os.path.join(s3_data_folder, s3_folder), csv_files[2]))
    merged_df = pd.merge(acc_df, gyro_df, on='timestamp', how='inner', suffixes=('_acc', '_gyro'))
    Kalman_filter = Kalman()
    merged_df['roll'], merged_df['pitch'] = zip(*merged_df.apply(lambda row: get_kalman_orientation(row, Kalman_filter), axis=1))
    merged_df['timestamp'] = merged_df['timestamp'].apply(convert_millis_to_datetime)
    merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
    return merged_df


def plot_imu_garmin_comparison(imu_dfs, garmin_df, save_path= None):
    """
    Plot comparison between IMU and Garmin data for multiple IMU dataframes.
    
    Args:
        imu_dfs (list): List of IMU dataframes
        garmin_df (pd.DataFrame): Garmin dataframe with power and cadence data
    """
    # Create figure with subplots
    n_plots = len(imu_dfs)
    fig, axes = plt.subplots(n_plots, 1, figsize=(12, 6*n_plots))
    
    # If there's only one plot, make axes a list for consistency
    if n_plots == 1:
        axes = [axes]
    
    for idx, imu_df in enumerate(imu_dfs):
        # Filter Garmin data for this IMU dataframe's time range
        start_timestamp = imu_df['timestamp'].iloc[0]
        end_timestamp = imu_df['timestamp'].iloc[-1]
        garmin_df_filtered = garmin_df[(garmin_df['timestamp'] >= start_timestamp) & 
                                     (garmin_df['timestamp'] <= end_timestamp)]
        
        columns = ['roll', 'pitch']
        # Group IMU data by 1-second intervals
        imu_df_grouped = imu_df.groupby(pd.Grouper(key='timestamp', freq='5s'))[columns].agg(
            lambda x: x.quantile(0.75) - x.quantile(0.25)
        )
        
        # Get current axis
        ax1 = axes[idx]
        
        garmin_df_filtered['speed_kmh'] = garmin_df_filtered['enhanced_speed'] * 3.6
        
        # 5 seconds aggregate for garmin data
        garmin_df_filtered = garmin_df_filtered.groupby(pd.Grouper(key='timestamp', freq='5s'))[['speed_kmh', 'heart_rate']].agg(
            lambda x: x.mean()
        )
        
        # Plot power and cadence on left y-axis
        ax1.plot(garmin_df_filtered.index, garmin_df_filtered['speed_kmh'], 'b-', label='Speed')
        ax1.plot(garmin_df_filtered.index, garmin_df_filtered['heart_rate'], 'g-', label='HR')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Speed (km/h) / HR (BPM)', color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        
        # Create second y-axis for roll and pitch
        ax2 = ax1.twinx()
        ax2.plot(imu_df_grouped.index, imu_df_grouped['roll'], 'r-', label=f'Roll {imu_df_grouped["roll"].mean():.2f}')
        ax2.plot(imu_df_grouped.index, imu_df_grouped['pitch'], 'm-', label=f'Pitch {imu_df_grouped["pitch"].mean():.2f}')
        ax2.set_ylabel('Roll/Pitch (degrees)', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        ax2.set_ylim(0, 30)  # Set y-axis limits for roll and pitch
        
        # Make grid lines more visible
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # Format x-axis
        plt.setp(ax1.get_xticklabels(), rotation=45)
        
        # Add title for each subplot
        ax1.set_title(f'IMU Data {idx+1} {start_timestamp}')
    
    # Adjust layout
    plt.tight_layout()
    
    # Show plot
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()
        
def analyze_frame_rates(imu_dfs, save_path=None):
    """
    Analyze and plot frame rates for multiple IMU dataframes.
    
    Args:
        imu_dfs (list): List of pandas DataFrames containing IMU data
        save_path (str, optional): Path to save the plot. If None, plot is only displayed
    """
    n_dfs = len(imu_dfs)
    fig, axes = plt.subplots(n_dfs, 1, figsize=(12, 6*n_dfs))
    if n_dfs == 1:
        axes = [axes]
    
    for idx, (df, ax) in enumerate(zip(imu_dfs, axes)):
        # Calculate frame rate
        frame_rate = df.groupby(pd.Grouper(key='timestamp', freq='1s')).size()
        
        # Plot frame rate
        ax.plot(frame_rate.index, frame_rate.values)
        start_time = df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M:%S')
        ax.set_title(f'IMU Frame Rate Analysis - Start: {start_time}')
        ax.set_xlabel('Time')
        ax.set_ylabel('Samples per Second')
        ax.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()
    