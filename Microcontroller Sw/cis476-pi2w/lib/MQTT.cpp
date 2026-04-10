#include "MQTT.h"

// Private Constructor sets up the FreeRTOS reconnect timer
MQTT::MQTT() {
    mqttReconnectTimer = xTimerCreate(
        "mqttTimer", 
        pdMS_TO_TICKS(2000), 
        pdFALSE, 
        (void*)0, 
        reconnectTimerCallback
    );
}

void MQTT::setup(const char* host, uint16_t port) {
    mqttClient.setServer(host, port);
}

void MQTT::setClientId(const char* clientId) {
    mqttClient.setClientId(clientId);
}

// Setup Last Will and Testament (LWT)
void MQTT::setWill(const char* topic, uint8_t qos, bool retain, const char* payload) {
    mqttClient.setWill(topic, qos, retain, payload);
}

void MQTT::connect() {
    Serial.println("[MQTT] Connecting to broker...");
    mqttClient.connect();
}

void MQTT::disconnect() {
    mqttClient.disconnect();
}

uint16_t MQTT::publish(const char* topic, uint8_t qos, bool retain, const char* payload) {
    return mqttClient.publish(topic, qos, retain, payload);
}

uint16_t MQTT::subscribe(const char* topic, uint8_t qos) {
    return mqttClient.subscribe(topic, qos);
}

// Callback Wrappers
void MQTT::onConnect(AsyncMqttClientInternals::OnConnectUserCallback callback) {
    mqttClient.onConnect(callback);
}

void MQTT::onDisconnect(AsyncMqttClientInternals::OnDisconnectUserCallback callback) {
    mqttClient.onDisconnect(callback);
}

void MQTT::onMessage(AsyncMqttClientInternals::OnMessageUserCallback callback) {
    mqttClient.onMessage(callback);
}

// Reconnect Timer Controls
void MQTT::startReconnectTimer() {
    xTimerStart(mqttReconnectTimer, 0);
}

void MQTT::stopReconnectTimer() {
    xTimerStop(mqttReconnectTimer, 0);
}

// Static callback for FreeRTOS timer
void MQTT::reconnectTimerCallback(TimerHandle_t xTimer) {
    MQTT::getInstance().connect();
}