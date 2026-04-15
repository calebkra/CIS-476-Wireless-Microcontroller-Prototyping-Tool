// PicoController.h
#pragma once
#include <Arduino.h>
#include "IController.h"

class PicoController : public IController {
private:
    // array for all pins to store last state, This is too send all states without
    // locking having to poll the other cores. 
    int _lastState[30] = {0}; 

public:
    int readPWM(int pin) override;
    void writePWM(int pin, float value) override;
    int readAnalog(int pin) override;
    void writeAnalog(int pin, int value) override;
    void writeDigital(int pin, int value) override;
    int readDigital(int pin) override;
};