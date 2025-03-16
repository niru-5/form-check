# usage: python3 raw_data_logger.py [mac] [config_file]
from __future__ import print_function
import sys
import os
sys.path.append('/home/rpi5/metawear/MetaWear-SDK-Python')
from mbientlab.metawear import MetaWear, libmetawear, parse_value, create_voidp
from mbientlab.metawear.cbindings import *
from time import sleep, strftime
from threading import Event
import yaml

sys.stdout.reconfigure(line_buffering=True)  # Python 3.7+
# OR
os.environ['PYTHONUNBUFFERED'] = '1'  # Alternative approach

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

# Load configuration
if len(sys.argv) > 2:
    config = load_config(sys.argv[2])
else:
    config = load_config('config.yaml')  # Default config file

# Create directory for run
run_name = config.get('run_name', 'default_run')
run_num = config.get('run_num', 1)
run_directory = f"{run_name}_{run_num}"

time_capture_data = config.get('time_capture_data', 10)
time_interval_to_print = config.get('time_interval_to_print', 5)

if not os.path.exists(run_directory):
    os.makedirs(run_directory)

# Connect to device
print("Searching for device...")
device_mac = config.get('device_mac', sys.argv[1])  # Use MAC from config if available, else from command line
d = MetaWear(device_mac)
d.connect()
print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))

# Event setup
e = Event()

# Callback handlers
class DataHandler:
    def __init__(self, sensor_name):
        self.filename = os.path.join(run_directory, f"{sensor_name}-{strftime('%Y%m%d-%H%M%S')}.csv")
        self.file = None
        self.data_handler_fn = FnVoid_VoidP_DataP(lambda ctx, ptr: self.data_handler(ptr))
        
    def data_handler(self, ptr):
        data = parse_value(ptr)
        if self.file is None:
            self.file = open(self.filename, 'w')
            self.file.write("epoch,x,y,z\n")
        self.file.write(f"{ptr.contents.epoch},{data.x},{data.y},{data.z}\n")
        
    def __del__(self):
        if self.file is not None:
            self.file.close()

try:
    print("Configuring device")
    
    # Configure BLE connection
    libmetawear.mbl_mw_settings_set_connection_parameters(d.board, 7.5, 7.5, 0, 6000)
    sleep(3.0)
    
    # Configure sensors based on config file
    acc_config = config.get('accelerometer', {})
    gyro_config = config.get('gyroscope', {})
    mag_config = config.get('magnetometer', {})
    
    handlers = []
    loggers = []
    
    # Accelerometer configuration
    if acc_config.get('enabled', True):
        print(f"Configuring accelerometer: {acc_config['odr']}Hz, ±{acc_config['range']}g")
        libmetawear.mbl_mw_acc_set_odr(d.board, float(acc_config['odr']))
        libmetawear.mbl_mw_acc_set_range(d.board, float(acc_config['range']))
        libmetawear.mbl_mw_acc_write_acceleration_config(d.board)
        
        acc_signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(d.board)
        acc_handler = DataHandler("accelerometer")
        handlers.append(acc_handler)
        acc_logger = create_voidp(lambda fn: libmetawear.mbl_mw_datasignal_log(acc_signal, None, fn))
        loggers.append((acc_logger, acc_handler))
    
    # Gyroscope configuration
    if gyro_config.get('enabled', True):
        print(f"Configuring gyroscope: {gyro_config['odr']}Hz, ±{gyro_config['range']}dps")
        # Map ODR values to enum
        odr_map = {
            800: GyroBoschOdr._800Hz,
            400: GyroBoschOdr._400Hz,
            200: GyroBoschOdr._200Hz,
            100: GyroBoschOdr._100Hz,
            50: GyroBoschOdr._50Hz
        }
        # Map range values to enum
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
        gyro_handler = DataHandler("gyroscope")
        handlers.append(gyro_handler)
        gyro_logger = create_voidp(lambda fn: libmetawear.mbl_mw_datasignal_log(gyro_signal, None, fn))
        loggers.append((gyro_logger, gyro_handler))
    
    # Magnetometer configuration
    if mag_config.get('enabled', True):
        print("Configuring magnetometer with regular preset")
        libmetawear.mbl_mw_mag_bmm150_set_preset(d.board, MagBmm150Preset.REGULAR)
        
        mag_signal = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(d.board)
        mag_handler = DataHandler("magnetometer")
        handlers.append(mag_handler)
        mag_logger = create_voidp(lambda fn: libmetawear.mbl_mw_datasignal_log(mag_signal, None, fn))
        loggers.append((mag_logger, mag_handler))
    
    # Start logging
    libmetawear.mbl_mw_logging_start(d.board, 0)
    
    # Start enabled sensors
    if acc_config.get('enabled', True):
        libmetawear.mbl_mw_acc_enable_acceleration_sampling(d.board)
        libmetawear.mbl_mw_acc_start(d.board)
    
    if gyro_config.get('enabled', True):
        libmetawear.mbl_mw_gyro_bmi270_enable_rotation_sampling(d.board)
        libmetawear.mbl_mw_gyro_bmi270_start(d.board)
    
    if mag_config.get('enabled', True):
        libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(d.board)
        libmetawear.mbl_mw_mag_bmm150_start(d.board)
    
    # Log for specified duration
    print(f"Logging data for {time_capture_data} seconds...")
    for i in range(time_capture_data):
        if i % time_interval_to_print == 0:
            print(f"{i} seconds are done, {time_capture_data - i} seconds to go")
        sleep(1.0)
    
    # Stop enabled sensors
    if acc_config.get('enabled', True):
        libmetawear.mbl_mw_acc_stop(d.board)
        libmetawear.mbl_mw_acc_disable_acceleration_sampling(d.board)
    
    if gyro_config.get('enabled', True):
        libmetawear.mbl_mw_gyro_bmi270_stop(d.board)
        libmetawear.mbl_mw_gyro_bmi270_disable_rotation_sampling(d.board)
    
    if mag_config.get('enabled', True):
        libmetawear.mbl_mw_mag_bmm150_stop(d.board)
        libmetawear.mbl_mw_mag_bmm150_disable_b_field_sampling(d.board)
    
    # Stop logging
    libmetawear.mbl_mw_logging_stop(d.board)
    
    # Setup download handler
    def progress_update_handler(context, entries_left, total_entries):
        if entries_left == 0:
            print("Download completed")
            e.set()
    
    # Download data
    print("Downloading data...")
    progress_handler_fn = FnVoid_VoidP_UInt_UInt(progress_update_handler)
    download_handler = LogDownloadHandler(context=None,
                                        received_progress_update=progress_handler_fn,
                                        received_unknown_entry=cast(None, FnVoid_VoidP_UByte_Long_UByteP_UByte),
                                        received_unhandled_entry=cast(None, FnVoid_VoidP_DataP))
    
    # Subscribe to all active loggers
    for logger, handler in loggers:
        libmetawear.mbl_mw_logger_subscribe(logger, None, handler.data_handler_fn)
    
    libmetawear.mbl_mw_logging_download(d.board, 0, byref(download_handler))
    e.wait()
    
except RuntimeError as err:
    print(err)
finally:
    print("Resetting device")
    e.clear()
    d.on_disconnect = lambda status: e.set()
    libmetawear.mbl_mw_debug_reset(d.board)
    e.wait()