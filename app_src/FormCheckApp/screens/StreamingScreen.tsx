import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Button,
  Alert,
  NativeModules,
} from 'react-native';

// Import the native module
const { MetaWearModule } = NativeModules;

const StreamingScreen = ({ route, navigation }: any) => {
  const { deviceId, deviceName } = route.params;

  const handleConnect = async () => {
    try {
      const result = await MetaWearModule.connectToDevice(deviceId);
      Alert.alert('Success', result);
    } catch (error) {
      console.error('Connection error:', error);
      Alert.alert('Error', 'Failed to connect to the MetaWear device');
    }
  };

  const handleDisconnect = async () => {
    try {
      const result = await MetaWearModule.disconnectDevice();
      Alert.alert('Disconnected', result);
      navigation.goBack(); // Optional: Go back after disconnect
    } catch (error) {
      console.error('Disconnect error:', error);
      Alert.alert('Error', 'Failed to disconnect');
    }
  };

  const handleStreamData = async () => {
    try {
      const filePath = await MetaWearModule.streamAccelerometer();
      Alert.alert('Success', `Data saved at:\n${filePath}`);
    } catch (error) {
      console.error('Stream error:', error);
      Alert.alert('Error', 'Failed to stream data');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Streaming Screen</Text>

      <Text style={styles.label}>Device Name:</Text>
      <Text style={styles.value}>{deviceName || 'Unnamed Device'}</Text>

      <Text style={styles.label}>Device ID:</Text>
      <Text style={styles.value}>{deviceId}</Text>

      <View style={styles.buttonContainer}>
        <Button title="Connect to Device" onPress={handleConnect} />
      </View>

      <View style={styles.buttonContainer}>
        <Button title="Stream Data (3s)" onPress={handleStreamData} />
      </View>

      <View style={styles.buttonContainer}>
        <Button title="Disconnect" color="red" onPress={handleDisconnect} />
      </View>
    </View>
  );
};

export default StreamingScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 32,
    textAlign: 'center',
  },
  label: {
    fontSize: 16,
    color: '#888',
    marginTop: 12,
  },
  value: {
    fontSize: 18,
    fontWeight: '600',
  },
  buttonContainer: {
    marginTop: 20,
  },
});
