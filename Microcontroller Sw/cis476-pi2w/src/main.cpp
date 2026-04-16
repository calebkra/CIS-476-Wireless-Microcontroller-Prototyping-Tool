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

void sendAllStates(); // Prototype for function used in setup() and onMqttMessage()
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
queue_t coreQueue;

// Updated labels to explicitly match the rubric requirement: 
// {"DO1":(value), "DO2": (value), "DI1": (value), "DI2": (value), "PWM1": (value), "PWM2":(value)}
// this was chat's Idea after a code review idk why. 
PinObject myHardware[] = {
    {"PWM1",  8,  OUTPUT_PIN, SIG_PWM,     5000, 0}, 
    {"PWM2",  9,  OUTPUT_PIN, SIG_PWM,     5000, 0}, 
    {"DI1",   36,  INPUT_PIN,  SIG_DIGITAL, 5000, 0}, 
    {"DI2",   37,  INPUT_PIN,  SIG_DIGITAL, 5000, 0}, 
    {"DO1",   6,  OUTPUT_PIN, SIG_DIGITAL, 5000, 0},
    {"DO2",   7,  OUTPUT_PIN, SIG_DIGITAL, 5000, 0} // Added to match rubric
};

// Calculate how many pins are in the array automatically
const int PIN_COUNT = sizeof(myHardware) / sizeof(PinObject);

void setup() {
  Serial.begin(115200);  
  delay(2000); 

  queue_init(&coreQueue, sizeof(CoreMessage), 10);

  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Wi-Fi IP: ");
Serial.println(WiFi.localIP());
Serial.print("Gateway: ");
Serial.println(WiFi.gatewayIP());
Serial.print("DNS: ");
Serial.println(WiFi.dnsIP());

// Test broker resolution
IPAddress brokerIP;
if (WiFi.hostByName(MQTT_SERVER, brokerIP)) {
  Serial.print("Broker IP: ");
  Serial.println(brokerIP);
} else {
  Serial.println("DNS lookup failed for MQTT_SERVER");
}

// Test raw TCP connection
WiFiClient test;
Serial.print("Testing TCP to ");
Serial.print(MQTT_SERVER);
Serial.print(":");
Serial.print(MQTT_PORT);
Serial.print(" ... ");
if (test.connect(MQTT_SERVER, MQTT_PORT)) {
  Serial.println("SUCCESS");
  test.stop();
} else {
  Serial.println("FAILED");
}
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
  mqtt.setWill("Test/Server", 2, false, lwtBuffer);
  
  mqtt.onConnect(onMqttConnect);
  mqtt.onDisconnect(onMqttDisconnect);
  mqtt.onMessage(onMqttMessage);

  mqtt.connect();
}

void loop() {
  // Keep MQTT alive
  MQTT::getInstance().loop();

  CoreMessage incomingMsg; 
    if (queue_try_remove(&coreQueue, &incomingMsg)) {
      sendAllStates();
      delay(1000);
    }

  } // end loop

// CORE 1: Hardware & Sensors SETUP
void setup1() {
  // Setup hardware for Core 1 (e.g., I2C sensors, SPI devices)
  // Note: setup1() runs automatically alongside setup()

  // speficty the PIN here. with pwnPin
  // required for saying if a pin is reading or doing something else. 
  // this just basically tells the code HEY WE WANT TO READ OR WRITE ON THESE
  for (int i = 0; i < PIN_COUNT; i++) {
        if (myHardware[i].mode == INPUT_PIN) {
            pinMode(myHardware[i].pin, INPUT_PULLUP);
        } else {
            pinMode(myHardware[i].pin, OUTPUT_12MA);
        }
    }
}

// CORE 1: Hardware & Sensors LOOP
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


// UTILITY / CALLBACK FUNCTIONS

/**
 * @brief Sends the current state of all hardware pins to the MQTT server.
 */
void sendAllStates() {
    JsonDocument doc;
    doc["ID"] = DEVICE_ID;
    doc["Device_Type"] = "Pico";
    doc["Key"] = AUTH_CODE;
    doc["Server_Command"] = "Send_Message";
    doc["Client_Command"] = "Receive State";

    JsonObject message = doc["Message"].to<JsonObject>();
    
    for (int i = 0; i < PIN_COUNT; i++) {
      int val = 0;
      if (myHardware[i].mode == INPUT_PIN) {
        // use the pico controller. 
        val = myBoard->readDigital(myHardware[i].pin);
      } else if (myHardware[i].signalType == SIG_PWM) {
        val = myBoard->readPWM(myHardware[i].pin);
      } else {
        val = digitalRead(myHardware[i].pin);
      }
      message[myHardware[i].label] = val;
    }

    char buffer[512];
    serializeJson(doc, buffer);
    
    MQTT::getInstance().publish("Test/Server", 2, false, buffer);
    Serial.print("sent meesage\n");
}
/**
 * @brief Handles incoming MQTT messages from the server.
 * Determines if the command is a "Get State" or "Set State".
 */
void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total) {
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
  } else if (command == "Set State") {
  // const char* targetPinLabel = doc["Message"]["Pin"]; 
  // int value = doc["Message"]["Value"];
  String targetPinLabel;
  String valueString;
  JsonObject msg = doc["Message"].as<JsonObject>();
  for (JsonPair kv : msg) {
    const char* pinChar = kv.key().c_str();
    const char* valueChar = kv.value().as<const char*>();

    targetPinLabel = String(pinChar);
    valueString = String(valueChar);
  }

  int value;

  if(valueString == "HIGH"){
    value = 1;
  }
  else if (valueString == "LOW"){
    value = 0;
  } else{
    value = valueString.toInt();
  }
  // Find the pin by label and update it
  for(int i=0; i<PIN_COUNT; i++) {
    if(String(myHardware[i].label) == targetPinLabel) {
      if(myHardware[i].signalType == SIG_PWM) {
        myBoard->writePWM(myHardware[i].pin, (float)value);
      } else {
        myBoard->writeDigital(myHardware[i].pin, value);
      }
      break;
    }
  }
  sendAllStates(); 
  }
}

/**
 * @brief Callback executed upon successful MQTT connection.
 * Publishes a 'Connect' message and subscribes to the device topic.
 */
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

/**
 * @brief Callback executed when MQTT disconnection is detected.
 * Restarts the reconnection timer.
 */
void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
  Serial.println("[MQTT] Disconnected from Broker.");
  MQTT::getInstance().startReconnectTimer();
}

