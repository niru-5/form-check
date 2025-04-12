import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import pandas as pd
import argparse
import os
import sys
import os
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")

from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
import yaml
from threading import Event, Thread
from queue import Queue
import numpy as np
from time import sleep, strftime
from datetime import datetime
# from utils import convert_millis_to_datetime
from imusensor.filters.kalman import Kalman
from datetime import datetime

# Define vertices and edges for the cube
# vertices = (
#     (1, -2, -1),  # 0
#     (1, 2, -1),   # 1
#     (-1, 2, -1),  # 2
#     (-1, -2, -1), # 3
#     (1, -2, 1),   # 4
#     (1, 2, 1),    # 5
#     (-1, -2, 1),  # 6
#     (-1, 2, 1)    # 7
# )

# edges = (
#     (0, 1), (0, 3), (0, 4),
#     (2, 1), (2, 3), (2, 7),
#     (6, 3), (6, 4), (6, 7),
#     (5, 1), (5, 4), (5, 7)
# )

# def Cube():
#     glBegin(GL_LINES)
#     for edge in edges:
#         for vertex in edge:
#             glVertex3fv(vertices[vertex])
#     glEnd()
    
# Define vertices and edges for the cube visualization
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

# Define edges for the wireframe
edges = (
    (0, 1), (0, 3), (0, 4),  # Edges from vertex 0
    (2, 1), (2, 3), (2, 7),  # Edges from vertex 2
    (6, 3), (6, 4), (6, 7),  # Edges from vertex 6
    (5, 1), (5, 4), (5, 7)   # Edges from vertex 5
)

# Define the faces of the cube (each face is defined by 4 vertices)
faces = (
    (0, 1, 2, 3),  # Back face
    (4, 5, 6, 7),  # Front face
    (0, 1, 5, 4),  # Right face
    (2, 3, 6, 7),  # Left face
    (1, 2, 7, 5),  # Top face
    (0, 3, 6, 4)   # Bottom face
)

# Define colors for each face (RGBA)
colors = (
    (1, 0, 0, 0.5),  # Red (Back)
    (0, 1, 0, 0.5),  # Green (Front)
    (0, 0, 1, 0.5),  # Blue (Right)
    (1, 1, 0, 0.5),  # Yellow (Left)
    (1, 0, 1, 0.5),  # Magenta (Top)
    (0, 1, 1, 0.5)   # Cyan (Bottom)
)

def draw_cube():
    """Draw the cube using OpenGL with colored faces and black edges"""
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    # Draw filled faces
    glBegin(GL_QUADS)
    for i, face in enumerate(faces):
        glColor4fv(colors[i])  # Set color for this face
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()
    
    # Draw edges in black with thicker lines
    glLineWidth(2.0)
    glColor4f(0, 0, 0, 1.0)  # Black color for edges
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()
    glLineWidth(1.0)  # Reset line width

class IMUState:
    def __init__(self, device):
        self.device = device
        self.acc_queue = Queue()
        self.gyro_queue = Queue()
        self.mag_queue = Queue()
        self.should_stop = False
        
        # Current orientation state
        self.curr_roll = 0
        self.curr_pitch = 0
        self.curr_yaw = 0
        
        # Initialize Kalman filter
        self.kalman_filter = Kalman()
        self.last_update = datetime.now()
        
        # Create handlers
        self.acc_handler = self.create_handler("acc")
        self.gyro_handler = self.create_handler("gyro")
        self.mag_handler = self.create_handler("mag")
        
    def create_handler(self, sensor_type):
        """Create a data handler for the specified sensor type"""
        def data_handler(ctx, ptr):
            data = parse_value(ptr)
            timestamp = datetime.now()
            if sensor_type == "acc":
                self.acc_queue.put((sensor_type, timestamp, data.x, data.y, data.z))
            elif sensor_type == "gyro":
                self.gyro_queue.put((sensor_type, timestamp, data.x, data.y, data.z))
            elif sensor_type == "mag":
                self.mag_queue.put((sensor_type, timestamp, data.x, data.y, data.z))
        return FnVoid_VoidP_DataP(data_handler)

