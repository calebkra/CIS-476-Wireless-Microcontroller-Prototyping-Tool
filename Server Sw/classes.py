from queue import Queue
from abc import ABC, abstractmethod
import json

#Singleton pattern
#connection class to handle messages
class Connection:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'inst'):
            cls.inst = super().__new__(cls)
            return cls.inst
    
    def initialize(self,MqttClient):
        self.MqttConnection = MqttClient
    
    #queue to hold incomimg messages in order
    MessageList = Queue()

    #places message into the queue 
    def recieveMessage(self,msg):
        self.MessageList.put(msg)
    
    #returns the first message in the queue if it exists
    def getMessage(self):
        if not self.MessageList.empty():
            return self.MessageList.get()
        else:
            return None

    #sends given message to the given topic
    def sendMessage(self,topic,message):
        self.MqttConnection.publish(topic,message,qos=2)


#Proxy and Singleton Pattern
#Authenticates incoming messages and forwards them to the connection class upon successful authentication
class connProxy:
     
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'inst'):
            cls.inst = super().__new__(cls)
            return cls.inst
    #initializes the proxy class
    def initialize(self,key,conn):
        self.AuthKey=key
        self.Connection = conn
        
    #handles the authentication of incoming messages, forwards them to connection on message handler if authenticated, sends failure message if wrong key
    def authenticate(self,msg):
        submittedKey = msg.get("Key")
        if submittedKey == self.AuthKey:
            self.Connection.recieveMessage(msg)
        else:
            id = msg.get("ID")
            device_type = msg.get("Device_Type")
            if device_type == "GUI":
                topic = f"GUI/{id}"
            else:
                topic = f"Microcontroller/{device_type.upper()}/{id}"

            self.Connection.sendMessage(topic,json.dumps({"ID":"Server","Key":self.AuthKey,"Client_Command":"Invalid Key"}))
            print("Wrong Authentication Code")

#abstract microcontroller class to act as abstract object of abstract factory 
class AbstractMicrocontroller(ABC):
    @abstractmethod
    def sendMsg(self,msg):
        pass

