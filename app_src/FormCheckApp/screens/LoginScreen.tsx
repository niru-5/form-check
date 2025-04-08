import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert } from 'react-native';

const LoginScreen = ({ navigation }: any) => {
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    if (password === '1234') {
      navigation.navigate('DeviceList');
    } else {
      Alert.alert('Incorrect Password', 'Please try again.');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Login</Text>
      <TextInput
        placeholder="Enter password"
        secureTextEntry
        style={styles.input}
        onChangeText={setPassword}
        value={password}
      />
      <Button title="Login" onPress={handleLogin} />
    </View>
  );
};

export default LoginScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 24,
    marginBottom: 24,
    textAlign: 'center',
  },
  input: {
    borderWidth: 1,
    borderColor: '#aaa',
    padding: 10,
    borderRadius: 8,
    marginBottom: 16,
  },
});