def setup_sensors(device, state):
    """Configure and start the IMU sensors"""
    try:
        print("Configuring device...")
        
        # Configure accelerometer
        print("Configuring accelerometer...")
        libmetawear.mbl_mw_acc_set_odr(device.board, 100.0)  # 100Hz
        print("Set accelerometer ODR")
        libmetawear.mbl_mw_acc_set_range(device.board, 16.0)  # ±16g
        print("Set accelerometer range")
        libmetawear.mbl_mw_acc_write_acceleration_config(device.board)
        print("Wrote accelerometer config")
        
        # Configure gyroscope
        print("Configuring gyroscope...")
        libmetawear.mbl_mw_gyro_bmi270_set_odr(device.board, GyroBoschOdr._100Hz)
        print("Set gyroscope ODR")
        libmetawear.mbl_mw_gyro_bmi270_set_range(device.board, GyroBoschRange._2000dps)
        print("Set gyroscope range")
        libmetawear.mbl_mw_gyro_bmi270_write_config(device.board)
        print("Wrote gyroscope config")
        
        # Configure magnetometer
        print("Configuring magnetometer...")
        libmetawear.mbl_mw_mag_bmm150_set_preset(device.board, MagBmm150Preset.ENHANCED_REGULAR)
        print("Set magnetometer preset")
        
        # Get signals and subscribe
        print("Setting up signal processing...")
        acc_signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(device.board)
        gyro_signal = libmetawear.mbl_mw_gyro_bmi270_get_rotation_data_signal(device.board)
        mag_signal = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(device.board)
        
        libmetawear.mbl_mw_datasignal_subscribe(acc_signal, None, state.acc_handler)
        libmetawear.mbl_mw_datasignal_subscribe(gyro_signal, None, state.gyro_handler)
        libmetawear.mbl_mw_datasignal_subscribe(mag_signal, None, state.mag_handler)
        print("Subscribed to all signals")
        
        # Start streaming
        print("Starting sensor streaming...")
        libmetawear.mbl_mw_acc_enable_acceleration_sampling(device.board)
        libmetawear.mbl_mw_acc_start(device.board)
        print("Started accelerometer")
        
        libmetawear.mbl_mw_gyro_bmi270_enable_rotation_sampling(device.board)
        libmetawear.mbl_mw_gyro_bmi270_start(device.board)
        print("Started gyroscope")
        
        libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(device.board)
        libmetawear.mbl_mw_mag_bmm150_start(device.board)
        print("Started magnetometer")
        
        print("All sensors configured and started successfully")
        
    except Exception as e:
        print(f"Error in setup_sensors: {str(e)}")
        raise

def cleanup_sensors(device, state):
    """Stop sensors and cleanup"""
    # Stop streaming
    libmetawear.mbl_mw_acc_stop(device.board)
    libmetawear.mbl_mw_acc_disable_acceleration_sampling(device.board)
    libmetawear.mbl_mw_gyro_bmi270_stop(device.board)
    libmetawear.mbl_mw_gyro_bmi270_disable_rotation_sampling(device.board)
    libmetawear.mbl_mw_mag_bmm150_stop(device.board)
    libmetawear.mbl_mw_mag_bmm150_disable_b_field_sampling(device.board)
    
    # Reset device
    e = Event()
    device.on_disconnect = lambda status: e.set()
    libmetawear.mbl_mw_debug_reset(device.board)
    e.wait()

