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


    @ReactMethod
    fun disconnectDevice(promise: Promise) {
        try {
            metawearBoard?.disconnectAsync()?.continueWith {
                promise.resolve("Disconnected from MetaWear device")
                null
            }
        } catch (e: Exception) {
            promise.reject("DISCONNECT_FAILED", e)
        }
    }

    @ReactMethod
    fun streamAccelerometer(promise: Promise) {
        if (metawearBoard == null) {
            promise.reject("NO_DEVICE", "Not connected to MetaWear")
            return
        }

        try {
            val accel = metawearBoard!!.getModule(com.mbientlab.metawear.module.Accelerometer::class.java)
            val dataPoints = mutableListOf<String>()

            accel.acceleration().addRouteAsync { source ->
                source.stream { data, _ ->
                    val acc = data.value(com.mbientlab.metawear.data.Acceleration::class.java)
                    val line = "${System.currentTimeMillis()},${acc.x()},${acc.y()},${acc.z()}"
                    dataPoints.add(line)
                }
            }.continueWith {
                accel.acceleration().start()
                accel.start()

                // Stop after 3 seconds
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                    accel.stop()
                    accel.acceleration().stop()

                    val fileName = "accelerometer_${System.currentTimeMillis()}.csv"
                    val file = java.io.File(reactApplicationContext.getExternalFilesDir(null), fileName)
                    file.printWriter().use { out ->
                        out.println("timestamp,x,y,z")
                        dataPoints.forEach { out.println(it) }
                    }

                    promise.resolve("Data written to: ${file.absolutePath}")
                }, 3000)

                null
            }
        } catch (e: Exception) {
            promise.reject("STREAM_FAILED", e)
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
