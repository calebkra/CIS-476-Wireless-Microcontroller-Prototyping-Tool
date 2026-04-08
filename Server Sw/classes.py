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
        submittedKey = msg.get("Key")
        if submittedKey == self.AuthKey:
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

class RpiZero(AbstractMicrocontroller):
    def __init__(self,conn,id):
        self.Connection = conn
        self.ID = id
        self.Device_Type = "RpiZero"
    
    def sendMsg(self,msg):
        topic = f"Microcontroller/RPIZERO/{self.ID}"
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
    
class RpiZeroFactory(AbstractMicrocontrollerFactory):
    def __init__(self, conn):
        self.Connection = conn
    def createMicrocontroller(self,id) -> AbstractMicrocontroller:
        return RpiZero(self.Connection,id)

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
            
            serverCommand = currentMessage.get("Server_Command",None)
            deviceType = currentMessage.get("Device_Type",None)

            if serverCommand == "Connect" :
               
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
                if deviceType == "GUI":
                    idList = dict()
                    for microcontroller in self.microcontrollerList:
                      idList.update({f"{microcontroller.ID}":f"{microcontroller.Device_Type}"})

                    GUIID = currentMessage.get("ID",None)  
                    for gui in self.GUIList:
                        if gui.ID == GUIID:
                            gui.sendMsg(json.dumps({"ID":"Server", "Key":"1234", "Client_Command":"Recieve_Microcontrollers", "Message":f"{idList}"}))

        
