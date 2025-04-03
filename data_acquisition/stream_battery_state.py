# usage: python3 stream_battery_state.py [mac]
from __future__ import print_function
import sys
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")
from mbientlab.metawear import MetaWear, libmetawear, parse_value, create_voidp, create_voidp_int
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event

import sys

# find by mac
print("Searching for device...")
d = MetaWear(sys.argv[1])

# connect to device
d.connect()
print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
e = Event()

# create callback
callback = FnVoid_VoidP_DataP(lambda ctx, p: print("{epoch: %d, battery: %s}" % (p.contents.epoch, parse_value(p))))

# get battery state signal
print("Configuring device")
signal = libmetawear.mbl_mw_settings_get_battery_state_data_signal(d.board)

# subscribe to battery state signal
libmetawear.mbl_mw_datasignal_subscribe(signal, None, callback)

# create timer - fires every 1000ms
timer = create_voidp(lambda fn: libmetawear.mbl_mw_timer_create_indefinite(d.board, 1000, 0, None, fn), resource = "timer", event = e)
    
# create event based on timer - read battery state when timer fires
libmetawear.mbl_mw_event_record_commands(timer)
libmetawear.mbl_mw_datasignal_read(signal)
create_voidp_int(lambda fn: libmetawear.mbl_mw_event_end_record(timer, None, fn), event = e)

# start timer
libmetawear.mbl_mw_timer_start(timer)

# wait 5s
print("Stream battery state data for 5s")
sleep(5.0)

# remove timer
libmetawear.mbl_mw_timer_remove(timer)
sleep(1.0)

# remove event
libmetawear.mbl_mw_event_remove_all(d.board)
sleep(1.0)

# unsubscribe
libmetawear.mbl_mw_datasignal_unsubscribe(signal)
sleep(2.0)

# disconnect
print("Resetting device")
e = Event()
d.on_disconnect = lambda status: e.set()
libmetawear.mbl_mw_debug_reset(d.board)
e.wait() 