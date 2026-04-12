#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <MQTTClient.h> // From 256dpi/MQTT

extern "C" {
  #include "freertos/FreeRTOS.h"
  #include "freertos/timers.h"
  #include "freertos/task.h"
}

// --- MOCK ASYNC TYPES TO KEEP FRONT-END UNCHANGED ---
struct AsyncMqttClientMessageProperties {
    uint8_t qos;
    bool dup;
    bool retain;
};

// Mocking the disconnect reasons the ESP32 library used
enum class AsyncMqttClientDisconnectReason {
    TCP_DISCONNECTED = 0,
    MQTT_UNACCEPTABLE_PROTOCOL_VERSION = 1,
    MQTT_IDENTIFIER_REJECTED = 2,
    MQTT_SERVER_UNAVAILABLE = 3,
    MQTT_MALFORMED_CREDENTIALS = 4,
    MQTT_NOT_AUTHORIZED = 5
};

namespace AsyncMqttClientInternals {
    typedef void (*OnConnectUserCallback)(bool sessionPresent);
    typedef void (*OnDisconnectUserCallback)(AsyncMqttClientDisconnectReason reason);
    typedef void (*OnMessageUserCallback)(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total);
}
// ----------------------------------------------------

class MQTT {
public:
    // Singleton Access
    static MQTT& getInstance() {
        static MQTT instance;
        return instance;
    }

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

    void startReconnectTimer();
    void stopReconnectTimer();

private:
    MQTT();
    ~MQTT() = default;

    TimerHandle_t mqttReconnectTimer;
    static void reconnectTimerCallback(TimerHandle_t xTimer);

    WiFiClient wifiClient;
    MQTTClient mqttClient;

    String _clientId;
    bool _wasConnected;
    
    // Store user callbacks
    AsyncMqttClientInternals::OnConnectUserCallback _onConnectCb;
    AsyncMqttClientInternals::OnDisconnectUserCallback _onDisconnectCb;
    AsyncMqttClientInternals::OnMessageUserCallback _onMessageCb;

    // FreeRTOS background task
    TaskHandle_t _loopTask;
    static void loopTaskCode(void* parameter);
    
    // Bridge callback
    static void messageBridge(MQTTClient *client, char topic[], char bytes[], int length);
};