def process_sensor_data(state):
    """Process available sensor data and update orientation"""
    acc_data = None
    gyro_data = None
    mag_data = None
    # print("Processing sensor data")
    
    # Get latest data from each sensor
    if not state.acc_queue.empty():
        acc_data = state.acc_queue.get()
    if not state.gyro_queue.empty():
        gyro_data = state.gyro_queue.get()
    if not state.mag_queue.empty():
        mag_data = state.mag_queue.get()
    # print("Sensor data retrieved")
    # Update orientation if we have both accelerometer and gyroscope data
    if acc_data and gyro_data:
        current_time = datetime.now()
        dt = (current_time - state.last_update).total_seconds()
        state.last_update = current_time
        
        # Update Kalman filter with new data
        state.kalman_filter.computeAndUpdateRollPitch(
            acc_data[2],   # x_acc
            acc_data[3],   # y_acc
            acc_data[4],   # z_acc
            gyro_data[2],  # x_gyro
            gyro_data[3],  # y_gyro
            dt
        )
        
        # Get filtered orientation
        state.curr_roll = state.kalman_filter.roll
        state.curr_pitch = state.kalman_filter.pitch
        print(f"Filtered orientation: {state.curr_roll}, {state.curr_pitch}")
        
        # Calculate yaw using magnetometer if available
        if mag_data:
            # Simple yaw calculation - could be improved with proper sensor fusion
            state.curr_yaw = np.arctan2(mag_data[3], mag_data[2]) * 180.0 / np.pi
            print(f"Yaw: {state.curr_yaw}")
    # print("Orientation updated")
 




