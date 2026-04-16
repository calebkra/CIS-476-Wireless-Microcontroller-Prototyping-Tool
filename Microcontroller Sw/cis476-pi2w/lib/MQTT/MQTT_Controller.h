#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <MQTTClient.h> // From 256dpi/MQTT

// --- Mock async types to keep front‑end unchanged ---
struct AsyncMqttClientMessageProperties {
    uint8_t qos;
    bool dup;
    bool retain;
};

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
    // Singleton access
    static MQTT& getInstance() {
        static MQTT instance;
        return instance;
    }

    MQTT(const MQTT&) = delete;
    void operator=(const MQTT&) = delete;

    // Configuration
    void setup(const char* host, uint16_t port);
    void setClientId(const char* clientId);
    void setWill(const char* topic, uint8_t qos, bool retain, const char* payload);

    // Connection
    void connect();
    void disconnect();
    void loop();                     // << Must be called regularly (e.g., in main loop())

    // Core operations
    uint16_t publish(const char* topic, uint8_t qos, bool retain, const char* payload);
    uint16_t subscribe(const char* topic, uint8_t qos);

    // Event handlers (same signatures as before)
    void onConnect(AsyncMqttClientInternals::OnConnectUserCallback callback);
    void onDisconnect(AsyncMqttClientInternals::OnDisconnectUserCallback callback);
    void onMessage(AsyncMqttClientInternals::OnMessageUserCallback callback);

    // Reconnect control (kept for API compatibility)
    void startReconnectTimer();
    void stopReconnectTimer();

private:
    MQTT();
    ~MQTT() = default;

    WiFiClient wifiClient;
    MQTTClient mqttClient;

    String _clientId;
    bool _wasConnected;

    // User callbacks
    AsyncMqttClientInternals::OnConnectUserCallback _onConnectCb;
    AsyncMqttClientInternals::OnDisconnectUserCallback _onDisconnectCb;
    AsyncMqttClientInternals::OnMessageUserCallback _onMessageCb;

    // Reconnect state
    bool _reconnectEnabled;
    unsigned long _lastReconnectAttempt;

    // Bridge callback (static)
    static void messageBridge(MQTTClient *client, char topic[], char bytes[], int length);
};