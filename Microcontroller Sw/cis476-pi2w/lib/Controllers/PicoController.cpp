// PicoController.cpp
#include "PicoController.h"

void PicoController::writeDigital(int pin, int value) {
    digitalWrite(pin, value);
}

int PicoController::readPWM(int pin){
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

// helpers for reading the Pinouts. will move to a headerfile later.
void PicoController::writePWM(int pin, float value){
  // note that analogWrite() only works for pins somethimes idk
  // TODO fix that please
  analogWrite(pin, value);
}

// analog pin
int PicoController::readAnalog(int pin) {
  return analogRead(pin);
}

void PicoController::writeAnalog(int pin, int value){
  analogWrite(pin, value);
}

int PicoController::readDigital(int pin){
  return digitalRead(pin);
}
