from queue import Queue
from abc import ABC, abstractmethod
import json

class Connection:
    
    def __init__(self,MqttClient):
        self.MqttConnection = MqttClient
    
    MessageList = Queue()

    def recieveMessage(self,msg):
        self.MessageList.put(msg)
    
    def getMessage(self):
        if not self.MessageList.empty():
            return self.MessageList.get()
        else:
            return None

    def sendMessage(self,topic,message):
        self.MqttConnection.publish(topic,message,qos=2)


class connProxy:
    
    def __init__(self,key,conn):
        self.AuthKey=key
        self.Connection = conn
        
    
    def authenticate(self,msg):
        if msg['Key'] == self.AuthKey:
            self.Connection.recieveMessage(msg)
        else:
            #add sending error code back to sender
            print("Wrong Authentication Code")

class AbstractMicrocontroller(ABC):
    @abstractmethod
    def sendMsg(self,msg):
        pass

class ESP32(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/ESP32/{self.ID}"
        self.Connection.sendMessage(topic,msg)

class Pico(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/PICO/{self.ID}"
        self.Connection.sendMessage(topic,msg)
        

class AbstractMicrocontrollerFactory(ABC):
    @abstractmethod
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        pass

class Esp32Factory(AbstractMicrocontrollerFactory):
    def __init__(self, conn):
        self.Connection = conn
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        return ESP32(self.Connection,id)

class PicoFactory(AbstractMicrocontrollerFactory):
    def __init__(self, conn):
        self.Connection = conn
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        return Pico(self.Connection,id)

class GUIFactory:
    def __init__(self,conn):
        self.Connection = conn
        
    def createGUI(self,id):
        return GUI(self.Connection,id)
    
class GUI:
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
    
    def sendMsg(self,msg):
        topic = f"GUI/{self.ID}"
        self.Connection.sendMessage(topic,msg)    

#Finish and Test this class
class Mediator:
    microcontrollerList = list()
    GUIList = list()
    microcontrollerGUIMapping = {}
    
    def __init__(self,conn,factoryDict):
        self.Connection = conn
        self.Factories = factoryDict

    def startMediation(self):
        while True:
            currentMessage= self.Connection.getMessage()
            if currentMessage == None :
                continue

            if currentMessage["Server_Command"] == "Connect" :
               
                if currentMessage["Device_Type"] == "GUI":
                    factoryGUI = self.Factories["GUI"]
                    GUIinstance = factoryGUI.createGUI(currentMessage["ID"])
                    self.GUIList.append(GUIinstance)
                    GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Connection Success"}))

                if currentMessage["Device_Type"] == "ESP32" or currentMessage["Device_Type"] == "Pico":
                    if currentMessage["Device_Type"] == "ESP32":
                        factoryMicrocontroller = self.Factories["ESP32"] 
                    if currentMessage["Device_Type"] == "Pico":
                        factoryMicrocontroller = self.Factories["Pico"]
                   
                    microcontrollerInstance = factoryMicrocontroller.createMicrocontroller(currentMessage["ID"])
                    self.microcontrollerList.append(microcontrollerInstance)
                    microcontrollerInstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Connection Success"}))
            
            if currentMessage["Server_Command"] == "Bind" and currentMessage["Device_Type"] == "GUI":
                #find GUI instance first
                for GUIinst in self.GUIList:
                    GUIinstance = GUIinst
                    if GUIinst.ID == currentMessage["ID"]:
                        break
                    else:
                        GUIinstance = None
                
                if GUIinstance != None:
                    #find microcontroller instance
                    for microcontrollerInst in self.microcontrollerList:
                        microcontrollerInstance = microcontrollerInst
                        if microcontrollerInst == currentMessage["Message"]:
                            break
                        else:
                            GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Bind Unsuccessful"}))
                            microcontrollerInstance = None
                
                if microcontrollerInstance != None:
                    currGUIMapList = self.microcontrollerGUIMapping.get(f"{microcontrollerInstance.ID}",None)
                    if currGUIMapList == None :
                        self.microcontrollerGUIMapping.update(f"{microcontrollerInstance.ID}") = list(GUIinstance.ID)
                        GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Bind Successful"}))
                    else:
                        currGUIMapList.append(GUIinstance.ID)
                        self.microcontrollerGUIMapping.update(f"{microcontrollerInstance.ID}") = currGUIMapList
                        GUIinstance.sendMsg(json.dumps({"ID":"Server", "Key":"1234","Client_Command":"Bind Successful"}))

        #add Disconnect, Send message