#concrete microcontroller class for the ESP32
class ESP32(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
        self.Device_Type = "ESP32"
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/ESP32/{self.ID}"
        self.Connection.sendMessage(topic,msg)

#concrete microcontroller class for the Raspberry Pi Pico
class Pico(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
        self.Device_Type = "Pico"
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/PICO/{self.ID}"
        self.Connection.sendMessage(topic,msg)

#concrete microcontroller class for the Raspberry Pi Zero
class RpiZero(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
        self.Device_Type = "RpiZero"
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/RPIZERO/{self.ID}"
        self.Connection.sendMessage(topic,msg)
        

#abstract factory for creating microcontroller instances
class AbstractMicrocontrollerFactory(ABC):
    @abstractmethod
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        pass

#concrete factory for ESP32
class Esp32Factory(AbstractMicrocontrollerFactory):
    def __init__(self, conn):
        self.Connection = conn
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        return ESP32(self.Connection,id)

#concrete factory for Raspberry Pi Pico
class PicoFactory(AbstractMicrocontrollerFactory):
    def __init__(self, conn):
        self.Connection = conn
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        return Pico(self.Connection,id)

#concrete factory for Raspberry Pi Zero    
class RpiZeroFactory(AbstractMicrocontrollerFactory):
    def __init__(self, conn):
        self.Connection = conn
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        return RpiZero(self.Connection,id)

#Factory Pattern
#Factory to create GUI instance representations
class GUIFactory:
    def __init__(self,conn):
        self.Connection = conn
        
    def createGUI(self,id):
        return GUI(self.Connection,id)

#GUI class is the GUI representation that the GUI factory creates    
class GUI:
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
    
    def sendMsg(self,msg):
        topic = f"GUI/{self.ID}"
        self.Connection.sendMessage(topic,msg)    


#Mediator Pattern
#This mediator class handles most of the logic of the server, it is resposible for coordinating communication between the GUI and the MCs
class Mediator:
    #list of currently connected microcontrollers
    microcontrollerList = list()

    #list of currently connected GUIs
    GUIList = list()

    #Dictionary of lists of GUIs that are binded to Microcontrollers
    microcontrollerGUIMapping = {}
    
    def __init__(self,conn,factoryDict):
        self.Connection = conn
        self.Factories = factoryDict

    #This method is where mediation occurs, it will maintain the lists of currently connected devices, handle communication between GUIs and MCs
    def startMediation(self):
        while True:
            #gets next message from message queue
            currentMessage= self.Connection.getMessage()
            if currentMessage == None :
                continue
            
            serverCommand = currentMessage.get("Server_Command",None)
            deviceType = currentMessage.get("Device_Type",None)

            if serverCommand == "Connect" :
               #This block handles devices connecting to the server, it adds them to their respective lists so the server knows they are there
               #It creates objects to track these devices and send messages to them

                if deviceType == "GUI":
                    factoryGUI = self.Factories["GUI"]
                    GUIID = currentMessage.get("ID",None)
                    GUIinstance = factoryGUI.createGUI(GUIID)
                    self.GUIList.append(GUIinstance)
                    GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Connection Success"}))

                if deviceType == "ESP32" or deviceType == "Pico" or deviceType == "RpiZero":
                    if deviceType == "ESP32":
                        factoryMicrocontroller = self.Factories["ESP32"] 
                    if deviceType == "Pico":
                        factoryMicrocontroller = self.Factories["Pico"]
                    if deviceType == "RpiZero":
                        factoryMicrocontroller = self.Factories["RpiZero"]
                    
                    MCID = currentMessage.get("ID",None)
                    microcontrollerInstance = factoryMicrocontroller.createMicrocontroller(MCID)
                    self.microcontrollerList.append(microcontrollerInstance)
                    microcontrollerInstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Connection Success"}))
            
            if serverCommand == "Bind" and deviceType == "GUI":
                #this block handles binding GUIs to MCs, so when MCs send messages all binded GUIs recieve that message
                #additionally it allows the server to know where to send messages to that are sent from the GUI
                
                GUIID = currentMessage.get("ID",None)
                MCID = currentMessage.get("Message",None)
                #find GUI instance first
                for GUIinst in self.GUIList:
                    GUIinstance = GUIinst
                    if GUIinst.ID == GUIID:
                        break
                    else:
                        GUIinstance = None
                
                if GUIinstance != None:
                    #find microcontroller instance
                    for microcontrollerInst in self.microcontrollerList:
                        microcontrollerInstance = microcontrollerInst
                        if microcontrollerInst.ID == MCID:
                            break
                        else:
                            GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Bind Unsuccessful"}))
                            microcontrollerInstance = None
                
                if microcontrollerInstance != None:
                    currGUIMapList = self.microcontrollerGUIMapping.get(f"{microcontrollerInstance.ID}",None)
                    if currGUIMapList == None :
                        tempList = list()
                        tempList.append(GUIinstance.ID)
                        self.microcontrollerGUIMapping.update({f"{microcontrollerInstance.ID}":tempList}) 
                        GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Bind Successful"}))
                    else:
                        currGUIMapList.append(GUIinstance.ID)
                        self.microcontrollerGUIMapping.update({f"{microcontrollerInstance.ID}":currGUIMapList})
                        GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Bind Successful"}))
                    print(self.microcontrollerGUIMapping)
               
            if serverCommand == "Disconnect":
                #this block handles when a device disconnects from the server, it will remove the device from the respective lists and bindings
                #additonally it will notify the binded devices if necessary
                
                if deviceType == "GUI":
                    GUIID = currentMessage.get("ID",None)
                    keyList = [key for key, val in self.microcontrollerGUIMapping.items() if GUIID in val]

                    for key in keyList:
                        currList = self.microcontrollerGUIMapping[key]
                        currList.remove(GUIID)
                        if not currList:
                            self.microcontrollerGUIMapping.pop(key,None)
                        else:
                            self.microcontrollerGUIMapping[key]=currList

                if deviceType == "ESP32" or deviceType == "Pico" or deviceType == "RpiZero":
                    MCID = currentMessage.get("ID",None)
                    currList = self.microcontrollerGUIMapping.get(f"{MCID}")
                    if currList:
                        for GUIid in currList:
                            for gui in self.GUIList:
                                if gui.ID == GUIid:
                                    gui.sendMsg(json.dumps({"ID":"Server","Key":"1234", "Client_Command":"Microcontroller_Disconnect"}))
                    
                        self.microcontrollerGUIMapping.pop(MCID)
            
            if serverCommand == "Send_Message":
                #This block handles sending messages from one device to another, using the receiver ID and/or the bindings

                if deviceType == "GUI":
                    for microcontroller in self.microcontrollerList:
                        RID = currentMessage.get("Reciever_ID",None)
                        if microcontroller.ID == RID:
                            microcontroller.sendMsg(json.dumps(currentMessage))
                if deviceType == "ESP32" or deviceType == "Pico" or deviceType == "RpiZero":
                    MCID = currentMessage.get("ID",None)
                    currList = self.microcontrollerGUIMapping.get(MCID,None)
                    if currList :
                        for guiId in currList:
                            for gui in self.GUIList:
                                if gui.ID == guiId:
                                    gui.sendMsg(json.dumps(currentMessage))

            if serverCommand == "Get_Microcontrollers":
                #this block handles a request from the GUI asking what microcontrollers are currently connected to the server
                #this enables the GUI to discover the devices it may want to bind to 
                if deviceType == "GUI":
                    idList = dict()
                    for microcontroller in self.microcontrollerList:
                      idList.update({f"{microcontroller.ID}":f"{microcontroller.Device_Type}"})

                    GUIID = currentMessage.get("ID",None)  
                    for gui in self.GUIList:
                        if gui.ID == GUIID:
                            gui.sendMsg(json.dumps({"ID":"Server", "Key":"1234", "Client_Command":"Recieve_Microcontrollers", "Message":f"{idList}"}))

        
