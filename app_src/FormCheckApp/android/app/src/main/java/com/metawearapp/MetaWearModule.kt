package com.metawearapp

import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.*
import android.os.IBinder
import com.facebook.react.bridge.*
import com.mbientlab.metawear.MetaWearBoard
import com.mbientlab.metawear.android.BtleService
import com.mbientlab.metawear.data.Acceleration
import com.mbientlab.metawear.data.AngularVelocity
import com.mbientlab.metawear.data.MagneticField
import com.mbientlab.metawear.module.AccelerometerBmi270
import com.mbientlab.metawear.module.GyroBmi270
import com.mbientlab.metawear.module.MagnetometerBmm150
import com.mbientlab.metawear.module.Gyro
import java.io.File

class MetaWearModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext), ServiceConnection {
    private var serviceBinder: BtleService.LocalBinder? = null
    private var metawearBoard: MetaWearBoard? = null
    private var accel: AccelerometerBmi270? = null
    private var gyro: GyroBmi270? = null
    private var mag: MagnetometerBmm150? = null
    private var accelDataPoints = mutableListOf<String>()
    private var gyroDataPoints = mutableListOf<String>()
    private var magDataPoints = mutableListOf<String>()
    private var currentFolder: File? = null

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
    fun startStream(config: ReadableMap, promise: Promise) {
        if (metawearBoard == null) {
            promise.reject("NO_DEVICE", "Not connected to MetaWear")
            return
        }

        try {
            // Reset data points
            accelDataPoints.clear()
            gyroDataPoints.clear()
            magDataPoints.clear()

            // Create timestamp folder
            val timestamp = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy_MM_dd_HH_mm_ss"))
            currentFolder = java.io.File(reactApplicationContext.getExternalFilesDir(null), timestamp)
            currentFolder?.mkdir()

            // Get sensor modules with correct types
            accel = metawearBoard!!.getModule(AccelerometerBmi270::class.java)
            gyro = metawearBoard!!.getModule(GyroBmi270::class.java)
            mag = metawearBoard!!.getModule(MagnetometerBmm150::class.java)

            // Configure and start accelerometer BMI270
            accel?.configure()
                ?.odr(config.getDouble("accel").toFloat())  // Set ODR from config
                ?.commit()
            accel?.acceleration()?.addRouteAsync { source ->
                source.stream { data, _ ->
                    val acc = data.value(Acceleration::class.java)
                    val line = "${System.currentTimeMillis()},${acc.x()},${acc.y()},${acc.z()}"
                    accelDataPoints.add(line)
                }
            }?.continueWith {
                accel?.acceleration()?.start()
                accel?.start()
            }

            // Configure and start gyroscope BMI270
            val gyroOdr = when (config.getDouble("gyro").toFloat()) {
                25f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_25_HZ
                50f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_50_HZ
                100f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_100_HZ
                200f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_200_HZ
                400f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_400_HZ
                800f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_800_HZ
                1600f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_1600_HZ
                3200f -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_3200_HZ
                else -> com.mbientlab.metawear.module.Gyro.OutputDataRate.ODR_100_HZ  // default
            }

            gyro?.configure()
                ?.odr(gyroOdr)
                ?.range(com.mbientlab.metawear.module.Gyro.Range.FSR_2000)  // ±2000 degrees per second
                ?.filter(com.mbientlab.metawear.module.Gyro.FilterMode.NORMAL)
                ?.commit()
            gyro?.angularVelocity()?.addRouteAsync { source ->
                source.stream { data, _ ->
                    val angular = data.value(AngularVelocity::class.java)
                    val line = "${System.currentTimeMillis()},${angular.x()},${angular.y()},${angular.z()}"
                    gyroDataPoints.add(line)
                }
            }?.continueWith {
                gyro?.angularVelocity()?.start()
                gyro?.start()
            }

            // Configure and start magnetometer BMM150
            val magOdr = when (config.getDouble("mag").toFloat()) {
                2f -> MagnetometerBmm150.OutputDataRate.ODR_2_HZ
                6f -> MagnetometerBmm150.OutputDataRate.ODR_6_HZ
                8f -> MagnetometerBmm150.OutputDataRate.ODR_8_HZ
                10f -> MagnetometerBmm150.OutputDataRate.ODR_10_HZ
                15f -> MagnetometerBmm150.OutputDataRate.ODR_15_HZ
                20f -> MagnetometerBmm150.OutputDataRate.ODR_20_HZ
                25f -> MagnetometerBmm150.OutputDataRate.ODR_25_HZ
                30f -> MagnetometerBmm150.OutputDataRate.ODR_30_HZ
                else -> MagnetometerBmm150.OutputDataRate.ODR_10_HZ  // default
            }

            mag?.usePreset(MagnetometerBmm150.Preset.HIGH_ACCURACY)  // Using HIGH_ACCURACY preset for best results
            mag?.configure()
                ?.outputDataRate(magOdr)  // Use proper enum instead of float
                ?.commit()
            mag?.magneticField()?.addRouteAsync { source ->
                source.stream { data, _ ->
                    val magnetic = data.value(MagneticField::class.java)
                    val line = "${System.currentTimeMillis()},${magnetic.x()},${magnetic.y()},${magnetic.z()}"
                    magDataPoints.add(line)
                }
            }?.continueWith {
                mag?.magneticField()?.start()
                mag?.start()
            }

            promise.resolve("Started streaming to folder: ${currentFolder?.absolutePath}")

        } catch (e: Exception) {
            promise.reject("STREAM_FAILED", e)
        }
    }

    @ReactMethod
    fun stopStream(promise: Promise) {
        try {
            // Stop all sensors
            accel?.let {
                it.stop()
                it.acceleration().stop()
            }
            gyro?.let {
                it.stop()
                it.angularVelocity().stop()
            }
            mag?.let {
                it.stop()
                it.magneticField().stop()
            }

            // Save accelerometer data
            currentFolder?.let { folder ->
                val accelFile = java.io.File(folder, "accelerometer.csv")
                accelFile.printWriter().use { out ->
                    out.println("timestamp,x,y,z")
                    accelDataPoints.forEach { out.println(it) }
                }

                // Save gyroscope data
                val gyroFile = java.io.File(folder, "gyroscope.csv")
                gyroFile.printWriter().use { out ->
                    out.println("timestamp,x,y,z")
                    gyroDataPoints.forEach { out.println(it) }
                }

                // Save magnetometer data
                val magFile = java.io.File(folder, "magnetometer.csv")
                magFile.printWriter().use { out ->
                    out.println("timestamp,x,y,z")
                    magDataPoints.forEach { out.println(it) }
                }

                promise.resolve("Data saved to folder: ${folder.absolutePath}")
            } ?: promise.reject("SAVE_FAILED", "No current folder found")

        } catch (e: Exception) {
            promise.reject("STOP_STREAM_FAILED", e)
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
