from __future__ import print_function
import sys
import os
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep, strftime
from threading import Event
import yaml

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

class SensorFusionStreamer:
    def __init__(self, device_mac, run_directory):
        self.device = MetaWear(device_mac)
        self.run_directory = run_directory
        self.filename = os.path.join(run_directory, f"sensor_fusion_stream-{strftime('%Y%m%d-%H%M%S')}.csv")
        self.file = None
        self.callback = FnVoid_VoidP_DataP(self.data_handler)
        self.samples = 0

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
        if self.file is None:
            self.file = open(self.filename, 'w')
            
            # TODO: for now checking hasattr. Need to find a better way to do this
            if hasattr(parsed_data, 'w'):
                self.file.write("epoch,w,x,y,z\n")
                self.file.write(f"{data.contents.epoch},{parsed_data.w},{parsed_data.x},{parsed_data.y},{parsed_data.z}\n")
            else:
                self.file.write("epoch,heading,pitch,roll,yaw\n")
                self.file.write(f"{data.contents.epoch},{parsed_data.heading},{parsed_data.pitch},{parsed_data.roll},{parsed_data.yaw}\n")
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

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config = load_config(sys.argv[1])
    else:
        config = load_config('config.yaml')  # Default config file

    device_mac = config.get('device_mac')
    run_name = config.get('run_name', 'default_run')
    run_num = config.get('run_num', 1)
    run_directory = f"{run_name}_{run_num}"

    time_capture_data = config.get('time_capture_data', 10)

    if not os.path.exists(run_directory):
        os.makedirs(run_directory)

    streamer = SensorFusionStreamer(device_mac, run_directory)
    try:
        streamer.connect()
        streamer.configure(config)
        streamer.start_streaming(config)
        print(f"Streaming data for {time_capture_data} seconds...")
        sleep(time_capture_data)
    finally:
        streamer.stop_streaming()
        streamer.disconnect()
        print(f"Total Samples Streamed: {streamer.samples}")
