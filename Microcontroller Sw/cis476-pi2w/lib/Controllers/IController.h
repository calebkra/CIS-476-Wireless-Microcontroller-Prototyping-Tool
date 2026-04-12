#pragma once

class IController {
public:
    virtual ~IController() = default;
    
    virtual int readPWM(int pin) = 0;
    virtual void writePWM(int pin, float value) = 0;
    virtual int readAnalog(int pin) = 0;
    virtual void writeAnalog(int pin, int value) = 0;
    virtual void writeDigital(int pin, int value) = 0;
    virtual int readDigital(int pin) = 0;
};