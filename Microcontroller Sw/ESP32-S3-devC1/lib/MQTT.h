#pragma once

#include <Arduino.h>
#include <WiFi.h>
// #include <MQTT.h>
#include <MQTTClient.h> // From 256dpi/MQTT

extern "C" {
  #include "freertos/FreeRTOS.h"
  #include "freertos/timers.h"
}

class MqttManager {
public:
    static MqttManager& getInstance() {
        static MqttManager instance;
        return instance;
    }

    MqttManager(const MqttManager&) = delete;
    void operator=(const MqttManager&) = delete;

    void setup(const char* host, uint16_t port);
    void setClientId(const char* clientId);
    void setWill(const char* topic, uint8_t qos, bool retain, const char* payload);
    
    void connect();
    void disconnect();
    void loop(); 

    // QoS defaults to 2 here!
    boolean publish(const char* topic, const char* payload, bool retain = false, uint8_t qos = 2);
    boolean subscribe(const char* topic, uint8_t qos = 2);

    void onMessage(MQTTClientCallbackSimple callback);
    
    boolean connected();

    void startReconnectTimer();
    void stopReconnectTimer();

private:
    MqttManager();
    ~MqttManager() = default;

    WiFiClient wifiClient;
    MQTTClient mqttClient; 
    TimerHandle_t mqttReconnectTimer;

    const char* _clientId;
    bool _hasWill = false;

    static void reconnectTimerCallback(TimerHandle_t xTimer);
};