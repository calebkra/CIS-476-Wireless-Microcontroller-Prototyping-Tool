#include <Arduino.h>
#include <pico/util/queue.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h" 

// ==========================================
//    pico cpp
// ==========================================


// helpers for reading the Pinouts. will move to a headerfile later.
int readPWM(int pin){
  // missing defs
  unsigned long highTime;
  unsigned long lowTime;
  unsigned long period;
  float dutyCycle;

  // Read the high pulse duration
  highTime = pulseIn(pin, HIGH);
  // Read the low pulse duration
  lowTime = pulseIn(pin, LOW);
  
  period = highTime + lowTime;
  dutyCycle = ((float)highTime / period) * 100;

  // Serial.print("Duty Cycle: ");
  // Serial.print(dutyCycle);
  // Serial.println("%");

  return (int)dutyCycle;
}

// analog pin
int readAnalog(int pin) {
  return analogRead(pin);
}

void writeAnalog(int pin, int value){
  analogWrite(pin, value);
}

void writeDitigal(int pin, int value){
  digitalWrite(pin, value);
}

int readDitigal(int pin){
  return digitalRead(pin);
}

//  DATA STRUCTURE & QUEUE SETUP
// Define the shape of the data you want to pass between cores
typedef struct {
  int sensorValue;
  int pin;
  unsigned long timestamp;
} CoreMessage;

// for knowing if input or putput.
typedef enum { INPUT_PIN, OUTPUT_PIN } PinMode_t;

typedef struct {
  const char* label;
  int pin;
  PinMode_t mode;

  int (*readFn)(int pin);
  void (*writeFun) (int, int);
  // return_type (*FuncPtr) (parameter type, ....); 

  unsigned long function_type;  // 0 for input 1 for output
  uint32_t interval; 
  uint32_t lastCheck;
  
} PinObject;

// Create the global queue so both cores can access it
queue_t coreQueue;

// MQTT SETUP 
WiFiClient picoClient;
PubSubClient client(picoClient);

void reconnet() {
  // loop until we're reconnected for. Ideally not blockinf core one. 
  while ((!client.connected())){
    /* code */
    Serial.print("[Core 0] Attempting MQTT connection...");
    String clientId = "PicoClient-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again");
      delay(5000);
    }
  }
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

PinObject myHardware[] = {
    // label            pin  mode        readFn      writeFun  func_type  interval  lastCheck
    {"pwm1",            34,  INPUT_PIN,  readAnalog, NULL,     0,         5000,     0}, 
    {"pwm2",            35,  INPUT_PIN,  readAnalog, NULL,     0,         5000,     0}, 
    {"digital input1",  36,  INPUT_PIN,  readDitigal,NULL,     0,         5000,     0}, 
    {"digital input2",  37,  INPUT_PIN,  readDitigal,NULL,     0,         5000,     0}, 
    {"digital output1", 38,  OUTPUT_PIN, NULL,       writeDitigal, 1,     5000,     0}, 
    {"digital output2", 39,  OUTPUT_PIN, NULL,       writeDitigal, 1,     5000,     0}, 
};

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
  // put your main code here, to run repeatedly:

  unsigned long now = millis(); // saves having to look up again

  // Iterate through your hardware array
  for (int i = 0; i < PIN_COUNT; i++) {
      
      // Check if this pin is an INPUT and if it's time to read it
      if (myHardware[i].function_type == 0 && (now - myHardware[i].lastCheck >= myHardware[i].interval)) {
          
          CoreMessage newMsg;
          // Use your function pointer to read the data
          newMsg.sensorValue = myHardware[i].readFn(myHardware[i].pin); 
          newMsg.pin = myHardware[i].pin;
          newMsg.timestamp = now;

          if (queue_try_add(&coreQueue, &newMsg)) {
            // Data successfully sent to Core 0
          } 
          
          // Update the timer
          myHardware[i].lastCheck = now;
      }
  }
  
  // A tiny delay just to prevent Core 1 from locking up the system completely
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