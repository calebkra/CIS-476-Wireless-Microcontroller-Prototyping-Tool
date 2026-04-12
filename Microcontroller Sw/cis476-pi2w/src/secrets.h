#ifndef SECRETS_H
#define SECRETS_H

const char* WIFI_SSID = "Test-Wifi"; 
const char* WIFI_PASS = "goodlife";

// Put your Python server's local IP here
const char* MQTT_SERVER = "192.168.8.101"; 
const int MQTT_PORT = 1883;

// put the auth code here
const char* AUTH_CODE = "1234";
const char* DEVICE_ID = "M002";
// publish topics. 
const char* SUB_TOPIC_PREFIX  = "Microcontroller/PICO/";

#endif