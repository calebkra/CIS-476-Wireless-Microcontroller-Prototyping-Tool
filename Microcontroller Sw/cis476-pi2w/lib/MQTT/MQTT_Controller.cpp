#include "MQTT_Controller.h"

// Set a large buffer (2048) to handle your JSON payloads safely
MQTT::MQTT() : mqttClient(2048), _wasConnected(false), _onConnectCb(nullptr), _onDisconnectCb(nullptr), _onMessageCb(nullptr) {
    
    mqttReconnectTimer = xTimerCreate(
        "mqttTimer", 
        pdMS_TO_TICKS(2000), 
        pdFALSE, 
        (void*)0, 
        reconnectTimerCallback
    );

    // Start a background FreeRTOS task to process incoming MQTT messages automatically
    xTaskCreate(loopTaskCode, "mqttLoop", 4096, this, 1, &_loopTask);
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
            _onConnectCb(false); // Trigger front-end connect callback
        }
    } else {
        Serial.print("[MQTT] Failed, rc=");
        Serial.print(mqttClient.lastError());
        Serial.println(" - trying again later");
        startReconnectTimer();
    }
}

void MQTT::disconnect() {
    mqttClient.disconnect();
}

uint16_t MQTT::publish(const char* topic, uint8_t qos, bool retain, const char* payload) {
    // Returns 1 on success, 0 on fail to match the uint16_t signature
    return mqttClient.publish(topic, payload, retain, qos) ? 1 : 0;
}

uint16_t MQTT::subscribe(const char* topic, uint8_t qos) {
    return mqttClient.subscribe(topic, qos) ? 1 : 0;
}

// --- Callbacks ---
void MQTT::onConnect(AsyncMqttClientInternals::OnConnectUserCallback callback) {
    _onConnectCb = callback;
}

void MQTT::onDisconnect(AsyncMqttClientInternals::OnDisconnectUserCallback callback) {
    _onDisconnectCb = callback;
}

void MQTT::onMessage(AsyncMqttClientInternals::OnMessageUserCallback callback) {
    _onMessageCb = callback;
}

void MQTT::startReconnectTimer() {
    xTimerStart(mqttReconnectTimer, 0);
}

void MQTT::stopReconnectTimer() {
    xTimerStop(mqttReconnectTimer, 0);
}

void MQTT::reconnectTimerCallback(TimerHandle_t xTimer) {
    MQTT::getInstance().connect();
}

// --- Internal Handlers ---

// This task runs continuously in the background, making the synchronous library act "Async"
void MQTT::loopTaskCode(void* parameter) {
    MQTT* instance = static_cast<MQTT*>(parameter);
    for (;;) {
        bool isConnected = instance->mqttClient.connected();
        
        // Detect sudden disconnects and fire callback
        if (instance->_wasConnected && !isConnected) {
            if (instance->_onDisconnectCb) {
                instance->_onDisconnectCb(AsyncMqttClientDisconnectReason::TCP_DISCONNECTED); 
            }
        }
        
        if (isConnected) {
            instance->mqttClient.loop(); // Handle QoS 2 acknowledgments
        }
        
        instance->_wasConnected = isConnected;
        vTaskDelay(pdMS_TO_TICKS(10)); // Yield to other FreeRTOS tasks
    }
}

// Maps the 256dpi callback signature to the AsyncMqttClient signature your main.cpp expects
void MQTT::messageBridge(MQTTClient *client, char topic[], char bytes[], int length) {
    MQTT& instance = MQTT::getInstance();
    if (instance._onMessageCb) {
        AsyncMqttClientMessageProperties props;
        props.qos = 2;       
        props.dup = false;   
        props.retain = false;
        
        instance._onMessageCb(topic, bytes, props, length, 0, length);
    }
}