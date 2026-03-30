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
        self.Device_Type = "ESP32"
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/ESP32/{self.ID}"
        self.Connection.sendMessage(topic,msg)

class Pico(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
        self.Device_Type = "Pico"
    
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
                        if microcontrollerInst.ID == currentMessage["Message"]:
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
               
            if currentMessage["Server_Command"] == "Disconnect":
                if currentMessage["Device_Type"] == "GUI":
                    keyList = [key for key, val in self.microcontrollerGUIMapping if currentMessage["ID"] in val]

                    for key in keyList:
                        currList = self.microcontrollerGUIMapping[key]
                        currList.remove(currentMessage["ID"])
                        if not currList:
                            self.microcontrollerGUIMapping.pop(key,None)
                        else:
                            self.microcontrollerGUIMapping[key]=currList

                if currentMessage["Device_Type"] == "ESP32" or currentMessage["Device_Type"] == "Pico":
                    currList = self.microcontrollerGUIMapping.get(f"{currentMessage["ID"]}")
                    if currList:
                        for GUIid in currList:
                            for gui in self.GUIList:
                                if gui.ID == GUIid:
                                    gui.sendMsg(json.dumps({"ID":"Server","Key":"1234", "Client_Command":"Microcontroller_Disconnect"}))
                    
                        self.microcontrollerGUIMapping.pop(currentMessage["ID"])
            
            if currentMessage["Server_Command"] == "Send_Message":
                if currentMessage["Device_Type"] == "GUI":
                    for microcontroller in self.microcontrollerList:
                        if microcontroller.ID == currentMessage["Reciever_ID"]:
                            microcontroller.sendMsg(json.dumps(currentMessage))
                if currentMessage["Device_Type"] == "ESP32" or currentMessage["Device_Type"] == "Pico":
                    currList = self.microcontrollerGUIMapping[currentMessage["ID"]]
                    for guiId in currList:
                        for gui in self.GUIList:
                            if gui.ID == guiId:
                                gui.sendMsg(json.dumps(currentMessage))

            if currentMessage["Server_Command"] == "Get_Microcontrollers":
                if currentMessage["Device_Type"] == "GUI":
                    idList = dict()
                    for microcontroller in self.microcontrollerList:
                      idList.update({f"{microcontroller.ID}":f"{microcontroller.Device_Type}"})
                      
                    for gui in self.GUIList:
                        if gui.ID == currentMessage["ID"]:
                            gui.sendMsg(json.dumps({"ID":"Server", "Key":"1234", "Client_Command":"Recieve_Microcontrollers", "Message":f"{idList}"}))

        
