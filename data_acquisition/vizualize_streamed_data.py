# This script is used to visualize the streamed data from the MetaWear device

# first streams the data from metawear device,

# and uses that stream to calculate the orientation. 

# and then uses that to show the orientation in a py game. 

import sys
import os
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")

from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import yaml
from threading import Event, Thread
from queue import Queue
import numpy as np
from time import sleep
from datetime import datetime
from imusensor.filters.kalman import Kalman

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

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

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

def draw_text(surface, text, position, color=(255, 255, 255)):
    """Draw text on the pygame surface"""
    font = pygame.font.Font(None, 36)
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, position)

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
    
def main():
    # Load configuration
    try:
        # config = load_config('config.yaml')
        config = load_config('/hdd/side_projects/imu_project/form-check/data_acquisition/config.yaml')
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return
    
    # Connect to device
    print("Searching for device...")
    device = None
    try:
        device_mac = config.get('device_mac')
        if not device_mac:
            raise ValueError("No device MAC address in config")
        
        device = MetaWear(device_mac)
        device.connect()
        print(f"Connected to {device.address}")
        print("Waiting for device to stabilize...")
        sleep(2)
        
        # Check if device is properly connected
        if not device.board:
            raise RuntimeError("Device board not initialized")
            
    except Exception as e:
        print(f"Error connecting to device: {str(e)}")
        if device:
            try:
                device.disconnect()
            except:
                pass
        return
    
    # Initialize state
    state = IMUState(device)
    
    try:
        # Initialize PyGame and OpenGL
        print("Initializing PyGame and OpenGL...")
        pygame.init()
        display = (800, 600)
        screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
        
        # Create a separate surface for text
        text_surface = pygame.Surface(display, pygame.SRCALPHA)
        font = pygame.font.Font(None, 36)
        
        # Enable depth testing and face culling
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        
        # Set background color to light gray
        glClearColor(0.8, 0.8, 0.8, 1.0)
        
        # Set up the perspective
        gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
        glTranslatef(0.0, 0.0, -10)
        
        print("PyGame and OpenGL initialized")
        sleep(1)
        
        # Setup sensors
        print("Setting up sensors...")
        setup_sensors(device, state)
        print("Waiting for sensors to stabilize...")
        sleep(2)
        
        print("Starting main loop...")
        # Main visualization loop
        while not state.should_stop:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    state.should_stop = True
                    break
            
            try:
                # Update sensor data
                process_sensor_data(state)
                
                # Clear the screen and depth buffer
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                
                # Reset transformations
                glLoadIdentity()
                glTranslatef(0.0, 0.0, -10)
                
                # Apply rotations
                glRotatef(state.curr_roll, 1, 0, 0)
                glRotatef(state.curr_pitch, 0, 1, 0)
                glRotatef(state.curr_yaw, 0, 0, 1)
                
                # Draw the cube
                draw_cube()
                
                # Update OpenGL display
                pygame.display.flip()
                
                # Clear text surface
                text_surface.fill((0, 0, 0, 0))
                
                # Draw text using PyGame
                y_pos = 10
                for label, value in [("Roll", state.curr_roll), 
                                   ("Pitch", state.curr_pitch), 
                                   ("Yaw", state.curr_yaw)]:
                    text = font.render(f"{label}: {value:.1f}°", True, (0, 0, 0))
                    text_surface.blit(text, (display[0] - 200, y_pos))
                    y_pos += 30
                
                # Blit text surface onto screen
                screen.blit(text_surface, (0, 0))
                pygame.display.flip()
                
            except Exception as e:
                print(f"Error in visualization: {str(e)}")
                continue
            
            pygame.time.wait(10)
    
    except Exception as e:
        print(f"Error in main loop: {str(e)}")
    finally:
        print("Cleaning up...")
        if device:
            try:
                cleanup_sensors(device, state)
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
        pygame.quit()
        print("Cleanup complete")

if __name__ == "__main__":
    main()

