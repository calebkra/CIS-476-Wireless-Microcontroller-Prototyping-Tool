#include <Arduino.h>
#include <pico/util/queue.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include "secrets.h" 
#include "MQTT_Controller.h"
// ==========================================
//    pico cpp
// ==========================================

// --- Hardware Abstraction Layer ---
// because why not! 
// as of now this is just an interface for the other board
#include "IController.h"
#ifdef USE_PICO_CONTROLLER
    #include "PicoController.h"
    IController* myBoard = new PicoController();
#else
    #error "Define a board in platformio.ini!"
#endif


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
queue_t coreQueue;

// Updated labels to explicitly match the rubric requirement: 
// {"DO1":(value), "DO2": (value), "DI1": (value), "DI2": (value), "PWM1": (value), "PWM2":(value)}
// this was chat's Idea after a code review idk why. 
PinObject myHardware[] = {
    {"PWM1",  34,  OUTPUT_PIN, SIG_PWM,     5000, 0}, 
    {"PWM2",  35,  OUTPUT_PIN, SIG_PWM,     5000, 0}, 
    {"DI1",   36,  INPUT_PIN,  SIG_DIGITAL, 5000, 0}, 
    {"DI2",   37,  INPUT_PIN,  SIG_DIGITAL, 5000, 0}, 
    {"DO1",   38,  OUTPUT_PIN, SIG_DIGITAL, 5000, 0},
    {"DO2",   39,  OUTPUT_PIN, SIG_DIGITAL, 5000, 0} // Added to match rubric
};

// Calculate how many pins are in the array automatically
const int PIN_COUNT = sizeof(myHardware) / sizeof(PinObject);



void sendAllStates() {
  JsonDocument doc;
  doc["ID"] = DEVICE_ID;
  doc["Device_Type"] = "Pico";
  doc["Key"] = AUTH_CODE;
  doc["Server_Command"] = "Send_Message";
  doc["Client_Command"] = "Recieve State";

  JsonObject message = doc["Message"].to<JsonObject>();
  
  // Loop through hardware and add each pin value to the JSON
  for (int i = 0; i < PIN_COUNT; i++) {
    int val = 0;
    if (myHardware[i].mode == INPUT_PIN) { 
        val = digitalRead(myHardware[i].pin); 
    } else {
        // For outputs, we'd ideally track the last set state 
      // For now, we'll read the digital state or pulse state
        val = digitalRead(myHardware[i].pin); 
    }
    message[myHardware[i].label] = val;
  }

  char buffer[512];
  serializeJson(doc, buffer);
  
  // Publish back to the server topic with QoS 2
  MQTT::getInstance().publish("Test/Server", 2, false, buffer); 
}

void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total) {
    String payloadStr = String(payload).substring(0, len);
    
    JsonDocument doc;
    deserializeJson(doc, payloadStr);

    String command = doc["Client_Command"];

    if (command == "Get State") {
        sendAllStates();
    } 
    else if (command == "Set State") {
        String targetPinLabel = doc["Message"]["Pin"];
        int value = doc["Message"]["Value"];
        
        // Find the pin by label and update it
        for(int i=0; i<PIN_COUNT; i++) {
            if(String(myHardware[i].label) == targetPinLabel) {
                if(myHardware[i].signalType == SIG_PWM) {
                    analogWrite(myHardware[i].pin, value);
                } else {
                    digitalWrite(myHardware[i].pin, value > 0 ? HIGH : LOW);
                }
                break;
            }
        }
        sendAllStates(); 
    }
}

void onMqttConnect(bool sessionPresent) {
  Serial.println("[MQTT] Connected to Broker!");
  MQTT::getInstance().stopReconnectTimer();

  // Send the mandatory "Connect" message to the Server
  JsonDocument connDoc;
  connDoc["ID"] = DEVICE_ID;
  connDoc["Device_Type"] = "Pico";
  connDoc["Key"] = AUTH_CODE;
  connDoc["Server_Command"] = "Connect";
  
  char connBuffer[256];
  serializeJson(connDoc, connBuffer);
  MQTT::getInstance().publish("Test/Server", 2, false, connBuffer); 

  // ALIGNMENT FIX: Subscribe to Microcontroller/PICO/02
  String myTopic = String(SUB_TOPIC_PREFIX) + String(DEVICE_ID);
  MQTT::getInstance().subscribe(myTopic.c_str(), 2); 
  Serial.print("[MQTT] Subscribed to: ");
  Serial.println(myTopic);
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
  Serial.println("[MQTT] Disconnected from Broker.");
  MQTT::getInstance().startReconnectTimer();
}

void setup() {
  Serial.begin(115200);  
  delay(2000); 

  queue_init(&coreQueue, sizeof(CoreMessage), 10);

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
  lwtDoc["Device_Type"] = "Pico";
  lwtDoc["Key"] = AUTH_CODE;
  lwtDoc["Server_Command"] = "Disconnect";
  char lwtBuffer[256];
  serializeJson(lwtDoc, lwtBuffer);

  // Setup Singleton MQTT Interface
  MQTT& mqtt = MQTT::getInstance();
  mqtt.setup(MQTT_SERVER, MQTT_PORT);
  mqtt.setClientId(DEVICE_ID);
  mqtt.setWill("Test/Server", 2, true, lwtBuffer);
  
  mqtt.onConnect(onMqttConnect);
  mqtt.onDisconnect(onMqttDisconnect);
  mqtt.onMessage(onMqttMessage);

  mqtt.connect();
}

void loop() {
  CoreMessage incomingMsg; 
  
  // Try to grab data from the queue
  if (queue_try_remove(&coreQueue, &incomingMsg)) {
    // debug serial prints
    // Serial.print("[Core 0] Background Data -> Pin: ");
    // Serial.print(incomingMsg.pin);
    // Serial.print(" | Value: ");
    // Serial.println(incomingMsg.sensorValue);
    Serial.println("MQTT Publish Success!");
  } else {
    Serial.println("MQTT Publish Failed.");
  }
  // Core 0 handles other non-blocking network tasks here
  // e.g., checking for incoming socket clients
} // end loop

// CORE 1: Hardware & Sensors

void setup1() {
  // Setup hardware for Core 1 (e.g., I2C sensors, SPI devices)
  // Note: setup1() runs automatically alongside setup()

  // speficty the PIN here. with pwnPin
  // required for saying if a pin is reading or doing something else. 
  // this just basically tells the code HEY WE WANT TO READ OR WRITE ON THESE
  for (int i = 0; i < PIN_COUNT; i++) {
        if (myHardware[i].mode == INPUT_PIN) {
            pinMode(myHardware[i].pin, INPUT);
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

          // using enum instead of function pointers because its a little more clear. Also not a requried sry 😅
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

          queue_try_add(&coreQueue, &newMsg);
          myHardware[i].lastCheck = now;
      }
  }
  delay(1);
}