class SensorFusionStreamer:
    def __init__(self, device_mac, run_directory=None, write_to_file=False):
        self.device = MetaWear(device_mac)
        if not write_to_file:
            self.run_directory = run_directory
            self.filename = os.path.join(run_directory, f"sensor_fusion_stream-{strftime('%Y%m%d-%H%M%S')}.csv")
            self.file = None
        self.callback = FnVoid_VoidP_DataP(self.data_handler)
        self.samples = 0
        self.orientation = Queue()
        self.write_to_file = write_to_file

    def connect(self):
        self.device.connect()
        print("Connected to " + self.device.address + " over " + ("USB" if self.device.usb.is_connected else "BLE"))

    def configure(self, config):
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(self.device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)
        
        # Set sensor fusion mode
        mode = SensorFusionMode.NDOF
        libmetawear.mbl_mw_sensor_fusion_set_mode(self.device.board, mode)
        
        # Set accelerometer and gyroscope ranges
        libmetawear.mbl_mw_sensor_fusion_set_acc_range(self.device.board, SensorFusionAccRange._8G)
        libmetawear.mbl_mw_sensor_fusion_set_gyro_range(self.device.board, SensorFusionGyroRange._2000DPS)
        
        # Write configuration
        libmetawear.mbl_mw_sensor_fusion_write_config(self.device.board)

    def start_streaming(self, config):
        # Determine data type based on config
        data_type = config['sensor_fusion'].get('preset', 'Quaternion').upper()
        if data_type == 'EULER':
            data_signal = SensorFusionData.EULER_ANGLE
        else:
            data_signal = SensorFusionData.QUATERNION
        
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(self.device.board, data_signal)
        libmetawear.mbl_mw_datasignal_subscribe(signal, None, self.callback)
        libmetawear.mbl_mw_sensor_fusion_enable_data(self.device.board, data_signal)
        libmetawear.mbl_mw_sensor_fusion_start(self.device.board)

    def data_handler(self, ctx, data):
        parsed_data = parse_value(data)
        print (parsed_data)
        if self.write_to_file:
            if self.file is None:
                self.file = open(self.filename, 'w')
                
            # TODO: for now checking hasattr. Need to find a better way to do this
            if hasattr(parsed_data, 'w'):
                self.file.write("epoch,w,x,y,z\n")
                self.file.write(f"{data.contents.epoch},{parsed_data.w},{parsed_data.x},{parsed_data.y},{parsed_data.z}\n")
            else:
                self.file.write("epoch,heading,pitch,roll,yaw\n")
                self.file.write(f"{data.contents.epoch},{parsed_data.heading},{parsed_data.pitch},{parsed_data.roll},{parsed_data.yaw}\n")
        else:
            self.orientation.put((parsed_data.heading, parsed_data.roll, parsed_data.pitch, parsed_data.yaw))
        self.samples += 1

    def stop_streaming(self):
        libmetawear.mbl_mw_sensor_fusion_stop(self.device.board)
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(self.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal)

    def disconnect(self):
        libmetawear.mbl_mw_debug_disconnect(self.device.board)

    def __del__(self):
        if self.file is not None:
            self.file.close()
            
    def get_orientation(self):
        _, roll, pitch, yaw = self.orientation.get()
        return roll, pitch, yaw











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
        draw_cube()
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

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def main():
    # Load configuration
    try:
        config = load_config('config.yaml')
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return

    # Connect to device
    # print("Searching for device...")
    # device = None
    # try:
    #     device_mac = config.get('device_mac')
    #     if not device_mac:
    #         raise ValueError("No device MAC address in config")
        
    #     device = MetaWear(device_mac)
    #     device.connect()
    #     print(f"Connected to {device.address}")
    #     print("Waiting for device to stabilize...")
    #     sleep(2)
        
    #     # Check if device is properly connected
    #     if not device.board:
    #         raise RuntimeError("Device board not initialized")
            
    # except Exception as e:
    #     print(f"Error connecting to device: {str(e)}")
    #     if device:
    #         try:
    #             device.disconnect()
    #         except:
    #             pass
    #     return
    
    # # Initialize state
    # state = IMUState(device)
    
    streamer = SensorFusionStreamer(config.get('device_mac'), "", False)
    streamer.connect()
    streamer.configure(config)
    
    streamer.start_streaming(config)
    
    
    
    
    
    
    # setup_sensors(device, state)
    # sleep(2)
    
    pygame.init()
    display = (800, 600)
    # pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -10)
    
    text_surface = pygame.Surface(display, pygame.SRCALPHA)
    font = pygame.font.Font(None, 36)

    curr_roll = 0
    curr_pitch = 90
    curr_yaw = 0
    glRotatef(0 - curr_pitch, 0, 1, 0)
    glRotatef(0 - curr_yaw, 0, 0, 1)
    
    
    curr_time = datetime.now()
    while (datetime.now() - curr_time).total_seconds() < 30:
        roll, pitch, yaw = streamer.get_orientation()
        
        
        glRotatef(roll - curr_roll, 1, 0, 0)
        curr_roll = roll


        glRotatef(pitch - curr_pitch, 0, 1, 0)
        curr_pitch = pitch

        glRotatef(yaw - curr_yaw, 0, 0, 1)
        curr_yaw = yaw

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        draw_cube()
        print(f"Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}")
        
        # y_pos = 10
        # for label, value in [("Roll", state.curr_roll), 
        #                     ("Pitch", state.curr_pitch), 
        #                     ("Yaw", state.curr_yaw)]:
        #     text = font.render(f"{label}: {value:.1f}°", True, (0, 0, 0))
        #     text_surface.blit(text, (display[0] - 200, y_pos))
        #     y_pos += 30
        
        # screen.blit(text_surface, (0, 0))
        pygame.display.flip()
        pygame.time.wait(10)
        
        
        # sleep(0.1)
    # merged_df = process_folder("data/test_18")
    streamer.stop_streaming()
    streamer.disconnect()
    # process_sensor_data(state)
    
    # displayCube(merged_df)
    
    
    
    pygame.quit()
    # cleanup_sensors(device, state)
    
    
    
    



if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='Display a rotating cube using roll and pitch from a CSV file.')
    # parser.add_argument('--folder-path', type=str, help='Path to the folder containing acc, gyro, and mag csv files')
    # args = parser.parse_args()

    # # Read the CSV file into a DataFrame
    # merged_df = process_folder(args.folder_path)

    # # Call the displayCube function with the DataFrame
    # displayCube(merged_df) 
    main()