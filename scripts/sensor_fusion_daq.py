import sys
sys.path.append("/hdd/side_projects/imu_project/form-check")
from src.sensor_utils import SensorFusionStreamer
from src.utils import load_config
from time import sleep
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/sensor_fusion.yaml")
    args = parser.parse_args()
    
    config = load_config(args.config)
    sensor_fusion_streamer = SensorFusionStreamer(config)

    sensor_fusion_streamer.connect()
    sensor_fusion_streamer.configure_sensor()
    
    sensor_fusion_streamer.start_streaming()
    
    sleep(1)    
    
    sensor_fusion_streamer.stop_streaming()
    sensor_fusion_streamer.disconnect()

if __name__ == "__main__":
    main()