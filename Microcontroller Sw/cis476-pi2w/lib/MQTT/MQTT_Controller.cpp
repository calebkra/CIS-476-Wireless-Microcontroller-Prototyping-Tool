#include "MQTT_Controller.h"

MQTT::MQTT()
    : mqttClient(4096)
    , _wasConnected(false)
    , _onConnectCb(nullptr)
    , _onDisconnectCb(nullptr)
    , _onMessageCb(nullptr)
    , _reconnectEnabled(false)
    , _lastReconnectAttempt(0)
{
    // No background task – user must call loop()
}

void MQTT::setup(const char* host, uint16_t port) {
    mqttClient.begin(host, port, wifiClient);
    mqttClient.onMessageAdvanced(messageBridge);
}

void MQTT::setClientId(const char* clientId) {
    _clientId = clientId;
}

void MQTT::setWill(const char* topic, uint8_t qos, bool retain, const char* payload) {
    mqttClient.setWill(topic, payload, retain, qos);
}

void MQTT::connect() {
    Serial.println("[MQTT] Connecting to broker...");

    bool success = mqttClient.connect(_clientId.c_str());

    if (success) {
        Serial.println("[MQTT] Connected to Broker!");
        stopReconnectTimer();
        if (_onConnectCb) {
            _onConnectCb(false);   // false = not a session present (simplified)
        }
    } else {
        Serial.print("[MQTT] Failed, rc=");
        Serial.print(mqttClient.lastError());
        Serial.println(" - will retry if reconnect timer is active");
        // If reconnect is enabled, loop() will handle it
    }
}

void MQTT::disconnect() {
    Serial.println("[MQTT] Disconnecting");
    mqttClient.disconnect();
}

void MQTT::loop() {
    // Let the underlying library process incoming data
    mqttClient.loop();

    bool isConnected = mqttClient.connected();

    // Detect falling edge: was connected, now disconnected
    if (_wasConnected && !isConnected) {
        Serial.println("[MQTT] Connection lost");
        if (_onDisconnectCb) {
            _onDisconnectCb(AsyncMqttClientDisconnectReason::TCP_DISCONNECTED);
        }
        // If reconnect is enabled, we'll attempt to reconnect in this loop
    }

    // Handle automatic reconnection if enabled and disconnected
    if (_reconnectEnabled && !isConnected) {
        unsigned long now = millis();
        if (now - _lastReconnectAttempt >= 5000) {   // retry every 5 seconds
            _lastReconnectAttempt = now;
            Serial.println("[MQTT] Reconnect attempt...");
            connect();   // will set _reconnectEnabled = false if successful
        }
    }

    _wasConnected = isConnected;
}

uint16_t MQTT::publish(const char* topic, uint8_t qos, bool retain, const char* payload) {
    return mqttClient.publish(topic, payload, retain, qos) ? 1 : 0;
}

uint16_t MQTT::subscribe(const char* topic, uint8_t qos) {
    return mqttClient.subscribe(topic, qos) ? 1 : 0;
}

// --- Callback registration (unchanged) ---
void MQTT::onConnect(AsyncMqttClientInternals::OnConnectUserCallback callback) {
    _onConnectCb = callback;
}

void MQTT::onDisconnect(AsyncMqttClientInternals::OnDisconnectUserCallback callback) {
    _onDisconnectCb = callback;
}

void MQTT::onMessage(AsyncMqttClientInternals::OnMessageUserCallback callback) {
    _onMessageCb = callback;
}

// --- Reconnect control (simplified) ---
void MQTT::startReconnectTimer() {
    _reconnectEnabled = true;
    _lastReconnectAttempt = millis();   // avoid immediate retry
}

void MQTT::stopReconnectTimer() {
    _reconnectEnabled = false;
}

// --- Static bridge (unchanged) ---
void MQTT::messageBridge(MQTTClient *client, char topic[], char bytes[], int length) {
    MQTT& instance = MQTT::getInstance();
    if (instance._onMessageCb) {
        AsyncMqttClientMessageProperties props;
        props.qos    = 2;
        props.dup    = false;
        props.retain = false;
        instance._onMessageCb(topic, bytes, props, length, 0, length);
    }
}