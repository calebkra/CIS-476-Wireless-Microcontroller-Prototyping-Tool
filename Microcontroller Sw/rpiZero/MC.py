import paho.mqtt.client as mqtt
import json
from abc import ABC, abstractmethod
import pigpio

#Singleton class, however different from normal implimentation since python does not support private constructors
class ConnectionHandler: 
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, initial_value=None):
        if not hasattr(self, '_initialized'):
            self.value = initial_value
            self._initialized = True 
            self.ServerTopic = "Test/Server"
            self.Connected = False
            self.MCID = None
            self.MCType = "RpiZero"

    def connect(self,server_ip,port,server_key,mc_id):
        self.SelfTopic = f"Microcontroller/{mc_id}"
        self.Server_Key = server_key
        self.MCID = mc_id
        self.client = mqtt.Client()
        self.client.on_message = self.__on_message
        self.client.will_set("Test/Server",json.dumps({"ID":mc_id,"Key":server_key,"Device_Type":self.MCType,"Server_Command":"Disconnect"}),qos=2)
        self.client.connect(server_ip, port)
        self.client.subscribe(self.SelfTopic,qos=2)
        self.client.loop_start()
        #need to send connect message here
        self.client.publish(self.ServerTopic,json.dumps({"ID":f"{self.MCID}","Device_Type":self.MCType,"Key":f"{self.Server_Key}","Server_Command":"Connect"}),qos=2)

    def sendMessage(self,msg):
        #finish send messages
        header = {"ID":f"{self.MCID}","Key":f"{self.Server_Key}","Device_Type":self.MCType}
        finalmsg = header | msg 
        self.client.publish(self.ServerTopic,json.dumps(finalmsg),qos=2)
        
    def isConnected(self):
        return self.Connected
    
    def __on_message(self,client, userdata, msg):
        msgJson = json.loads(msg.payload.decode('utf-8'))
        if msgJson["Client_Command"] == "Connection Success":
            self.Connected = True
        if msgJson["Client_Command"] == "Set State":
            msg = msgJson["Message"]
            self.CurrentMC.setStates(msg)
        if msgJson["Client_Command"] == "Get State":
            self.CurrentMC.sendStates()

    def setActiveMC(self,currMC):
        self.CurrentMC = currMC

class microcontroller:
    def __init__(self,connHandler):
        self.pi = pigpio.pi()
        
        self.ConnectionHandler = connHandler
        self.ConnectionHandler.setActiveMC(self)
        self.DigIn1PIN = 23
        self.DigIn2PIN = 24
        self.DigOut1PIN = 5
        self.DigOut2PIN = 6
        self.PWM1PIN =12
        self.PWM2PIN =13
        self.PWMFreq = 50

        self.DigIn1State = "LOW"
        self.DigIn2State= "LOW"
        self.DigOut1State = None
        self.DigOut2State = None
        self.PWM1Duty = 0
        self.PWM2Duty = 0

        self.pi.set_mode(self.DigIn1PIN,pigpio.INPUT)
        self.pi.set_pull_up_down(self.DigIn1PIN,pigpio.PUD_DOWN)
        self.pi.cb1= self.pi.callback(self.DigIn1PIN,pigpio.EITHER_EDGE,self.inputCallback)
        self.pi.set_mode(self.DigIn2PIN,pigpio.INPUT)
        self.pi.set_pull_up_down(self.DigIn2PIN,pigpio.PUD_DOWN)
        self.pi.cb2= self.pi.callback(self.DigIn2PIN,pigpio.EITHER_EDGE,self.inputCallback)
        self.pi.set_mode(self.DigOut1PIN,pigpio.OUTPUT)
        self.pi.set_mode(self.DigOut2PIN,pigpio.OUTPUT)
        self.pi.hardware_PWM(self.PWM1PIN,self.PWMFreq,self.PWM1Duty)
        self.pi.hardware_PWM(self.PWM2PIN,self.PWMFreq,self.PWM2Duty)

        if self.pi.read(self.DigIn1PIN) == 1:
            self.DigIn1State = "HIGH"
        else:
            self.DigIn1State = "LOW"
        
        if self.pi.read(self.DigIn2PIN) == 1:
            self.DigIn2State = "HIGH"
        else:
            self.DigIn2State = "LOW"

        self.sendStates()



    def inputCallback(self,gpioPin,level,timeTick):
        if level == 1:
            if gpioPin == self.DigIn1PIN:
                self.DigIn1State = "HIGH"
                self.sendStates()
            if gpioPin == self.DigIn2PIN:
                self.DigIn2State = "HIGH"
                self.sendStates()
        if level == 0:
            if gpioPin == self.DigIn1PIN:
                self.DigIn1State = "LOW"
                self.sendStates()
            if gpioPin == self.DigIn2PIN:
                self.DigIn2State = "LOW"
                self.sendStates()

    def sendStates(self):
        states = {"DI1":self.DigIn1State, "DI2":self.DigIn2State, "DO1":self.DigOut1State, "DO2":self.DigOut2State, "PWM1":self.PWM1Duty, "PWM2":self.PWM2Duty}
        self.ConnectionHandler.sendMessage({"Client_Command":"Recieve State", "Message":states})

    def setStates(self,msg):
        DO1 = msg.get("DO1",None)
        DO2 = msg.get("DO2",None)
        PWM1 = msg.get("PWM1",None)
        PWM2 = msg.get("PWM2",None)

        if DO1 is not None:
            self.setDigitalOutput1(DO1)

        if DO2 is not None:
            self.setDigitalOutput2(DO2)

        if PWM1 is not None:
            self.setDigitalOutput1(PWM1)

        if PWM2 is not None:
            self.setDigitalOutput1(PWM2)



    def setPWM1DutyCycle(self,dutyValue):
        self.PWM1Duty = dutyValue
        self.pi.hardware_PWM(self.PWM1PIN,self.PWMFreq,dutyValue*10000)

    def setPWM2DutyCycle(self,dutyValue):
        self.PWM1Duty = dutyValue
        self.pi.hardware_PWM(self.PWM2PIN,self.PWMFreq,dutyValue*10000)

    def setPWMFrequency(self, freq):
        self.PWMFreq = freq
        self.setPWM1DutyCycle(self.PWM1Duty)
        self.setPWM2DutyCycle(self.PWM2Duty)

    def setDigitalOutput1(self,value):
        self.DigOut1State = value
        if value == "HIGH":
            binaryValue = 1
        elif value == "LOW":
            binaryValue = 0

        self.pi.write(self.DigIn1PIN,binaryValue)

    def setDigitalOutput2(self,value):
        self.DigOut2State = value
        if value == "HIGH":
            binaryValue = 1
        elif value == "LOW":
            binaryValue = 0

        self.pi.write(self.DigIn2PIN,binaryValue)
        