# usage: python3 imu_logger.py [mac]
from __future__ import print_function
import sys
# sys.path.append('/home/rpi5/metawear/MetaWear-SDK-Python')
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")
from mbientlab.metawear import MetaWear, libmetawear, parse_value, create_voidp, SensorFusionMode, SensorFusionData
from mbientlab.metawear.cbindings import *
from time import sleep, strftime
from threading import Event

import sys

# Connect to device
print("Searching for device...")
d = MetaWear(sys.argv[1])
sleep(2)
d.connect()
print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))

# Event setup
e = Event()

# Callback handlers
class DataHandler:
    def __init__(self, sensor_name, columns=None):
        self.filename = f"{sensor_name}-{strftime('%Y%m%d-%H%M%S')}.csv"
        self.file = None
        self.columns = columns if columns else ["epoch", "x", "y", "z"]
        self.data_handler_fn = FnVoid_VoidP_DataP(lambda ctx, ptr: self.data_handler(ptr))
        
    def data_handler(self, ptr):
        data = parse_value(ptr)
        if self.file is None:
            self.file = open(self.filename, 'w')
            self.file.write(",".join(self.columns) + "\n")
            
        if "w" in self.columns:  # Quaternion data
            self.file.write(f"{ptr.contents.epoch},{data.w},{data.x},{data.y},{data.z}\n")
        elif "pitch" in self.columns:  # Euler angles
            self.file.write(f"{ptr.contents.epoch},{data.pitch},{data.roll},{data.yaw}\n")
        else:  # Regular XYZ data
            self.file.write(f"{ptr.contents.epoch},{data.x},{data.y},{data.z}\n")
        
    def __del__(self):
        if self.file is not None:
            self.file.close()

