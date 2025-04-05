package com.metawearapp

import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.*
import android.os.IBinder
import com.facebook.react.bridge.*
import com.mbientlab.metawear.MetaWearBoard
import com.mbientlab.metawear.android.BtleService

class MetaWearModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext), ServiceConnection {
    private var serviceBinder: BtleService.LocalBinder? = null
    private var metawearBoard: MetaWearBoard? = null

    init {
        val intent = Intent(reactApplicationContext, BtleService::class.java)
        reactApplicationContext.bindService(intent, this, Context.BIND_AUTO_CREATE)
    }

    override fun getName(): String {
        return "MetaWearModule"
    }

    @ReactMethod
    fun connectToDevice(macAddress: String, promise: Promise) {
        val btManager = reactApplicationContext.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val btDevice: BluetoothDevice = btManager.adapter.getRemoteDevice(macAddress)

        if (serviceBinder == null) {
            promise.reject("SERVICE_NOT_BOUND", "BtleService is not bound")
            return
        }

        metawearBoard = serviceBinder?.getMetaWearBoard(btDevice)
        metawearBoard?.connectAsync()?.continueWith { task ->
            if (task.isFaulted) {
                promise.reject("CONNECTION_FAILED", task.error)
            } else {
                promise.resolve("Connected to $macAddress")
            }
            null
        }
    }

    override fun onServiceConnected(name: ComponentName?, service: IBinder?) {
        serviceBinder = service as? BtleService.LocalBinder
    }

    override fun onServiceDisconnected(name: ComponentName?) {
        serviceBinder = null
    }

    override fun initialize() {
        super.initialize()
        val intent = Intent(reactApplicationContext, BtleService::class.java)
        reactApplicationContext.bindService(intent, this, Context.BIND_AUTO_CREATE)
    }

    override fun onCatalystInstanceDestroy() {
        super.onCatalystInstanceDestroy()
        reactApplicationContext.unbindService(this)
    }
}
