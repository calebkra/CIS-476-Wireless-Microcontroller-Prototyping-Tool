#include <Arduino.h>
#include <pico/util/queue.h>
#include <WiFi.h>
#include <PubSubClient.h> // TODO remove more QoS 2
#include <AsyncMqttClient.h> // the QoS 2
#include <ArduinoJson.h>
#include "secrets.h" 
#include "PicoController.h"

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
  unsigned long timestamp
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

PinObject myHardware[] = {
    // label            pin  mode        signalType   interval  lastCheck
    {"pwm1",            34,  OUTPUT_PIN, SIG_PWM,     5000,     0}, 
    {"pwm2",            35,  OUTPUT_PIN, SIG_PWM,     5000,     0}, 
    {"digital input1",  36,  INPUT_PIN,  SIG_DIGITAL, 5000,     0}, 
    {"digital input2",  37,  INPUT_PIN,  SIG_DIGITAL, 5000,     0}, 
    {"analog sensor",   26,  INPUT_PIN,  SIG_ANALOG,  5000,     0}, // unused analog bonus because I was here already
    {"digital output1", 38,  OUTPUT_PIN, SIG_DIGITAL, 5000,     0}, 
};
// MQTT SETUP 
WiFiClient picoClient;
PubSubClient client(picoClient);

String reconnet() {
  // loop until we're reconnected for. Ideally not blockinf core one. 
  bool gate = true;
  while ((!client.connected())){
    /* code */
    
    Serial.print("[Core 0] Attempting MQTT connection...");
    String clientId = "PicoClient-";
    String IdGuess = String(random(0xffff), HEX);
    clientId += IdGuess;

    // hardcode a "02" first time
    if (gate){
      clientId = String("02");
      gate = true;
    }
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      return IdGuess;
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again");
      delay(5000);
    }
  }
}

void connectToMqtt() {
  Serial.print("[Core 0] Connecting to MQTT...");

  // Prepare the Disconnect/LWT Message
  JsonDocument lwtDoc;
  lwtDoc["ID"] = DEVICE_ID; 
  lwtDoc["Device_Type"] = "Pico";
  lwtDoc["Key"] = AUTH_CODE;
  lwtDoc["Server_Command"] = "Disconnect";
  char lwtBuffer[256];
  serializeJson(lwtDoc, lwtBuffer);

  // Connect with Last Will (Topic, QoS=2, Retain=true, Message)
  if (client.connect(DEVICE_ID, NULL, NULL, "Test/Server", 2, true, lwtBuffer)) {
    Serial.println("connected");

    // Send the mandatory "Connect" message to the Server
    JsonDocument connDoc;
    connDoc["ID"] = DEVICE_ID;
    connDoc["Device_Type"] = "Pico";
    connDoc["Key"] = AUTH_CODE;
    connDoc["Server_Command"] = "Connect";
    
    char connBuffer[256];
    serializeJson(connDoc, connBuffer);
    client.publish("Test/Server", connBuffer, 2); // Must be QoS 2 

    // Subscribe to the dedicated Pico topic
    // The server builds this as: Microcontroller/PICO/{ID}
    String myTopic = String(PubTopic) + String(DEVICE_ID);
    client.subscribe(myTopic.c_str(), 2); 
  }
}

void sendAllStates() {
  JsonDocument doc;
  doc["ID"] = DEVICE_ID;
  doc["Device_Type"] = "Pico";
  doc["Key"] = AUTH_CODE;
  doc["Server_Command"] = "Send_Message";
  doc["Client_Command"] = "Recieve State"; // Spelling matches classes.py logic

  JsonObject message = doc.createNestedObject("Message");
  
  // Loop through hardware and add each pin value to the JSON
  for (int i = 0; i < PIN_COUNT; i++) {
    int val = 0;
    if (myHardware[i].function_type == 0) { // INPUT
      val = myHardware[i].readFn(myHardware[i].pin);
    } else {
      // For outputs, we'd ideally track the last set state 
      // For now, we'll read the digital state or pulse state
      val = digitalRead(myHardware[i].pin); 
    }
    message[myHardware[i].label] = val;
  }

  char buffer[512];
  serializeJson(doc, buffer);
  client.publish("Test/Server", buffer, 2); // QoS 2
}
// CORE 0: Handles Wi-Fi and MQTT

void setup() {
  Serial.begin(115200);  // bestest baugh rate. 
  delay(2000); // Giving the serial monitor a moment to connect

  // Initialize the queue: (pointer to queue, size of one item, max items)
  queue_init(&coreQueue, sizeof(CoreMessage), 10);

  // Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWi-Fi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // setup mqtt
  client.setServer(MQTT_SERVER, MQTT_PORT);
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
    JsonDocument doc;
    deserializeJson(doc, payload);

    String command = doc["Client_Command"];

    if (command == "Get State") {
        // Respond with all pin states
        sendAllStates();
    } 
    else if (command == "Set State") {
        // Extract pin and value, then update hardware
        int targetPin = doc["Message"]["Pin"];
        int value = doc["Message"]["Value"];
        updateHardware(targetPin, value); // when did this make it here 😭😭
        sendAllStates(); // Respond with updated state
    }
}



void loop() {
  // stanity check the MQTT connection
  if (!client.connected()) {
    reconnet();
  }

  client.loop();  // Important: Allows MQTT client to process incoming messages 
                  //and maintain connection
  
  CoreMessage incomingMsg; 
  // Try to grab data from the queue
  if (queue_try_remove(&coreQueue, &incomingMsg)) {
    Serial.print("[Core 0] Data received from Core 1 -> Value: ");
    Serial.print(incomingMsg.sensorValue);
    Serial.print(" | Time: ");
    Serial.println(incomingMsg.timestamp);
    
    // pack the data from Core 1 into JSON format
    JsonDocument doc; // https://arduinojson.org/v7/api/
    doc["deviceId"] = "02";
    // doc["authCode"] = "1234"; // todo not hardcode 
    doc["authCode"] = AUTH_CODE;
    doc["sensorValue"] = incomingMsg.sensorValue; // 
    doc["timestamp"] = incomingMsg.timestamp;

    // actually publich the message
    char jsonBuffer[256]; // Create a temporary text buffer
    serializeJson(doc, jsonBuffer); // Turn the JSON object into text
    
    // Publish to a topic (e.g., "pico/sensors")
    // TODO CHANGES THE TOPICS
    if(client.publish("pico/sensors", jsonBuffer)) {
        Serial.println("MQTT Publish Success!");
    } else {
        Serial.println("MQTT Publish Failed.");
    }
    
  }
  


  // Core 0 handles other non-blocking network tasks here
  // e.g., checking for incoming socket clients
} // end loop


// CORE 1: Handles Hardware, Sensors, and Heavy Math

// Calculate how many pins are in the array automatically
const int PIN_COUNT = sizeof(myHardware) / sizeof(PinObject);

void setup1() {
  // Setup hardware for Core 1 (e.g., I2C sensors, SPI devices)
  // Note: setup1() runs automatically alongside setup()

  // speficty the PIN here. with pwnPin
  // required for saying if a pin is reading or doing something else. 
  // this just basically tells the code HEY WE WANT TO READ OR WRITE ON THESE
  for (int i = 0; i < PIN_COUNT; i++) {
        if (myHardware[i].function_type == 0) {
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
/*
  //  Push data to the queue (non-blocking!)
  if (queue_try_add(&coreQueue, &newMsg)) {
    // Data successfully sent to Core 0
  } else {
    // The queue is full (Core 0 is busy). 
    // You can handle overflow/dropped packets here.
  }
*/
}