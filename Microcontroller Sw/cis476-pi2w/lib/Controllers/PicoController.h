// PicoController.h
#pragma once
#include <Arduino.h>
#include "IController.h"

class PicoController : public IController {
public:
    int readPWM(int pin) override;
    void writePWM(int pin, float value) override;
    int readAnalog(int pin) override;
    void writeAnalog(int pin, int value) override;
    void writeDigital(int pin, int value) override;
    int readDigital(int pin) override;
};