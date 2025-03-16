# usage: python3 reset_device.py [mac]
from __future__ import print_function
import sys
sys.path.append('/home/rpi5/metawear/MetaWear-SDK-Python')
from mbientlab.metawear import MetaWear, libmetawear
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event

# Connect to device
print("Searching for device...")
d = MetaWear(sys.argv[1])
d.connect()
print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))

e = Event()

try:
    # Simple reset - just restarts the device
    def simple_reset():
        print("Performing simple reset...")
        d.on_disconnect = lambda status: e.set()
        libmetawear.mbl_mw_debug_reset(d.board)
        e.wait()
        
    # Full reset - clears all configurations and data
    def full_reset():
        print("Performing full reset...")
        
        # Stop logging if active
        libmetawear.mbl_mw_logging_stop(d.board)
        sleep(1.0)
        
        # Flush log if needed
        libmetawear.mbl_mw_logging_flush_page(d.board)
        sleep(1.0)
        
        # Clear log entries
        libmetawear.mbl_mw_logging_clear_entries(d.board)
        sleep(1.0)
        
        # Remove all event handlers
        libmetawear.mbl_mw_event_remove_all(d.board)
        sleep(1.0)
        
        # Clear all macros
        libmetawear.mbl_mw_macro_erase_all(d.board)
        sleep(1.0)
        
        # Reset and garbage collect
        libmetawear.mbl_mw_debug_reset_after_gc(d.board)
        sleep(1.0)
        
        # Disconnect
        d.on_disconnect = lambda status: e.set()
        libmetawear.mbl_mw_debug_disconnect(d.board)
        e.wait()

    # Choose which reset to perform
    full_reset()  # Uncomment this for full reset
    # simple_reset()  # Comment this out if using full reset
    
except RuntimeError as err:
    print(err)
finally:
    print("Reset completed")
    sleep(1.0) 