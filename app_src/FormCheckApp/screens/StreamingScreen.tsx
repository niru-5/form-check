import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Button,
  Alert,
  NativeModules,
} from 'react-native';
import { useIsFocused, useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';

// Define the type for the navigation parameters
type RootStackParamList = {
  StreamingScreen: { deviceName: string; deviceId: string; newConfig?: { accel: number; gyro: number; mag: number; } };
  ConfigureScreen: { currentConfig: { accel: number; gyro: number; mag: number; } };
};

type StreamingScreenNavigationProp = StackNavigationProp<RootStackParamList, 'StreamingScreen'>;
type StreamingScreenRouteProp = RouteProp<RootStackParamList, 'StreamingScreen'>;

const { MetaWearModule } = NativeModules;

const StreamingScreen = () => {
  const navigation = useNavigation<StreamingScreenNavigationProp>();
  const route = useRoute<StreamingScreenRouteProp>();
  const isFocused = useIsFocused();

  const [config, setConfig] = useState({
    accel: 100,
    gyro: 100,
    mag: 25,
  });

  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sampleCounts, setSampleCounts] = useState({ accel: 0, gyro: 0, mag: 0 });
  const [sampleCountInterval, setSampleCountInterval] = useState<NodeJS.Timer | null>(null);

  useEffect(() => {
    if (route.params?.newConfig) {
      setConfig(route.params.newConfig);
    }
  }, [route.params, isFocused]);

  useEffect(() => {
    if (isStreaming) {
      // Start polling for sample counts
      const interval = setInterval(async () => {
        try {
          const counts = await MetaWearModule.getSampleCounts();
          setSampleCounts(counts);
        } catch (error) {
          console.error('Failed to get sample counts:', error);
        }
      }, 1000); // Update every second
      setSampleCountInterval(interval);
    } else {
      // Clear interval when not streaming
      if (sampleCountInterval) {
        clearInterval(sampleCountInterval);
        setSampleCountInterval(null);
      }
      setSampleCounts({ accel: 0, gyro: 0, mag: 0 });
    }

    return () => {
      if (sampleCountInterval) {
        clearInterval(sampleCountInterval);
      }
    };
  }, [isStreaming]);

  const handleConnectionToggle = async () => {
    try {
      if (!isConnected) {
        // Connect
        const result = await MetaWearModule.connectToDevice(route.params.deviceId);
        setIsConnected(true);
        Alert.alert('Success', result);
      } else {
        // Disconnect
        const result = await MetaWearModule.disconnectDevice();
        setIsConnected(false);
        Alert.alert('Disconnected', result);
      }
    } catch (error) {
      console.error('Connection error:', error);
      Alert.alert('Error', isConnected ? 'Failed to disconnect' : 'Failed to connect to the MetaWear device');
    }
  };

  const handleStreamStart = async () => {
    try {
      const path = await MetaWearModule.startStream({
        accel: config.accel,
        gyro: config.gyro,
        mag: config.mag
      });
      setIsStreaming(true);
      Alert.alert('Streaming', `Saved to: ${path}`);
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Stream failed');
    }
  };

  const handleStreamStop = async () => {
    try {
      const result = await MetaWearModule.stopStream();
      setIsStreaming(false);
      Alert.alert('Success', result);
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Failed to stop stream and save data');
    }
  };

  const goToConfigure = () => {
    navigation.navigate('ConfigureScreen', {
      currentConfig: config,
      deviceId: route.params.deviceId,
      deviceName: route.params.deviceName,
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Streaming Screen</Text>

      <Text style={styles.label}>Device Name:</Text>
      <Text style={styles.value}>{route.params.deviceName || 'Unnamed Device'}</Text>

      <Text style={styles.label}>Device ID:</Text>
      <Text style={styles.value}>{route.params.deviceId}</Text>

      <Text style={styles.label}>Current Config:</Text>
      <Text>Accelerometer: {config.accel} Hz</Text>
      <Text>Gyroscope: {config.gyro} Hz</Text>
      <Text>Magnetometer: {config.mag} Hz</Text>

      {isStreaming && (
        <View style={styles.sampleCountContainer}>
          <Text style={styles.label}>Samples Collected:</Text>
          <Text>Accelerometer: {sampleCounts.accel}</Text>
          <Text>Gyroscope: {sampleCounts.gyro}</Text>
          <Text>Magnetometer: {sampleCounts.mag}</Text>
        </View>
      )}

      <View style={styles.buttonContainer}>
        <Button title="Configure Sensors" onPress={goToConfigure} />
      </View>

      <View style={styles.buttonContainer}>
        <Button 
          title={isConnected ? "Disconnect" : "Connect to Device"} 
          onPress={handleConnectionToggle}
          color={isConnected ? "red" : undefined}
        />
      </View>

      <View style={styles.buttonContainer}>
        <Button 
          title="Start Stream" 
          onPress={handleStreamStart} 
          disabled={isStreaming || !isConnected}
        />
      </View>

      <View style={styles.buttonContainer}>
        <Button 
          title="Stop Stream" 
          onPress={handleStreamStop} 
          disabled={!isStreaming} 
        />
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
    marginBottom: 24,
    textAlign: 'center',
  },
  label: {
    fontSize: 16,
    marginTop: 12,
    color: '#888',
  },
  value: {
    fontSize: 18,
    fontWeight: '600',
  },
  buttonContainer: {
    marginTop: 20,
  },
  sampleCountContainer: {
    marginTop: 20,
    padding: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 5,
  },
});