try:
    print("Configuring device")
    
    # Configure BLE connection
    libmetawear.mbl_mw_settings_set_connection_parameters(d.board, 7.5, 7.5, 0, 6000)
    sleep(1.0)
    
    # Configure sensors first
    # Accelerometer config (BMI270)
    libmetawear.mbl_mw_acc_set_odr(d.board, 800.0)
    libmetawear.mbl_mw_acc_set_range(d.board, 16.0)
    libmetawear.mbl_mw_acc_write_acceleration_config(d.board)
    
    # Gyroscope config (BMI270)
    libmetawear.mbl_mw_gyro_bmi270_set_range(d.board, GyroBoschRange._2000dps)
    libmetawear.mbl_mw_gyro_bmi270_set_odr(d.board, GyroBoschOdr._800Hz)
    libmetawear.mbl_mw_gyro_bmi270_write_config(d.board)
    
    # Magnetometer config (BMM150)
    libmetawear.mbl_mw_mag_bmm150_set_preset(d.board, MagBmm150Preset.REGULAR)
    
    # Configure sensor fusion first
    print("Configuring sensor fusion...")
    libmetawear.mbl_mw_sensor_fusion_set_mode(d.board, SensorFusionMode.NDOF)
    libmetawear.mbl_mw_sensor_fusion_set_acc_range(d.board, SensorFusionAccRange._8G)
    libmetawear.mbl_mw_sensor_fusion_set_gyro_range(d.board, SensorFusionGyroRange._2000DPS)
    libmetawear.mbl_mw_sensor_fusion_write_config(d.board)
    sleep(1.0)  # Give time for config to be written

    # Enable sensor fusion data channels before getting signals
    libmetawear.mbl_mw_sensor_fusion_enable_data(d.board, SensorFusionData.EULER_ANGLE)
    libmetawear.mbl_mw_sensor_fusion_enable_data(d.board, SensorFusionData.QUATERNION)
    sleep(0.5)  # Give time for channels to be enabled

    # Get all signals
    acc_signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(d.board)
    gyro_signal = libmetawear.mbl_mw_gyro_bmi270_get_rotation_data_signal(d.board)
    mag_signal = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(d.board)
    euler_signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(d.board, SensorFusionData.EULER_ANGLE)
    quat_signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(d.board, SensorFusionData.QUATERNION)
    
    # Setup data handlers
    acc_handler = DataHandler("accelerometer")
    gyro_handler = DataHandler("gyroscope")
    mag_handler = DataHandler("magnetometer")
    euler_handler = DataHandler("euler", ["epoch", "pitch", "roll", "yaw"])
    quat_handler = DataHandler("quaternion", ["epoch", "w", "x", "y", "z"])
    
    # Setup loggers with proper error handling
    def create_logger(signal, name):
        logger = create_voidp(
            lambda fn: libmetawear.mbl_mw_datasignal_log(signal, None, fn),
            resource=name
        )
        sleep(0.1)  # Give time between logger creation
        return logger

    # Create loggers
    acc_logger = create_logger(acc_signal, "acc_logger")
    gyro_logger = create_logger(gyro_signal, "gyro_logger")
    mag_logger = create_logger(mag_signal, "mag_logger")
    euler_logger = create_logger(euler_signal, "euler_logger")
    quat_logger = create_logger(quat_signal, "quat_logger")
    
    # Start logging
    libmetawear.mbl_mw_logging_start(d.board, 0)
    
    # Start all sensors
    libmetawear.mbl_mw_acc_enable_acceleration_sampling(d.board)
    libmetawear.mbl_mw_acc_start(d.board)
    
    libmetawear.mbl_mw_gyro_bmi270_enable_rotation_sampling(d.board)
    libmetawear.mbl_mw_gyro_bmi270_start(d.board)
    
    libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(d.board)
    libmetawear.mbl_mw_mag_bmm150_start(d.board)
    
    # Start sensor fusion last
    libmetawear.mbl_mw_sensor_fusion_start(d.board)
    
    # Log for 2 minutes
    print("Logging data for 10 seconds...")
    sleep(10.0)
    
    # Stop sensors
    libmetawear.mbl_mw_acc_stop(d.board)
    libmetawear.mbl_mw_acc_disable_acceleration_sampling(d.board)
    
    libmetawear.mbl_mw_gyro_bmi270_stop(d.board)
    libmetawear.mbl_mw_gyro_bmi270_disable_rotation_sampling(d.board)
    
    libmetawear.mbl_mw_mag_bmm150_stop(d.board)
    libmetawear.mbl_mw_mag_bmm150_disable_b_field_sampling(d.board)
    
    # Stop sensor fusion
    libmetawear.mbl_mw_sensor_fusion_stop(d.board)
    
    # Stop logging
    libmetawear.mbl_mw_logging_stop(d.board)
    
    # Setup download handler
    def download_handler(ctx, pointer):
        print("Download completed")
        e.set()
        
    download_handler_fn = FnVoid_VoidP_DataP(download_handler)
    
    # Setup progress handler
    def progress_update_handler(context, entries_left, total_entries):
        if entries_left == 0:
            print("Download completed")
            e.set()
            
    handlers = []
    
    # Subscribe to loggers
    libmetawear.mbl_mw_logger_subscribe(acc_logger, None, acc_handler.data_handler_fn)
    libmetawear.mbl_mw_logger_subscribe(gyro_logger, None, gyro_handler.data_handler_fn)
    libmetawear.mbl_mw_logger_subscribe(mag_logger, None, mag_handler.data_handler_fn)
    libmetawear.mbl_mw_logger_subscribe(euler_logger, None, euler_handler.data_handler_fn)
    libmetawear.mbl_mw_logger_subscribe(quat_logger, None, quat_handler.data_handler_fn)
    
    # Download data
    print("Downloading data...")
    progress_handler_fn = FnVoid_VoidP_UInt_UInt(progress_update_handler)
    download_handler = LogDownloadHandler(context=None,
                                        received_progress_update=progress_handler_fn,
                                        received_unknown_entry=cast(None, FnVoid_VoidP_UByte_Long_UByteP_UByte),
                                        received_unhandled_entry=cast(None, FnVoid_VoidP_DataP))
    
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