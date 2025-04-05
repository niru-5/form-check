import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';



// Screens
import LoginScreen from './screens/LoginScreen';
import DeviceListScreen from './screens/DeviceListScreen';
import StreamingScreen from './screens/StreamingScreen';

// You can add DeviceListScreen later
// import DeviceListScreen from './app_src/FormCheckApp/screens/DeviceListScreen';

const Stack = createNativeStackNavigator();

function App(): React.JSX.Element {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Login">
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="DeviceList" component={DeviceListScreen} />
        <Stack.Screen name="StreamingScreen" component={StreamingScreen} />
        {/* Add this later when ready */}
        {/* <Stack.Screen name="DeviceList" component={DeviceListScreen} /> */}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default App;
