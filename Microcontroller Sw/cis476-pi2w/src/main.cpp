#include <Arduino.h>
#include <pico/util/queue.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h" 

// ==========================================
//    pico cpp
// ==========================================

//  DATA STRUCTURE & QUEUE SETUP
// Define the shape of the data you want to pass between cores
typedef struct {
  int sensorValue;
  unsigned long timestamp;
} CoreMessage;

// Create the global queue so both cores can access it
queue_t coreQueue;

// MQTT SETUP 
WiFiClient picoClient;
PubSubClient client(picoClient);

void reconnet() {
  // loop until we're reconnected for. Ideally not blockinf core one. 
  while ((!cilent.connect())){
    /* code */
    Serial.print("[Core 0] Attempting MQTT connection...");
    String clientId = "PicoClient-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      serial.println(" trying again");
      delay(5000);
    }
  }
  
}


//  WI-FI CONFIGURATION
// i dont think having this in the main file is the startest way to do this tbh though.
// const char* WIFI_SSID = "YOUR_WIFI_SSID"; 
// const char* WIFI_PASS = "YOUR_WIFI_PASSWORD"; 


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

  client.loop(); // Important: Allows MQTT client to process incoming messages and maintain connection
  
  // Try to grab data from the queue
  if (queue_try_remove(&coreQueue, &incomingMsg)) {
    Serial.print("[Core 0] Data received from Core 1 -> Value: ");
    Serial.print(incomingMsg.sensorValue);
    Serial.print(" | Time: ");
    Serial.println(incomingMsg.timestamp);
    
    // SOCKET PROGRAMMING GOES HERE 
    JsonDocument doc; // https://arduinojson.org/v7/api/
    doc["deviceId"] = "02";
    // doc["authCode"] = "1234"; // todo not hardcode 
    doc["authCode"] = AUTH_CODE;
    doc["sensorValue"] = incomingMsg.sensorValue; // 
    doc["timestamp"] = incomingMsg.timestamp;

    // pack the data from Core 1 into JSON format
    
  }
  
  // Core 0 handles other non-blocking network tasks here
  // e.g., checking for incoming socket clients
}


// CORE 1: Handles Hardware, Sensors, and Heavy Math

void setup1() {
  // Setup hardware for Core 1 (e.g., I2C sensors, SPI devices)
  // Note: setup1() runs automatically alongside setup()
}

void loop1() {
  //  Generate or read data
  CoreMessage newMsg;
  newMsg.sensorValue = random(0, 1024); // Simulating reading an ADC or Sensor
  newMsg.timestamp = millis();

  //  Push data to the queue (non-blocking!)
  if (queue_try_add(&coreQueue, &newMsg)) {
    // Data successfully sent to Core 0
  } else {
    // The queue is full (Core 0 is busy). 
    // You can handle overflow/dropped packets here.
  }

  // Simulate doing work every 2 seconds
  // TODO  remove when working
  delay(2000); 
}