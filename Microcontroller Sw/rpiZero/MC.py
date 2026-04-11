import paho.mqtt.client as mqtt
import json
from abc import ABC, abstractmethod
import pigpio

#Constants
SERVER_IP = '192.168.8.101'
PORT = 1883
SERVER_KEY = "1234"
MICROCONTROLLER_ID = "M001"
MICROCONTROLLER_TYPE = "RpiZero"
SERVER_TOPIC = "Test/Server"


#Singleton and Proxy pattern
#This proxy class will handle message authentication, fowarding authenticated messages to the connection class object, sends error message if key is incorrect
class authenticationProxy:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'inst'):
            cls.inst = super().__new__(cls)
            return cls.inst

    #initializes the class object
    def initialize(self,conn):
        self.ConnectionHandler = conn 
        self.ConnectionHandler.setOnMessage(self.on_message)

    #on_message handler for mqtt client that will authenticate messages and act accordingly
    def on_message(self,client, userdata, msg):
        Message = json.loads(msg.payload.decode('utf-8'))

        client_command = Message.get("Client_Command", None)
        if client_command and client_command == "Invalid Key":
            print("Invalid Server Key")
            return

        id = Message.get("ID",None)

        if id and id == "Server":
            key = Message.get("Key",None)
            if key:
                self.setKey(key)

        attemptedKey = Message.get("Key")

        if attemptedKey and self.Key and attemptedKey == self.Key:
            self.ConnectionHandler.on_message(client,userdata,msg)
        
    #sets the server key
    def setKey(self, key):
        self.Key = key    


#Singleton class, however different from normal implimentation since python does not support private constructors
#handles the mqtt client and communication with the mqtt broker
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
            self.ServerTopic = SERVER_TOPIC
            self.Connected = False
            self.MCID = None
            self.MCType = MICROCONTROLLER_TYPE
            self.proxyOnMessage = None

    #connects with the mqtt broker with the passed in parameters
    def connect(self,server_ip,port,server_key,mc_id):
        self.SelfTopic = f"Microcontroller/RPIZERO/{mc_id}"
        self.Server_Key = server_key
        self.MCID = mc_id
        self.client = mqtt.Client()
        self.client.on_message = self.proxyOnMessage
        self.client.will_set(self.ServerTopic,json.dumps({"ID":mc_id,"Key":server_key,"Device_Type":self.MCType,"Server_Command":"Disconnect"}),qos=2)
        self.client.connect(server_ip, port)
        self.client.subscribe(self.SelfTopic,qos=2)
        self.client.loop_start()
        #need to send connect message here
        self.client.publish(self.ServerTopic,json.dumps({"ID":f"{self.MCID}","Device_Type":self.MCType,"Key":f"{self.Server_Key}","Server_Command":"Connect"}),qos=2)

    #sends message to the mqtt broker to the server topic
    def sendMessage(self,msg):
        #finish send messages
        header = {"ID":f"{self.MCID}","Key":f"{self.Server_Key}","Device_Type":self.MCType}
        finalmsg = header | msg 
        self.client.publish(self.ServerTopic,json.dumps(finalmsg),qos=2)

    #returns true if the GUI is successfully connected to server
    #returns false if the GUI is not connected to the server 
    def isConnected(self):
        return self.Connected
    
    #on_message handler for the mqtt client, handles acting on incoming messages
    def on_message(self,client, userdata, msg):
        msgJson = json.loads(msg.payload.decode('utf-8'))
        clientCommand = msgJson.get("Client_Command",None)
        print(f"Client_Command:{clientCommand}")
        if clientCommand == "Connection Success":
            self.Connected = True
        if clientCommand == "Set State":
            print("Set State Reached")
            msg = msgJson.get("Message")
            self.CurrentMC.setStates(msg)
        if clientCommand == "Get State":
            self.CurrentMC.sendStates()
            print("Get State Reached")
            
    #sets the current MC in the connection class so on_message can manipulate the microcontroller
    def setActiveMC(self,currMC):
        self.CurrentMC = currMC

    #sets the proxy on_message handler so the connection class can setup the mqtt client
    def setOnMessage(self,onmsg):
        self.proxyOnMessage = onmsg

#microcontroller class, handles all manipulation of IO pins and devices
class microcontroller:
    #initialize the class, defining which pins will be used and how they can be accessed
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
        self.DigOut1State = "LOW"
        self.DigOut2State = "LOW"
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


    #handles call back for rising/falling edge of digital input pins, allows class to act when state changes
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

    #sends current state of all pins to the server to be forwarded to the binded microcontrollers
    def sendStates(self):
        states = {"DI1":self.DigIn1State, "DI2":self.DigIn2State, "DO1":self.DigOut1State, "DO2":self.DigOut2State, "PWM1":self.PWM1Duty, "PWM2":self.PWM2Duty}
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Client_Command":"Recieve State", "Message":states})

    #sets the state of the output pins based on the message recieved
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
            self.setPWM1DutyCycle(PWM1)

        if PWM2 is not None:
            self.setPWM2DutyCycle(PWM2)



    #sets the duty cycles for PWM 1
    def setPWM1DutyCycle(self,dutyValue):
        self.PWM1Duty = dutyValue
        self.pi.hardware_PWM(self.PWM1PIN,self.PWMFreq,dutyValue*10000)

    #sets the duty cycles for PWM 2
    def setPWM2DutyCycle(self,dutyValue):
        self.PWM2Duty = dutyValue
        self.pi.hardware_PWM(self.PWM2PIN,self.PWMFreq,dutyValue*10000)

    #sets the PWM frequency for the both PWM 1 and 2
    def setPWMFrequency(self, freq):
        self.PWMFreq = freq
        self.setPWM1DutyCycle(self.PWM1Duty)
        self.setPWM2DutyCycle(self.PWM2Duty)

    #sets the state of Digital Output 1
    def setDigitalOutput1(self,value):
        self.DigOut1State = value
        if value == "HIGH":
            binaryValue = 1
        elif value == "LOW":
            binaryValue = 0

        self.pi.write(self.DigOut1PIN,binaryValue)

    #sets the state of Digital Output 2
    def setDigitalOutput2(self,value):
        self.DigOut2State = value
        if value == "HIGH":
            binaryValue = 1
        elif value == "LOW":
            binaryValue = 0

        self.pi.write(self.DigOut2PIN,binaryValue)

#Factory pattern
#creates instances of the microcontroller class
class mcFactory:
   def __init__(self, conn):
       self.ConnectionHandler = conn
   def createMC(self):
       return microcontroller(connHandler=self.ConnectionHandler)




#instantiate and intialize the connection and proxy classes 
conn = ConnectionHandler()
proxy = authenticationProxy()
proxy.initialize(conn=conn)

#connect to the mqtt broker and the server
conn.connect(SERVER_IP,PORT,SERVER_KEY,MICROCONTROLLER_ID)

#Instaniate and initalize the microcontroller factory
McFactory = mcFactory(conn)

#create a microcontroller instance
MC = McFactory.createMC()

while True:
    pass