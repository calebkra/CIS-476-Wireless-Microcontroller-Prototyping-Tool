#include <Arduino.h>
#include <freertos/queue.h> // #include <pico/util/queue.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h" 

// ==========================================
//    ESP cpp
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
    String clientId = "Esp32_Cleint-";
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

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);  // bestest baugh rate. 
  delay(2000); // Giving the serial monitor a moment to connect

  // Initialize the queue: (pointer to queue, size of one item, max items)
  queue_init(&coreQueue, sizeof(CoreMessage), 10);


}

void loop() {
  // put your main code here, to run repeatedly:
}


void setup1() {
  // put your setup code here, to run once:
  int result = myFunction(2, 3);
}

void loop1() {
  // put your main code here, to run repeatedly:
}


// put function definitions here:
int myFunction(int x, int y) {
  return x + y;
}