#include <Arduino.h>
#include <freertos/queue.h> // #include <pico/util/queue.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h" 

// ==========================================
//    ESP cpp
// ==========================================

int readPWM(int pin) {
  // Read the high pulse duration
  highTime = pulseIn(pwmPin, HIGH);
  // Read the low pulse duration
  lowTime = pulseIn(pwmPin, LOW);
  
  period = highTime + lowTime;
  dutyCycle = (highTime / period) * 100;

  // Serial.print("Duty Cycle: ");
  // Serial.print(dutyCycle);
  // Serial.println("%");

  return dutyCycle;
}

// analog pin
int readAnalog(int pin, int ingore) {
  return analogRead(pin);
}

int writeAnalog(int pin, int value){
  return analogWrite(pin, value);
}

int writeDitigal(int pin, int value){
  return digitalWrite(pin, value);
}

int readDitigal(int pin, int ingore){
  return digitalRead(pin, value);
}



// write out 

//  DATA STRUCTURE & QUEUE SETUP
// Define the shape of the data you want to pass between cores
typedef struct {
  int sensorValue;
  int pin;
  unsigned long timestamp;
} CoreMessage;

typedef struct {
  int pin;
  // return_type (*FuncPtr) (parameter type, ....); 
  int (*FuncPtr) (int, int)
  unsigned long function_type;
} pinObject;

// Create the global queue so both cores can access it
queue_t coreQueue;

// MQTT SETUP 
WiFiClient ESBClient;
PubSubClient client(ESBClient);

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

  // Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // setup mqtt
  client.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop() {
  // put your main code here, to run repeatedly:

  // stanity check the MQTT connection
  if (!client.connected()) {
    reconnet();
  }

  client.loop();  // Important: Allows MQTT client to process incoming messages and 
                  // maintain connection
  
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


}


void setup1() {
  // put your setup code here, to run once:
  
  // Setup hardware for Core 1 (e.g., I2C sensors, SPI devices)
  // Note: setup1() runs automatically alongside setup()

  // speficty the PIN here. with pwnPin
  // required for saying if a pin is reading or doing something else. 
  pinMode(pwmPin, INPUT);
  pinMode(pwmPin, INPUT);
  pinMode(pwmPin, INPUT);
  pinMode(pwmPin, INPUT);
}

void loop1() {
  // put your main code here, to run repeatedly:

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

int read(int pin) {
  // Read the high pulse duration
  highTime = pulseIn(pwmPin, HIGH);
  // Read the low pulse duration
  lowTime = pulseIn(pwmPin, LOW);
  
  period = highTime + lowTime;
  dutyCycle = (highTime / period) * 100;

  Serial.print("Duty Cycle: ");
  Serial.print(dutyCycle);
  Serial.println("%");
}

// reading analog
// int sensorValue = analogRead(A0); A0 is pinout. 
// will we see about multiplexing this?
