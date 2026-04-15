#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include "secrets.h"
#include "MQTT.h"                     // ESP32 native AsyncMqttClient wrapper

// ==========================================
//    ESP32 main (aligned with Pico version)
// ==========================================

// --- Hardware Abstraction Layer ---
#include "IController.h"
#ifdef USE_PICO_CONTROLLER
    #include "PicoController.h"
    IController* myBoard = new PicoController();
#else
    #error "Define a board in platformio.ini!"
#endif

// Forward declarations
void sendAllStates();
void onMqttConnect(bool sessionPresent);
void onMqttDisconnect(AsyncMqttClientDisconnectReason reason);
void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total);

//  DATA STRUCTURE & QUEUE SETUP
// Define the shape of the data you want to pass between cores
typedef struct {
    int sensorValue;
    int pin;
    unsigned long timestamp;
} CoreMessage;

// for knowing if input or putput.
typedef enum { INPUT_PIN, OUTPUT_PIN } PinMode_t;

// for moving away from function pointers 
typedef enum { SIG_DIGITAL, SIG_ANALOG, SIG_PWM } SignalType_t;

typedef struct {
    const char* label;
    int pin;
  PinMode_t mode;           // INPUT_PIN or OUTPUT_PIN
  SignalType_t signalType;  // SIG_DIGITAL, SIG_ANALOG, or SIG_PWM
    uint32_t interval;
    uint32_t lastCheck;
} PinObject;

// Create the global queue so both cores can access it
// FreeRTOS Queue (ESP32 native)
QueueHandle_t coreQueue;   // FreeRTOS queue handle

// Updated labels to explicitly match the projects requirement: 
// {"DO1":(value), "DO2": (value), "DI1": (value), "DI2": (value), "PWM1": (value), "PWM2":(value)}
// this was chat's Idea after a code review better syntax. 
PinObject myHardware[] = {
    {"PWM1",  34,  OUTPUT_PIN, SIG_PWM,     5000, 0}, 
    {"PWM2",  35,  OUTPUT_PIN, SIG_PWM,     5000, 0}, 
    {"DI1",   36,  INPUT_PIN,  SIG_DIGITAL, 5000, 0}, 
    {"DI2",   37,  INPUT_PIN,  SIG_DIGITAL, 5000, 0}, 
    {"DO1",   38,  OUTPUT_PIN, SIG_DIGITAL, 5000, 0},
    {"DO2",   39,  OUTPUT_PIN, SIG_DIGITAL, 5000, 0}
};

// Calculate how many pins are in the array automatically
const int PIN_COUNT = sizeof(myHardware) / sizeof(PinObject);

// ==========================================
//    MQTT Callbacks
// ==========================================

void sendAllStates() {
    JsonDocument doc;
    doc["ID"] = DEVICE_ID;
    doc["Device_Type"] = "ESP32";
    doc["Key"] = AUTH_CODE;
    doc["Server_Command"] = "Send_Message";
    doc["Client_Command"] = "Receive State";

    JsonObject message = doc["Message"].to<JsonObject>();

  // Loop through hardware and add each pin value to the JSON
    for (int i = 0; i < PIN_COUNT; i++) {
        int val = 0;
        // Use hardware abstraction for all reads
        if (myHardware[i].mode == INPUT_PIN) {
            val = myBoard->readDigital(myHardware[i].pin);
        } else if (myHardware[i].signalType == SIG_PWM) {
            val = myBoard->readPWM(myHardware[i].pin);
        } else {
            val = myBoard->readDigital(myHardware[i].pin);
        }
        message[myHardware[i].label] = val;
    }

    char buffer[512];
    serializeJson(doc, buffer);
    MQTT::getInstance().publish("Test/Server", 2, false, buffer);
}

void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties,
                   size_t len, size_t index, size_t total) {
    String payloadStr = String(payload).substring(0, len);
    JsonDocument doc;
    deserializeJson(doc, payloadStr);

    if (doc["Key"] != AUTH_CODE) {
        Serial.println("[Security] Unauthorized command rejected.");
        return;
    }

    String command = doc["Client_Command"];

    if (command == "Get State") {
        sendAllStates();
    }
    else if (command == "Set State") {
        const char* targetPinLabel = doc["Message"]["Pin"];
        int value = doc["Message"]["Value"];

        // Find the pin by label and update it
        for(int i=0; i<PIN_COUNT; i++) {
            if(strcmp(myHardware[i].label, targetPinLabel) == 0) {
                if (myHardware[i].signalType == SIG_PWM) {
                    myBoard->writePWM(myHardware[i].pin, (float)value);
                } else {
                    myBoard->writeDigital(myHardware[i].pin, value);
                }
                break;
            }
        }
        sendAllStates();   // Reply with updated states
    }
}

