#include "MqttManager.h"

// We set the buffer to 1024 to accommodate your JSON payloads
MqttManager::MqttManager() : mqttClient(1024) { 
    mqttReconnectTimer = xTimerCreate(
        "mqttTimer", 
        pdMS_TO_TICKS(2000), 
        pdFALSE, 
        (void*)0, 
        reconnectTimerCallback
    );
}

void MqttManager::setup(const char* host, uint16_t port) {
    mqttClient.begin(host, port, wifiClient);
}

void MqttManager::setClientId(const char* clientId) {
    _clientId = clientId;
}

void MqttManager::setWill(const char* topic, uint8_t qos, bool retain, const char* payload) {
    mqttClient.setWill(topic, payload, retain, qos);
    _hasWill = true;
}

void MqttManager::connect() {
    Serial.println("[MQTT] Connecting to broker...");
    
    bool success = mqttClient.connect(_clientId);

    if (success) {
        Serial.println("[MQTT] Connected to Broker!");
        stopReconnectTimer();
    } else {
        Serial.print("[MQTT] Failed, rc=");
        Serial.print(mqttClient.lastError());
        Serial.println(" - trying again later");
        startReconnectTimer();
    }
}

void MqttManager::disconnect() {
    mqttClient.disconnect();
}

void MqttManager::loop() {
    mqttClient.loop();
}

boolean MqttManager::connected() {
    return mqttClient.connected();
}

boolean MqttManager::publish(const char* topic, const char* payload, bool retain, uint8_t qos) {
    return mqttClient.publish(topic, payload, retain, qos);
}

boolean MqttManager::subscribe(const char* topic, uint8_t qos) {
    return mqttClient.subscribe(topic, qos);
}

void MqttManager::onMessage(MQTTClientCallbackSimple callback) {
    mqttClient.onMessage(callback);
}

void MqttManager::startReconnectTimer() {
    xTimerStart(mqttReconnectTimer, 0);
}

void MqttManager::stopReconnectTimer() {
    xTimerStop(mqttReconnectTimer, 0);
}

void MqttManager::reconnectTimerCallback(TimerHandle_t xTimer) {
    MqttManager::getInstance().connect();
}