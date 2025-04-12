import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import pandas as pd
import argparse
import os
# from utils import convert_millis_to_datetime
from imusensor.filters.kalman import Kalman
from datetime import datetime

# Define vertices and edges for the cube
vertices = (
    (1, -2, -1),  # 0
    (1, 2, -1),   # 1
    (-1, 2, -1),  # 2
    (-1, -2, -1), # 3
    (1, -2, 1),   # 4
    (1, 2, 1),    # 5
    (-1, -2, 1),  # 6
    (-1, 2, 1)    # 7
)

edges = (
    (0, 1), (0, 3), (0, 4),
    (2, 1), (2, 3), (2, 7),
    (6, 3), (6, 4), (6, 7),
    (5, 1), (5, 4), (5, 7)
)

def Cube():
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

def displayCube(dataframe):
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -10)

    curr_roll = 0
    curr_pitch = 90
    curr_yaw = 0
    glRotatef(0 - curr_pitch, 0, 1, 0)
    glRotatef(0 - curr_yaw, 0, 0, 1)

    for index, row in dataframe.iterrows():
        roll = row['roll']
        pitch = row['pitch']    
        yaw = row.get('yaw', curr_yaw)  # Use current yaw if not in DataFrame

        glRotatef(roll - curr_roll, 1, 0, 0)
        curr_roll = roll


        glRotatef(pitch - curr_pitch, 0, 1, 0)
        curr_pitch = pitch

        glRotatef(yaw - curr_yaw, 0, 0, 1)
        curr_yaw = yaw

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        Cube()
        pygame.display.flip()
        pygame.time.wait(10)

    pygame.quit()
    
def convert_millis_to_datetime(millis):
    dt = datetime.fromtimestamp(millis/1000)
    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_time

def get_kalman_orientation(row, kalman_filter):
    kalman_filter.computeAndUpdateRollPitchYaw(row['x_acc'], row['y_acc'], row['z_acc'], 
                                            row['x_gyro'], row['y_gyro'], row['z_gyro'],
                                            row['x'], row['y'], row['z'],
                                            10)
    roll = kalman_filter.roll
    pitch = kalman_filter.pitch
    yaw = kalman_filter.yaw
    return roll, pitch, yaw

def process_folder(folder_path):
    csv_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.csv') ])
    acc_df = pd.read_csv(os.path.join(folder_path, csv_files[0]))
    gyro_df = pd.read_csv(os.path.join(folder_path, csv_files[1]))
    mag_df = pd.read_csv(os.path.join(folder_path, csv_files[2]))
    # mag_df['timestamp'] = mag_df['epoch'].apply(convert_millis_to_datetime)
    
    merged_df = pd.merge(acc_df, gyro_df, on='epoch', how='inner', suffixes=('_acc', '_gyro'))
    merged_df = pd.merge(merged_df, mag_df, on='epoch', how='outer')
    merged_df.interpolate(method='linear', inplace=True)
    merged_df.dropna(inplace=True)
    
    # mag df is low frequency, so we need to extraplolate it. 
    
    Kalman_filter = Kalman()
    merged_df['roll'], merged_df['pitch'], merged_df['yaw'] = zip(*merged_df.apply(lambda row: get_kalman_orientation(row, Kalman_filter), axis=1))
    merged_df['timestamp'] = merged_df['epoch'].apply(convert_millis_to_datetime)
    merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
    return merged_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display a rotating cube using roll and pitch from a CSV file.')
    parser.add_argument('--folder-path', type=str, help='Path to the folder containing acc, gyro, and mag csv files')
    args = parser.parse_args()

    # Read the CSV file into a DataFrame
    merged_df = process_folder(args.folder_path)

    # Call the displayCube function with the DataFrame
    displayCube(merged_df) 