void onMqttConnect(bool sessionPresent) {
    Serial.println("[MQTT] Connected to Broker!");
    MQTT::getInstance().stopReconnectTimer();

  // Send the mandatory "Connect" message to the Server
    JsonDocument connDoc;
    connDoc["ID"] = DEVICE_ID;
    connDoc["Device_Type"] = "ESP32";
    connDoc["Key"] = AUTH_CODE;
    connDoc["Server_Command"] = "Connect";
    
    char connBuffer[256];
    serializeJson(connDoc, connBuffer);
    MQTT::getInstance().publish("Test/Server", 2, false, connBuffer);

    // Subscribe to device‑specific topic
    String myTopic = String(SUB_TOPIC_PREFIX) + String(DEVICE_ID);
    MQTT::getInstance().subscribe(myTopic.c_str(), 2);
    Serial.print("[MQTT] Subscribed to: ");
    Serial.println(myTopic);
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
    Serial.println("[MQTT] Disconnected from Broker.");
    MQTT::getInstance().startReconnectTimer();
}




// ==========================================
//    Core 0 Setup & Loop (Network / MQTT)
// ==========================================

void setup() {
    Serial.begin(115200);
    delay(2000);

    // Create FreeRTOS queue (ESP32 native)
    coreQueue = xQueueCreate(10, sizeof(CoreMessage));
    if (coreQueue == NULL) {
        Serial.println("Failed to create queue!");
        while (1);
    }

    Serial.print("Connecting to Wi-Fi: ");
    Serial.println(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWi-Fi Connected!");

    // Prepare Last Will and Testament
    JsonDocument lwtDoc;
    lwtDoc["ID"] = DEVICE_ID;
    lwtDoc["Device_Type"] = "ESP32";
    lwtDoc["Key"] = AUTH_CODE;
    lwtDoc["Server_Command"] = "Disconnect";
    char lwtBuffer[256];
    serializeJson(lwtDoc, lwtBuffer);

  // Setup Singleton MQTT Interface
    MQTT& mqtt = MQTT::getInstance();
    mqtt.setup(MQTT_SERVER, MQTT_PORT);
    mqtt.setClientId(DEVICE_ID);
    mqtt.setWill("Test/Server", 2, false, lwtBuffer);   // retain = false (align with Pico)

    mqtt.onConnect(onMqttConnect);
    mqtt.onDisconnect(onMqttDisconnect);
    mqtt.onMessage(onMqttMessage);

    mqtt.connect();
}

void loop() {
    CoreMessage incomingMsg;

    // Try to grab data from the queue
    if (xQueueReceive(coreQueue, &incomingMsg, 0) == pdTRUE) {
        sendAllStates();
    }

    // Other non‑blocking tasks can go here
    delay(10);
}

// ==========================================
//    Core 1 Setup & Loop (Hardware I/O)
// ==========================================

void setup1() {
  // Setup hardware for Core 1 (e.g., I2C sensors, SPI devices)
  // Note: setup1() runs automatically alongside setup()

  // speficty the PIN here. with pwnPin
  // required for saying if a pin is reading or doing something else. 
  // this just basically tells the code HEY WE WANT TO READ OR WRITE ON THESE
    for (int i = 0; i < PIN_COUNT; i++) {
        if (myHardware[i].mode == INPUT_PIN) {
            pinMode(myHardware[i].pin, INPUT_PULLUP);   // ESP32 uses INPUT_PULLUP
        } else {
            pinMode(myHardware[i].pin, OUTPUT);
        }
    }
}

void loop1() {
    unsigned long now = millis();

    for (int i = 0; i < PIN_COUNT; i++) {
        if (myHardware[i].mode == INPUT_PIN && (now - myHardware[i].lastCheck >= myHardware[i].interval)) {
            CoreMessage newMsg;
            newMsg.pin = myHardware[i].pin;
            newMsg.timestamp = now;

            switch (myHardware[i].signalType) {
                case SIG_DIGITAL:
                    newMsg.sensorValue = myBoard->readDigital(myHardware[i].pin);
                    break;
                case SIG_ANALOG:
                    newMsg.sensorValue = myBoard->readAnalog(myHardware[i].pin);
                    break;
                case SIG_PWM:
                    newMsg.sensorValue = myBoard->readPWM(myHardware[i].pin);
                    break;
            }

            // Send to Core 0 queue (non‑blocking)
            xQueueSend(coreQueue, &newMsg, 0);
            myHardware[i].lastCheck = now;
        }
    }

    delay(1);
}