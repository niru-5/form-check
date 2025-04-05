import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Button,
  ScrollView,
} from 'react-native';
import Slider from '@react-native-community/slider';

const ConfigureScreen = ({ route, navigation }: any) => {
  const { currentConfig, deviceId, deviceName } = route.params;

  const [accelerometerHz, setAccelerometerHz] = useState(currentConfig.accel);
  const [gyroscopeHz, setGyroscopeHz] = useState(currentConfig.gyro);
  const [magnetometerHz, setMagnetometerHz] = useState(currentConfig.mag);

  const handleSave = () => {
    navigation.navigate('StreamingScreen', {
      newConfig: {
        accel: accelerometerHz,
        gyro: gyroscopeHz,
        mag: magnetometerHz,
      },
      deviceId,
      deviceName,
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Configure Sensors</Text>

      <Text style={styles.label}>Accelerometer Frequency: {accelerometerHz} Hz</Text>
      <Slider
        minimumValue={10}
        maximumValue={200}
        step={10}
        value={accelerometerHz}
        onValueChange={setAccelerometerHz}
      />

      <Text style={styles.label}>Gyroscope Frequency: {gyroscopeHz} Hz</Text>
      <Slider
        minimumValue={10}
        maximumValue={200}
        step={10}
        value={gyroscopeHz}
        onValueChange={setGyroscopeHz}
      />

      <Text style={styles.label}>Magnetometer Frequency: {magnetometerHz} Hz</Text>
      <Slider
        minimumValue={5}
        maximumValue={100}
        step={5}
        value={magnetometerHz}
        onValueChange={setMagnetometerHz}
      />

      <View style={styles.buttonRow}>
        <Button title="Save Config" onPress={handleSave} />
        <View style={{ width: 16 }} />
        <Button title="Cancel" color="red" onPress={() => navigation.goBack()} />
      </View>
    </ScrollView>
  );
};

export default ConfigureScreen;

const styles = StyleSheet.create({
  container: {
    padding: 24,
    backgroundColor: '#fff',
    flexGrow: 1,
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 24,
    textAlign: 'center',
  },
  label: {
    marginTop: 20,
    fontSize: 16,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 40,
  },
});
