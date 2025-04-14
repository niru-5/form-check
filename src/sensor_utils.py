from __future__ import print_function
import sys
import os
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep, strftime
from threading import Event
import yaml
from collections import deque


# multiple usecases of this class
# 1. sensor fusion data logger to a file 
# 2. sensor fusion data streamer to a file
# 3. sesnor fusion data to a queue of a certain length.






class SensorFusionStreamer:
    def __init__(self, device_mac):
        self.device = MetaWear(device_mac)

    def __init__(self, config):
        self.config = config
        self.device = MetaWear(config['device_mac'])
        
        self.sensor_settings = config['sensor_settings']
        
        self.data_acquisition_type = config['data_acquisition_type']
        
        # get the run directory, if it does not exist, then set it to ""
        if self.data_acquisition_type == "logger_to_file" or self.data_acquisition_type == "stream_to_file":
            self.run_directory = config.get('run_directory', "")
            self.run_name = config.get('run_name', "")
            os.makedirs(os.path.join(self.run_directory, self.run_name), exist_ok=True)
            print (os.path.join(self.run_directory, self.run_name))
            self.file_name = os.path.join(self.run_directory, self.run_name, f"{self.run_name}-sensor_fusion_stream-{strftime('%Y%m%d-%H%M%S')}.csv") 
        elif self.data_acquisition_type == "write_to_queue":
            self.data_queue = deque(maxlen=config.get('data_queue_length', 50))
        else:
            raise ValueError("Invalid data acquisition type")
        
        
        self.callback = FnVoid_VoidP_DataP(self.data_handler)
        self.samples = 0
        
    def configure_sensor(self):
        # needs to be done after the connecting to the device
        
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(self.device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)
        
        # set the accelerometer range first
        if self.sensor_settings['accel_range'] == 16:
            libmetawear.mbl_mw_sensor_fusion_set_acc_range(self.device.board, SensorFusionAccRange._16G)
        elif self.sensor_settings['accel_range'] == 8:
            libmetawear.mbl_mw_sensor_fusion_set_acc_range(self.device.board, SensorFusionAccRange._8G)
            
        # set the gyroscope range
        if self.sensor_settings['gyro_range'] == 2000:
            libmetawear.mbl_mw_sensor_fusion_set_gyro_range(self.device.board, SensorFusionGyroRange._2000DPS)
        elif self.sensor_settings['gyro_range'] == 1000:
            libmetawear.mbl_mw_sensor_fusion_set_gyro_range(self.device.board, SensorFusionGyroRange._1000DPS)
            
        # set the data type
        self.sensor_data_type = self.sensor_settings['data_type']
        
        # TODO: hardcoded for now
        mode = SensorFusionMode.NDOF
        libmetawear.mbl_mw_sensor_fusion_set_mode(self.device.board, mode)
        libmetawear.mbl_mw_sensor_fusion_write_config(self.device.board)

    def connect(self):
        self.device.connect()
        print("Connected to " + self.device.address + " over " + ("USB" if self.device.usb.is_connected else "BLE"))

    def start_streaming(self):
        # Determine data type based on config
        data_type = self.sensor_data_type.upper()
        if data_type == 'EULER':
            self.data_signal = SensorFusionData.EULER_ANGLE
        else:
            self.data_signal = SensorFusionData.QUATERNION
        
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(self.device.board, self.data_signal)
        libmetawear.mbl_mw_datasignal_subscribe(signal, None, self.callback)
        libmetawear.mbl_mw_sensor_fusion_enable_data(self.device.board, self.data_signal)
        libmetawear.mbl_mw_sensor_fusion_start(self.device.board)

    def data_handler(self, ctx, data):
        parsed_data = parse_value(data)
        print (parsed_data)
        if self.file_name is not None:
            self.file = open(self.file_name, 'w')
            
            # TODO: for now checking hasattr. Need to find a better way to do this
            if hasattr(parsed_data, 'w'):
                self.file.write("epoch,w,x,y,z\n")
                self.file.write(f"{data.contents.epoch},{parsed_data.w},{parsed_data.x},{parsed_data.y},{parsed_data.z}\n")
            else:
                self.file.write("epoch,heading,pitch,roll,yaw\n")
                self.file.write(f"{data.contents.epoch},{parsed_data.heading},{parsed_data.pitch},{parsed_data.roll},{parsed_data.yaw}\n")
        else:
            if hasattr(parsed_data, 'w'):
                self.data_queue.append((parsed_data.w, parsed_data.x, parsed_data.y, parsed_data.z))
            else:
                self.data_queue.append((parsed_data.heading, parsed_data.pitch, parsed_data.roll, parsed_data.yaw))
        self.samples += 1
        

    def stop_streaming(self):
        libmetawear.mbl_mw_sensor_fusion_stop(self.device.board)
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(self.device.board, self.data_signal)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal)

    def disconnect(self):
        libmetawear.mbl_mw_debug_disconnect(self.device.board)

    def __del__(self):
        if self.file is not None:
            self.file.close()