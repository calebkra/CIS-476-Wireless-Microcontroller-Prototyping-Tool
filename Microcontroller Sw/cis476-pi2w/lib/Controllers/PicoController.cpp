// PicoController.cpp
#include "PicoController.h"

void PicoController::writeDigital(int pin, int value) {
    digitalWrite(pin, value);
    _lastState[pin] = value;
}

int PicoController::readDigital(int pin){
    return digitalRead(pin);
}

void PicoController::writePWM(int pin, float value){
    analogWrite(pin, (int)value);
    _lastState[pin] = (int)value;
}

int PicoController::readPWM(int pin){
    return _lastState[pin];
}

int PicoController::readAnalog(int pin) {
    return analogRead(pin);
}

void PicoController::writeAnalog(int pin, int value){
    analogWrite(pin, value);
    _lastState[pin] = value;
}