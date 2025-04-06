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
import com.mbientlab.metawear.module.Accelerometer
import com.mbientlab.metawear.module.Gyro
import java.io.File
import android.util.Log

class MetaWearModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext), ServiceConnection {
    private var serviceBinder: BtleService.LocalBinder? = null
    private var metawearBoard: MetaWearBoard? = null
    private var accel: Accelerometer? = null
    private var gyro: GyroBmi270? = null
    private var mag: MagnetometerBmm150? = null
    private var currentFolder: File? = null
    private var accelWriter: java.io.PrintWriter? = null
    private var gyroWriter: java.io.PrintWriter? = null
    private var magWriter: java.io.PrintWriter? = null

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
        println("METAWEAR_DEBUG: Starting stream")
        System.out.println("METAWEAR_DEBUG: Starting stream with config: ${config.toString()}")
        Log.d("METAWEAR_DEBUG", "Starting stream with config: ${config.toString()}")
        
        if (metawearBoard == null) {
            println("METAWEAR_DEBUG: Board is null!")
            promise.reject("NO_DEVICE", "Not connected to MetaWear")
            return
        }

        println("METAWEAR_DEBUG: Board connection state: ${metawearBoard?.isConnected}")
        
        try {

            // Create timestamp folder
            val timestamp = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy_MM_dd_HH_mm_ss"))
            currentFolder = java.io.File(reactApplicationContext.getExternalFilesDir(null), timestamp)
            currentFolder?.mkdir()

            // Set up files and writers
            currentFolder?.let { folder ->
                val accelFile = java.io.File(folder, "accelerometer.csv")
                val gyroFile = java.io.File(folder, "gyroscope.csv")
                val magFile = java.io.File(folder, "magnetometer.csv")

                accelWriter = accelFile.printWriter().apply { println("timestamp,x,y,z") }
                gyroWriter = gyroFile.printWriter().apply { println("timestamp,x,y,z") }
                magWriter = magFile.printWriter().apply { println("timestamp,x,y,z") }
            }

            // Get sensor modules with correct types
            println("METAWEAR_DEBUG: Attempting to get accelerometer module")
            accel = metawearBoard!!.getModule(com.mbientlab.metawear.module.Accelerometer::class.java)
            println("METAWEAR_DEBUG: Accelerometer module obtained: ${accel != null}")

            gyro = metawearBoard!!.getModule(com.mbientlab.metawear.module.GyroBmi270::class.java)
            mag = metawearBoard!!.getModule(com.mbientlab.metawear.module.MagnetometerBmm150::class.java)
            

            // Configure accelerometer
            println("METAWEAR_DEBUG: Configuring accelerometer")
            val accelOdr = when (config.getDouble("accel").toFloat()) {
                0.78125f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_0_78125_HZ
                1.5625f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_1_5625_HZ
                3.125f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_3_125_HZ
                6.25f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_6_25_HZ
                12.5f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_12_5_HZ
                25f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_25_HZ
                50f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_50_HZ
                100f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_100_HZ
                200f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_200_HZ
                400f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_400_HZ
                800f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_800_HZ
                1600f -> com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_1600_HZ
                else -> {
                    println("METAWEAR_DEBUG: Using default ODR for accel: 100Hz")
                    com.mbientlab.metawear.module.AccelerometerBmi270.OutputDataRate.ODR_100_HZ
                }
            }
            
            println("METAWEAR_DEBUG: Configuring accelerometer with ODR: $accelOdr")

            accel?.configure()
                ?.odr(config.getDouble("accel").toFloat())
                ?.range(16.0.toFloat())
                // ?.filter(com.mbientlab.metawear.module.AccelerometerBmi270.FilterMode.NORMAL)
                ?.commit()

            println("METAWEAR_DEBUG: Setting up accelerometer route")
            
            

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
            

            // Configure and start magnetometer BMM150
            val magOdr = when (config.getDouble("mag").toFloat()) {
                2f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_2_HZ
                6f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_6_HZ
                8f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_8_HZ
                10f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_10_HZ
                15f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_15_HZ
                20f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_20_HZ
                25f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_25_HZ
                30f -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_30_HZ
                else -> com.mbientlab.metawear.module.MagnetometerBmm150.OutputDataRate.ODR_25_HZ  // default
            }

            mag?.usePreset(com.mbientlab.metawear.module.MagnetometerBmm150.Preset.ENHANCED_REGULAR)  // Using HIGH_ACCURACY preset for best results
            mag?.configure()
                ?.outputDataRate(magOdr)  // Use proper enum instead of float
                ?.commit()


            
            // accel?.acceleration()?.addRouteAsync { source ->
            //     source.stream { data, _ ->
            //         val acc = data.value(Acceleration::class.java)
            //         val line = "${System.currentTimeMillis()},${acc.x()},${acc.y()},${acc.z()}"
            //         accelDataPoints.add(line)
            //         println("METAWEAR_DEBUG: Accelerometer data: $line")
            //     }
            // }?.continueWith { 
            //     accel?.acceleration()?.start()
            //     accel?.start()
            // }
            accel?.acceleration()?.addRouteAsync { source ->
                source.stream { data, _ ->
                    val acc = data.value(Acceleration::class.java)
                    val line = "${System.currentTimeMillis()},${acc.x()},${acc.y()},${acc.z()}"
                    accelWriter?.println(line)
                }
            }?.continueWith { task ->
                accel?.acceleration()?.start()
                accel?.start()
            }
            
            gyro?.angularVelocity()?.addRouteAsync { source ->
                source.stream { data, _ ->
                    val angular = data.value(AngularVelocity::class.java)
                    val line = "${System.currentTimeMillis()},${angular.x()},${angular.y()},${angular.z()}"
                    gyroWriter?.println(line)
                }
            }?.continueWith {
                gyro?.angularVelocity()?.start()
                gyro?.start()
            }


            mag?.magneticField()?.addRouteAsync { source ->
                source.stream { data, _ ->
                    val magnetic = data.value(MagneticField::class.java)
                    val line = "${System.currentTimeMillis()},${magnetic.x()},${magnetic.y()},${magnetic.z()}"
                    magWriter?.println(line)
                }
            }?.continueWith {
                mag?.magneticField()?.start()
                mag?.start()
            }

            promise.resolve("Started streaming to folder: ${currentFolder?.absolutePath}")

        } catch (e: Exception) {
            println("METAWEAR_DEBUG: Stream failed: ${e.message}")
            e.printStackTrace()
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

            // Close all writers
            accelWriter?.close()
            gyroWriter?.close()
            magWriter?.close()

            // Reset writers to null
            accelWriter = null
            gyroWriter = null
            magWriter = null

            promise.resolve("Data saved to folder: ${currentFolder?.absolutePath}")
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
        // Close writers if they're still open
        accelWriter?.close()
        gyroWriter?.close()
        magWriter?.close()
        
        super.onCatalystInstanceDestroy()
        reactApplicationContext.unbindService(this)
    }
}
