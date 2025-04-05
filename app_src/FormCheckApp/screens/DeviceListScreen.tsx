import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, PermissionsAndroid, Platform, StyleSheet, ActivityIndicator } from 'react-native';
import { BleManager, Device } from 'react-native-ble-plx';

const manager = new BleManager();

const DeviceListScreen = ({ navigation }: any) => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [isScanning, setIsScanning] = useState(false);

  useEffect(() => {
    requestPermissions().then(startScan);

    return () => {
      manager.stopDeviceScan();
    };
  }, []);

  const requestPermissions = async () => {
    if (Platform.OS === 'android') {
      await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
      ]);
    }
  };

  const startScan = () => {
    setIsScanning(true);
    const discoveredDevices: { [id: string]: Device } = {};

    manager.startDeviceScan(null, null, (error, device) => {
      if (error) {
        console.error('Scan error:', error);
        setIsScanning(false);
        return;
      }

      if (device && device.name && !discoveredDevices[device.id]) {
        discoveredDevices[device.id] = device;
        setDevices(Object.values(discoveredDevices));
      }
    });

    // Stop scan after 10 seconds
    setTimeout(() => {
      manager.stopDeviceScan();
      setIsScanning(false);
    }, 10000);
  };

  const handleSelectDevice = (device: Device) => {
    // You can pass the device ID to the next screen or save in context
    console.log('Selected device:', device.name, device.id);
    // For now, let's just alert
    navigation.navigate('StreamingScreen', {
        deviceId: device.id,
        deviceName: device.name,
      });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Nearby Bluetooth Devices</Text>
      {isScanning ? (
        <ActivityIndicator size="large" />
      ) : (
        <FlatList
          data={devices}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.deviceItem} onPress={() => handleSelectDevice(item)}>
              <Text>{item.name || 'Unnamed Device'}</Text>
              <Text style={styles.deviceId}>{item.id}</Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
};

export default DeviceListScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  deviceItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#ddd',
  },
  deviceId: {
    fontSize: 12,
    color: '#888',
  },
});
