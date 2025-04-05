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

const StreamingScreen = ({ route }: any) => {
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
    marginTop: 40,
  },
});
