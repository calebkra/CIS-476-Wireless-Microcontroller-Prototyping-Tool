#pragma once

#include <Arduino.h>
#include <AsyncMQTT_ESP32.h>

extern "C" {
  #include "freertos/FreeRTOS.h"
  #include "freertos/timers.h"
}

class MQTT {
public:

    // Singleton Access
    static MQTT& getInstance() {
        static MQTT instance;
        return instance;
    }

    // Delete copy constructor and assignment to enforce Singleton
    MQTT(const MQTT&) = delete;
    void operator=(const MQTT&) = delete;


    // Configuration & Connection
    void setup(const char* host, uint16_t port);
    void setClientId(const char* clientId);
    void setWill(const char* topic, uint8_t qos, bool retain, const char* payload);
    
    void connect();
    void disconnect();


    // Core Operations
    uint16_t publish(const char* topic, uint8_t qos, bool retain, const char* payload);
    uint16_t subscribe(const char* topic, uint8_t qos);


    // Event Handlers
    void onConnect(AsyncMqttClientInternals::OnConnectUserCallback callback);
    void onDisconnect(AsyncMqttClientInternals::OnDisconnectUserCallback callback);
    void onMessage(AsyncMqttClientInternals::OnMessageUserCallback callback);

    // Timer controls for WiFi Event integration
    void startReconnectTimer();
    void stopReconnectTimer();

private:
    // Private constructor
    MQTT();
    ~MQTT() = default;

    AsyncMqttClient mqttClient;
    TimerHandle_t mqttReconnectTimer;

    // FreeRTOS Timer callback must be static
    static void reconnectTimerCallback(TimerHandle_t xTimer);
};