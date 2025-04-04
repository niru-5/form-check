# use the config file to connect to the device. 
# configure it as mentioned in the config file. 
# stream the data and write that data to a csv file. 

import sys
import os
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")

from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep, strftime
from threading import Event
import yaml

# Load configuration from a YAML file
def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

class State:
    def __init__(self, device, run_directory):
        self.device = device
        self.samples = 0
        self.run_directory = run_directory
        self.acc_handler = self.create_data_handler("accelerometer")
        self.gyro_handler = self.create_data_handler("gyroscope")
        self.mag_handler = self.create_data_handler("magnetometer")
        
    def create_data_handler(self, sensor_name):
        filename = os.path.join(self.run_directory, f"{sensor_name}-{strftime('%Y%m%d-%H%M%S')}.csv")
        file = open(filename, 'w')
        file.write("epoch,x,y,z\n")
        return FnVoid_VoidP_DataP(lambda ctx, ptr: self.data_handler(ptr, file))
    
    def data_handler(self, ptr, file):
        data = parse_value(ptr)
        file.write(f"{ptr.contents.epoch},{data.x},{data.y},{data.z}\n")
        self.samples += 1

def main():
    # Load configuration
    config = load_config('config.yaml')  # Default config file

    # Create directory for run
    run_name = config.get('run_name', 'default_run')
    run_num = config.get('run_num', 1)
    run_directory = f"{run_name}_{run_num}"
    data_acquisition_mode = config.get('data_acquisition_mode', 'logger')
    sensor_mode = config.get('sensor_mode', 'raw_data')

    if not os.path.exists(run_directory):
        os.makedirs(run_directory)

    # Connect to device
    print("Searching for device...")
    device_mac = config.get('device_mac')  # Use MAC from config
    d = MetaWear(device_mac)
    d.connect()
    print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))

    state = State(d, run_directory, sensor_mode)
    e = Event()  # Reintroduce the Event object

    try:
        print("Configuring device")
        
        # Configure BLE connection
        libmetawear.mbl_mw_settings_set_connection_parameters(d.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)
        
        # Configure sensors based on config file
        acc_config = config.get('accelerometer', {})
        gyro_config = config.get('gyroscope', {})
        mag_config = config.get('magnetometer', {})
        
        # Accelerometer configuration
        if acc_config.get('enabled', True):
            print(f"Configuring accelerometer: {acc_config['odr']}Hz, ±{acc_config['range']}g")
            libmetawear.mbl_mw_acc_set_odr(d.board, float(acc_config['odr']))
            libmetawear.mbl_mw_acc_set_range(d.board, float(acc_config['range']))
            libmetawear.mbl_mw_acc_write_acceleration_config(d.board)
            
            acc_signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(d.board)
            libmetawear.mbl_mw_datasignal_subscribe(acc_signal, None, state.acc_handler)
        
        # Gyroscope configuration
        if gyro_config.get('enabled', True):
            print(f"Configuring gyroscope: {gyro_config['odr']}Hz, ±{gyro_config['range']}dps")
            odr_map = {
                800: GyroBoschOdr._800Hz,
                400: GyroBoschOdr._400Hz,
                200: GyroBoschOdr._200Hz,
                100: GyroBoschOdr._100Hz,
                50: GyroBoschOdr._50Hz
            }
            range_map = {
                2000: GyroBoschRange._2000dps,
                1000: GyroBoschRange._1000dps,
                500: GyroBoschRange._500dps,
                250: GyroBoschRange._250dps,
                125: GyroBoschRange._125dps
            }
            
            libmetawear.mbl_mw_gyro_bmi270_set_odr(d.board, odr_map[gyro_config['odr']])
            libmetawear.mbl_mw_gyro_bmi270_set_range(d.board, range_map[gyro_config['range']])
            libmetawear.mbl_mw_gyro_bmi270_write_config(d.board)
            
            gyro_signal = libmetawear.mbl_mw_gyro_bmi270_get_rotation_data_signal(d.board)
            libmetawear.mbl_mw_datasignal_subscribe(gyro_signal, None, state.gyro_handler)
        
        # Magnetometer configuration
        if mag_config.get('enabled', True):
            print("Configuring magnetometer with regular preset")
            libmetawear.mbl_mw_mag_bmm150_set_preset(d.board, MagBmm150Preset.REGULAR)
            
            mag_signal = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(d.board)
            libmetawear.mbl_mw_datasignal_subscribe(mag_signal, None, state.mag_handler)
        
        # Start streaming
        if acc_config.get('enabled', True):
            libmetawear.mbl_mw_acc_enable_acceleration_sampling(d.board)
            libmetawear.mbl_mw_acc_start(d.board)
        
        if gyro_config.get('enabled', True):
            libmetawear.mbl_mw_gyro_bmi270_enable_rotation_sampling(d.board)
            libmetawear.mbl_mw_gyro_bmi270_start(d.board)
        
        if mag_config.get('enabled', True):
            libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(d.board)
            libmetawear.mbl_mw_mag_bmm150_start(d.board)
        
        # Stream for a specified duration
        time_capture_data = config.get('time_capture_data', 10)
        print(f"Streaming data for {time_capture_data} seconds...")
        sleep(time_capture_data)
        
        # Stop streaming
        if acc_config.get('enabled', True):
            libmetawear.mbl_mw_acc_stop(d.board)
            libmetawear.mbl_mw_acc_disable_acceleration_sampling(d.board)
        
        if gyro_config.get('enabled', True):
            libmetawear.mbl_mw_gyro_bmi270_stop(d.board)
            libmetawear.mbl_mw_gyro_bmi270_disable_rotation_sampling(d.board)
        
        if mag_config.get('enabled', True):
            libmetawear.mbl_mw_mag_bmm150_stop(d.board)
            libmetawear.mbl_mw_mag_bmm150_disable_b_field_sampling(d.board)
        
        # Unsubscribe from signals
        libmetawear.mbl_mw_datasignal_unsubscribe(acc_signal)
        libmetawear.mbl_mw_datasignal_unsubscribe(gyro_signal)
        libmetawear.mbl_mw_datasignal_unsubscribe(mag_signal)
        
    except RuntimeError as err:
        print(err)
    finally:
        print("Resetting device")
        d.on_disconnect = lambda status: e.set()
        libmetawear.mbl_mw_debug_reset(d.board)
        e.wait()

if __name__ == "__main__":
    main()


