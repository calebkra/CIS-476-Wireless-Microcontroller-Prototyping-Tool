import tkinter as tk
import paho.mqtt.client as mqtt
import json
from tkinter import ttk
from abc import ABC, abstractmethod
from tkinter import messagebox
import time

#Constants
SERVER_TOPIC = "Test/Server"



#Proxy and Singleton design pattern
#This proxy handles authentication of all in coming messages, if authenticated messages are forwarded to the on_message handler
#in the connection class, If not alerts user key is incorrect
class authenticationProxy:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'inst'):
            cls.inst = super().__new__(cls)
            return cls.inst
        
    def initialize(self,conn):
        self.ConnectionHandler = conn
        self.ConnectionHandler.setProxy(self.on_message)

    def setKey(self, key):
        self.Key = key

    def on_message(self,client, userdata, msg):
        Message = json.loads(msg.payload.decode('utf-8'))
        
        id = Message.get("ID",None)

        if id and id == "Server":
            serverKey = Message.get("Key",None)
            if serverKey:
                self.setKey(serverKey)
        
        #auth code here
        client_command = Message.get("Client_Command",None)
        if client_command and client_command == "Invalid Key":
            self.ConnectionHandler.CurrentWindow.showError("Invalid Server Key")
            print("Invalid Key")
            return
        
        attemptedKey = Message.get("Key",None)

        if attemptedKey and self.Key == attemptedKey:
            self.ConnectionHandler.on_message(client,userdata,msg)

#Singleton class, however different from normal implimentation since python does not support private constructors
#This connection class will handle MQTT messaging, such as sending messages, additionally it intializes the MQTT client
#It also defines on_message and handling to ensure incoming messages can update the GUI 
class ConnectionHandler: 
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, initial_value=None):
        if not hasattr(self, '_initialized'):
            self.value = SERVER_TOPIC
            self._initialized = True 
            self.ServerTopic = SERVER_TOPIC
            self.Connected = False
            self.MCID = None
            self.MCType = None

    #sets the proxy on_message handler so it can be set when MQTT client is intitalized
    def setProxy(self,proxyOnMessage):
        self.ProxyOnMessage = proxyOnMessage

    #Initalizes the MQTT client, connects to the MQTT broker, and subscribes to the GUI's unique topic
    def connect(self,server_ip,port,server_key,gui_id):
        self.SelfTopic = f"GUI/{gui_id}"
        self.Server_Key = server_key
        self.GUIID = gui_id
        self.client = mqtt.Client()
        self.client.on_message = self.ProxyOnMessage
        self.client.will_set(self.ServerTopic,json.dumps({"ID":gui_id,"Key":server_key,"Device_Type":"GUI","Server_Command":"Disconnect"}),qos=2)
        self.client.connect(server_ip, port)
        self.client.subscribe(self.SelfTopic,qos=2)
        self.client.loop_start()
        #need to send connect message here
        self.client.publish(self.ServerTopic,json.dumps({"ID":f"{self.GUIID}","Device_Type":"GUI","Key":f"{self.Server_Key}","Server_Command":"Connect"}),qos=2)

    #Sends message to the server, appends certain header information that the server will use
    def sendMessage(self,msg):
        #finish send messages
        header = {"ID":f"{self.GUIID}","Key":f"{self.Server_Key}","Device_Type":"GUI"}
        finalmsg = header | msg 
        self.client.publish(self.ServerTopic,json.dumps(finalmsg),qos=2)
        
    #returns true if the GUI is successfully connected to server
    #returns false if the GUI is not connected to the server
    def isConnected(self):
        return self.Connected
    
    #on_message handler for the mqtt client, controls/manipulates the GUI instance when desired messages come in
    def on_message(self,client, userdata, msg):
        msgJson = json.loads(msg.payload.decode('utf-8'))
        clientCommand = msgJson.get("Client_Command")
        if clientCommand == "Connection Success":
            self.Connected = True
        if self.CurrentWindow.WindowID == "Connection Dashboard":
            if clientCommand == "Recieve_Microcontrollers":
                microcontrollerDict = dict()
                microcontrollerDict = eval(msgJson["Message"])
                self.CurrentWindow.setMicrocontrollerCombobox(microcontrollerDict)
                self.CurrentWindow.MCselectionFieldButton.state(['!disabled'])
            if clientCommand == "Bind Successful":
                self.closeCurrentWindow() 
        else:
            if clientCommand == "Recieve State":
                state = msgJson.get("Message")
                self.CurrentWindow.fillMCStates(state)

            if clientCommand == "Microcontroller_Disconnect":
                self.CurrentWindow.messagebox.showerror("Microcontroller disconnected, program now closing")
                self.closeCurrentWindow()   

        #Add functionality to handle MC disconnect
            
    #sets connections class current active window so it can take action on recieved messages
    def setActiveWindow(self,currWindow):
        self.CurrentWindow = currWindow

    #sets the current microcontroller ID and type of the MC the GUI is connected to 
    def setActiveMC(self, id, mctype):
        self.MCID = id
        self.MCType = mctype

    #returns the MC ID and type of the current MC the GUI is 
    def getActiveMC(self):
        return self.MCID,self.MCType

    #This method will close the current window and allow the main loop to handle creating new window
    def closeCurrentWindow(self):
        self.CurrentWindow.closeWindow()


class ConnectionDashboard:
    #sets up the GUI layout, manipulation done by method calls
    def __init__(self,connHandler):
        self.WindowID = "Connection Dashboard"
        self.ConnectionHandler = connHandler
        self.terminated = False

        self.ConnectionHandler.setActiveWindow(self)

        self.ConnWindow = tk.Tk()
        self.ConnWindow.geometry(newGeometry="300x275")
        self.ConnWindow.title("Microcontroller Prototyping Tool")
        self.ConnWindow.resizable(False,False)

        self.frame = tk.Frame(self.ConnWindow)
        
        
        self.frame.columnconfigure(index=0, weight=1)
        self.frame.columnconfigure(index=1, weight=2)
        self.frame.rowconfigure(index=1, weight=1)
        self.frame.rowconfigure(index=2, weight=1)
        self.frame.rowconfigure(index=3, weight=1)
        self.frame.rowconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=5, weight=1)
        self.frame.rowconfigure(index=6, weight=1)
        

        self.ipLabel = tk.Label(self.frame,text="Server IP Address: ")
        self.ipLabel.grid(row=0,column=0,sticky=tk.W,pady=5)
        self.ipField = tk.Entry(self.frame)
        self.ipField.grid(row=0, column=1,sticky=tk.W,pady=5)

        self.portLabel = tk.Label(self.frame, text="Port Number: ")
        self.portLabel.grid(row=1,column=0,sticky=tk.W,pady=5)
        self.portField = tk.Entry(self.frame)
        self.portField.grid(row=1,column=1,sticky=tk.W,pady=5)

        self.keyLabel = tk.Label(self.frame, text="Server Key: ")
        self.keyLabel.grid(row=2,column=0,sticky=tk.W,pady=5)
        self.keyEntry = tk.Entry(self.frame)
        self.keyEntry.grid(row=2,column=1,sticky=tk.W,pady=5)

        self.GuiIdLabel = tk.Label(self.frame,text="GUI ID: ")
        self.GuiIdLabel.grid(row=3,column=0,sticky=tk.W, pady=5)
        self.GuiIdEntry = tk.Entry(self.frame)
        self.GuiIdEntry.grid(row=3,column=1,sticky=tk.W,pady=5)

        self.findButton = ttk.Button(self.frame,text="Find Microcontrollers",command=self.findMicrocontrollers)
        self.findButton.grid(row=4,column=0,columnspan=3,pady=5)

        self.microcontrollerSelection = tk.StringVar()
        self.MCselectionLabel = tk.Label(self.frame, text="Microcontrollers Available: ")
        self.MCselectionLabel.grid(row=5,column=0,sticky=tk.W,pady=20)
        self.MCselectionField = ttk.Combobox(self.frame,textvariable=self.microcontrollerSelection)
        self.MCselectionField['state'] = 'readonly'
        self.MCselectionField.grid(row=5,column=1,sticky=tk.W,pady=20)

        self.MCselectionFieldButton = ttk.Button(self.frame, text="Connect",command=self.processMCSelection)
        self.MCselectionFieldButton.grid(row=6,column=0,columnspan=3,pady=5)
        self.MCselectionFieldButton.state(['disabled'])
        self.frame.pack(fill="x",expand=False)

        self.ConnWindow.mainloop()
    
    #retreives entered server information and sends a connection request to the server
    def findMicrocontrollers(self):
        if self.ConnectionHandler.isConnected() == False:
            IP = self.ipField.get().strip()
            PORT = int(self.portField.get().strip())
            SERVER_KEY = self.keyEntry.get().strip()
            GUI_ID = self.GuiIdEntry.get().strip()
            self.ConnectionHandler.connect(IP,PORT,SERVER_KEY,GUI_ID)
            connStatus = self.ConnectionHandler.isConnected()
            retrys = 0
            while connStatus is False and retrys < 61:
                connStatus = self.ConnectionHandler.isConnected()
                time.sleep(0.05)
                retrys += 1
            if connStatus:
                self.ConnectionHandler.sendMessage({"Server_Command":"Get_Microcontrollers"})
            #updating combobox will be handled by on message

    #Populates the combobox with MC choices
    def setMicrocontrollerCombobox(self,IdDict):
        IdListItems = list(IdDict.items())
        IdList = list()

        for item in IdListItems:
            IdList.append(str(item))

        self.MCselectionField["values"]=IdList

    #gets the microcontroller selected, parses the string, and sets the current MC for the connection class
    def processMCSelection(self):
        selection = self.microcontrollerSelection.get()
        selectionInfo = selection.split(", ")
        mcID1 = selectionInfo[0].replace("'","")
        mcID2 = mcID1.replace("(","")
        mcID = mcID2.replace(")","")
        mcType1=selectionInfo[1].replace("'","")
        mcType2 = mcType1.replace(")","")
        mcType = mcType2.replace("(","")
        self.ConnectionHandler.setActiveMC(mcID,mcType)
        self.ConnectionHandler.sendMessage({"Message":mcID,"Server_Command":"Bind"})
        #on message will handle the call to teardown this window and open new window
        #upon reciept of successful binding 

    #Handles closing the GUI window
    def closeWindow(self):
        
        if self.terminated == False:
            self.terminated = True
            self.ConnWindow.after(0,self.ConnWindow.destroy)
    
    #displays error messagebox with the message passed in
    def showError(self,errorMessage):
        messagebox.showerror("Error",errorMessage)


#Abstract GUI class that is the abstract product that will be in the abstract factory
class abstractMCDisplayGUI(ABC):
    #will send new state for pin to MC for the MC to manipulate pin state accordingly
    @abstractmethod
    def setMCStates(self,pin,value):
        pass

    #will fill out the labels that display MC pin states
    @abstractmethod
    def fillMCStates(self,states):
        pass

    #Will create and start the GUI
    @abstractmethod
    def runGUI(self):
        pass

#Concrete GUI Class for Raspberry Pi Zero
class RpiZeroGUI(abstractMCDisplayGUI):
    #initalizes class
    def __init__(self,connectionHandler):
        self.WindowID = "RpiZero Dashboard"
        self.ConnectionHandler = connectionHandler
        self.ConnectionHandler.setActiveWindow(self)
        MC = self.ConnectionHandler.getActiveMC()
        self.MCID = MC[0]
        self.delayInterval = 50
        self.terminated = False
    
    #sets up the layout of the GUI and runs the GUI
    def runGUI(self):
        self.Window = tk.Tk()
        self.Window.geometry(newGeometry="680x360")
        self.Window.title("Microcontroller Prototyping Tool")
        self.Window.resizable(False,False)

        self.frame = tk.Frame(self.Window)

        self.xpad = 10
        self.ypad = 10

        #set up rows and columns for grid layout
        self.frame.columnconfigure(index=0, weight=1)
        self.frame.columnconfigure(index=1, weight=1)
        self.frame.columnconfigure(index=2, weight=1)
        self.frame.columnconfigure(index=3, weight=1)
        self.frame.columnconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=0, weight=1)
        self.frame.rowconfigure(index=2, weight=1)
        self.frame.rowconfigure(index=3, weight=1)
        self.frame.rowconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=5, weight=1)
        self.frame.rowconfigure(index=6, weight=1)

        #create header labels and place in grid
        self.currStateLabel = tk.Label(self.frame,text="Current State",font=("TkDefaultFont",12,"bold"))
        self.currStateLabel.grid(row=0, column=0, columnspan=2, pady=self.ypad)
        self.setStateLabel = tk.Label(self.frame, text="Set States",font=("TkDefaultFont",12,"bold"))
        self.setStateLabel.grid(row=0, column=2, columnspan=2,pady=self.ypad)

        #creates elements for current state and place in grid
        self.digIn1Label = tk.Label(self.frame, text="Digital Input 1: ")
        self.digIn1Label.grid(row=1, column=0,pady=self.ypad)
        self.digIn1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digIn1State.grid(row=1, column=1,pady=self.ypad)

        self.digIn2Label = tk.Label(self.frame, text="Digital Input 2: ")
        self.digIn2Label.grid(row=2, column=0,pady=self.ypad)
        self.digIn2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digIn2State.grid(row=2, column=1,pady=self.ypad)

        self.digOut1Label = tk.Label(self.frame, text="Digital Output 1: ")
        self.digOut1Label.grid(row=3, column=0,pady=self.ypad)
        self.digOut1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digOut1State.grid(row=3, column=1,pady=self.ypad)

        self.digOut2Label = tk.Label(self.frame, text="Digital Output 2: ")
        self.digOut2Label.grid(row=4, column=0,pady=self.ypad)
        self.digOut2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digOut2State.grid(row=4, column=1,pady=self.ypad)

        self.PWM1Label = tk.Label(self.frame, text="Digital PMW 1: ")
        self.PWM1Label.grid(row=5, column=0,pady=self.ypad)
        self.PWM1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.PWM1State.grid(row=5, column=1,pady=self.ypad)

        self.PWM2Label = tk.Label(self.frame, text="Digital PMW 2: ")
        self.PWM2Label.grid(row=6, column=0,pady=self.ypad)
        self.PWM2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.PWM2State.grid(row=6, column=1,pady=self.ypad)

        #creates elements for current state and place in grid
        
        self.digitalOutputOptions = ["HIGH","LOW"]
        self.setDigOut1Label = tk.Label(self.frame, text="Digital Output 1: ")
        self.setDigOut1Label.grid(row=3,column=2,pady=self.ypad)
        self.DigOut1Val = tk.StringVar(value=self.digitalOutputOptions[0])
        self.setDigOut1Combobox = ttk.Combobox(self.frame,textvariable=self.DigOut1Val,values=self.digitalOutputOptions,state="readonly")
        self.setDigOut1Combobox.grid(row=3,column=3,pady=self.ypad)
        self.setDigOut1Button = tk.Button(self.frame, text="Set",width=10, relief="groove",command=self.setDigOut1Val)
        self.setDigOut1Button.grid(row=3,column=4,pady=self.ypad)

        self.setDigOut2Label = tk.Label(self.frame, text="Digital Output 2: ")
        self.setDigOut2Label.grid(row=4,column=2,pady=self.ypad)
        self.DigOut2Val = tk.StringVar(value=self.digitalOutputOptions[0])
        self.setDigOut2Combobox = ttk.Combobox(self.frame,textvariable=self.DigOut2Val,values=self.digitalOutputOptions,state='readonly')
        self.setDigOut2Combobox.grid(row=4,column=3,pady=self.ypad)
        self.setDigOut2Button = tk.Button(self.frame, text="Set",width=10, relief="groove",command=self.setDigOut2Val)
        self.setDigOut2Button.grid(row=4,column=4,pady=self.ypad)

        self.setPWM1Label = tk.Label(self.frame, text="PWM 1: ")
        self.setPWM1Label.grid(row=5,column=2,pady=self.ypad)
        self.setPWM1Entry = tk.Entry(self.frame)
        self.setPWM1Entry.grid(row=5,column=3,pady=self.ypad)
        self.setPWM1Button = tk.Button(self.frame, text="Set",width=10, relief="groove", command=self.setPWM1Val)
        self.setPWM1Button.grid(row=5,column=4,pady=self.ypad)

        self.setPWM2Label = tk.Label(self.frame, text="PWM 2: ")
        self.setPWM2Label.grid(row=6,column=2,pady=self.ypad)
        self.setPWM2Entry = tk.Entry(self.frame)
        self.setPWM2Entry.grid(row=6,column=3,pady=self.ypad)
        self.setPWM2Button = tk.Button(self.frame, text="Set",width=10, relief="groove", command=self.setPWM2Val)
        self.setPWM2Button.grid(row=6,column=4,pady=self.ypad)

        #places UI elements into window
        self.frame.pack(fill="x",expand=False)
        
        #starts execution
        self.Window.mainloop()
        
        
    #button command methods that will forward pin and value to set MC states

    def setDigOut1Val(self):
        val = self.setDigOut1Combobox.get()
        self.setMCStates("DO1",val)
        self.Window.after(self.delayInterval,self.getMCStates)


    def setDigOut2Val(self):
        val = self.setDigOut2Combobox.get()
        self.setMCStates("DO2",val)
        self.Window.after(self.delayInterval,self.getMCStates)

    def setPWM1Val(self):
        try:
            pwmVal = self.setPWM1Entry.get()
            value = int(pwmVal)

            if value > 100 or value < -1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Please enter an integer between 0-100")
            return

        self.setMCStates("PWM1",value=value)
        self.Window.after(self.delayInterval,self.getMCStates)

    def setPWM2Val(self):
        try:
            pwmVal = self.setPWM2Entry.get()
            value = int(pwmVal)

            if value > 100 or value < -1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Please enter an integer between 0-100")
            return

        self.setMCStates("PWM2",value=value)
        self.Window.after(self.delayInterval,self.getMCStates)



    #sends pin and corresponding value for the MC to update
    def setMCStates(self, pin, value):
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Reciever_ID":self.MCID,"Client_Command":"Set State", "Message":{pin:value}})

    #takes new pin states, and updates display windows accordingly
    def fillMCStates(self, states):
        #get current label states for comparsion
        currentDI1 = self.digIn1State.cget("text")
        currentDI2 = self.digIn2State.cget("text")
        currentDO1 = self.digOut1State.cget("text")
        currentDO2 = self.digOut2State.cget("text")
        currentPWM1 = self.PWM1State.cget("text")
        currentPWM2 = self.PWM2State.cget("text")

        #get new states for comparison
        newDI1 = states.get("DI1","None")
        newDI2 = states.get("DI2","None")
        newDO1 = states.get("DO1","None")
        newDO2 = states.get("DO2","None")
        newPWM1 = states.get("PWM1","None")
        newPWM2= states.get("PWM2","None")

        #check if new state provided, if so check if display would change, if so update accordingly 

        if newDI1 != "None":
            if currentDI1 != newDI1:
                self.digIn1State.config(text=newDI1)

        if newDI2 != "None":
            if currentDI2 != newDI2:
                self.digIn2State.config(text=newDI2)

        if newDO1 != "None":
            if currentDO1 != newDO1:
                self.digOut1State.config(text=newDO1)

        if newDO2 != "None":
            if currentDO2 != newDO2:
                self.digOut2State.config(text=newDO2)

        if newPWM1 != "None":
            if currentPWM1 != newPWM1:
                self.PWM1State.config(text=str(newPWM1))
        
        if newPWM2 != "None":
            if currentPWM2 != newPWM2:
                self.PWM2State.config(text=str(newPWM2))

    #sends message to server then MC requesting MC current states
    def getMCStates(self):
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Reciever_ID":self.MCID,"Client_Command":"Get State"})

    #closes the GUI window
    def closeWindow(self):
        if self.terminated == False:
            self.terminated = True
            self.ConnWindow.after(0,self.ConnWindow.destroy)

#Concrete GUI class for Raspberry Pi Pico
class RpiPicoGUI(abstractMCDisplayGUI): #initalizes class
    def __init__(self,connectionHandler):
        self.WindowID = "Pico Dashboard"
        self.ConnectionHandler = connectionHandler
        self.ConnectionHandler.setActiveWindow(self)
        MC = self.ConnectionHandler.getActiveMC()
        self.MCID = MC[0]
        self.delayInterval = 50
        self.terminated = False
    
    #sets up the layout of the GUI and runs the GUI
    def runGUI(self):
        self.Window = tk.Tk()
        self.Window.geometry(newGeometry="680x360")
        self.Window.title("Microcontroller Prototyping Tool")
        self.Window.resizable(False,False)

        self.frame = tk.Frame(self.Window)

        self.xpad = 10
        self.ypad = 10

        #set up rows and columns for grid layout
        self.frame.columnconfigure(index=0, weight=1)
        self.frame.columnconfigure(index=1, weight=1)
        self.frame.columnconfigure(index=2, weight=1)
        self.frame.columnconfigure(index=3, weight=1)
        self.frame.columnconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=0, weight=1)
        self.frame.rowconfigure(index=2, weight=1)
        self.frame.rowconfigure(index=3, weight=1)
        self.frame.rowconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=5, weight=1)
        self.frame.rowconfigure(index=6, weight=1)

        #create header labels and place in grid
        self.currStateLabel = tk.Label(self.frame,text="Current State",font=("TkDefaultFont",12,"bold"))
        self.currStateLabel.grid(row=0, column=0, columnspan=2, pady=self.ypad)
        self.setStateLabel = tk.Label(self.frame, text="Set States",font=("TkDefaultFont",12,"bold"))
        self.setStateLabel.grid(row=0, column=2, columnspan=2,pady=self.ypad)

        #creates elements for current state and place in grid
        self.digIn1Label = tk.Label(self.frame, text="Digital Input 1: ")
        self.digIn1Label.grid(row=1, column=0,pady=self.ypad)
        self.digIn1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digIn1State.grid(row=1, column=1,pady=self.ypad)

        self.digIn2Label = tk.Label(self.frame, text="Digital Input 2: ")
        self.digIn2Label.grid(row=2, column=0,pady=self.ypad)
        self.digIn2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digIn2State.grid(row=2, column=1,pady=self.ypad)

        self.digOut1Label = tk.Label(self.frame, text="Digital Output 1: ")
        self.digOut1Label.grid(row=3, column=0,pady=self.ypad)
        self.digOut1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digOut1State.grid(row=3, column=1,pady=self.ypad)

        self.digOut2Label = tk.Label(self.frame, text="Digital Output 2: ")
        self.digOut2Label.grid(row=4, column=0,pady=self.ypad)
        self.digOut2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digOut2State.grid(row=4, column=1,pady=self.ypad)

        self.PWM1Label = tk.Label(self.frame, text="Digital PMW 1: ")
        self.PWM1Label.grid(row=5, column=0,pady=self.ypad)
        self.PWM1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.PWM1State.grid(row=5, column=1,pady=self.ypad)

        self.PWM2Label = tk.Label(self.frame, text="Digital PMW 2: ")
        self.PWM2Label.grid(row=6, column=0,pady=self.ypad)
        self.PWM2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.PWM2State.grid(row=6, column=1,pady=self.ypad)

        #creates elements for current state and place in grid
        
        self.digitalOutputOptions = ["HIGH","LOW"]
        self.setDigOut1Label = tk.Label(self.frame, text="Digital Output 1: ")
        self.setDigOut1Label.grid(row=3,column=2,pady=self.ypad)
        self.DigOut1Val = tk.StringVar(value=self.digitalOutputOptions[0])
        self.setDigOut1Combobox = ttk.Combobox(self.frame,textvariable=self.DigOut1Val,values=self.digitalOutputOptions,state="readonly")
        self.setDigOut1Combobox.grid(row=3,column=3,pady=self.ypad)
        self.setDigOut1Button = tk.Button(self.frame, text="Set",width=10, relief="groove",command=self.setDigOut1Val)
        self.setDigOut1Button.grid(row=3,column=4,pady=self.ypad)

        self.setDigOut2Label = tk.Label(self.frame, text="Digital Output 2: ")
        self.setDigOut2Label.grid(row=4,column=2,pady=self.ypad)
        self.DigOut2Val = tk.StringVar(value=self.digitalOutputOptions[0])
        self.setDigOut2Combobox = ttk.Combobox(self.frame,textvariable=self.DigOut2Val,values=self.digitalOutputOptions,state='readonly')
        self.setDigOut2Combobox.grid(row=4,column=3,pady=self.ypad)
        self.setDigOut2Button = tk.Button(self.frame, text="Set",width=10, relief="groove",command=self.setDigOut2Val)
        self.setDigOut2Button.grid(row=4,column=4,pady=self.ypad)

        self.setPWM1Label = tk.Label(self.frame, text="PWM 1: ")
        self.setPWM1Label.grid(row=5,column=2,pady=self.ypad)
        self.setPWM1Entry = tk.Entry(self.frame)
        self.setPWM1Entry.grid(row=5,column=3,pady=self.ypad)
        self.setPWM1Button = tk.Button(self.frame, text="Set",width=10, relief="groove", command=self.setPWM1Val)
        self.setPWM1Button.grid(row=5,column=4,pady=self.ypad)

        self.setPWM2Label = tk.Label(self.frame, text="PWM 2: ")
        self.setPWM2Label.grid(row=6,column=2,pady=self.ypad)
        self.setPWM2Entry = tk.Entry(self.frame)
        self.setPWM2Entry.grid(row=6,column=3,pady=self.ypad)
        self.setPWM2Button = tk.Button(self.frame, text="Set",width=10, relief="groove", command=self.setPWM2Val)
        self.setPWM2Button.grid(row=6,column=4,pady=self.ypad)

        #places UI elements into window
        self.frame.pack(fill="x",expand=False)
        
        #starts execution
        self.Window.mainloop()
        
        
    #button command methods that will forward pin and value to set MC states

    def setDigOut1Val(self):
        val = self.setDigOut1Combobox.get()
        self.setMCStates("DO1",val)
        self.Window.after(self.delayInterval,self.getMCStates)


    def setDigOut2Val(self):
        val = self.setDigOut2Combobox.get()
        self.setMCStates("DO2",val)
        self.Window.after(self.delayInterval,self.getMCStates)

    def setPWM1Val(self):
        try:
            pwmVal = self.setPWM1Entry.get()
            value = int(pwmVal)

            if value > 100 or value < -1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Please enter an integer between 0-100")
            return

        self.setMCStates("PWM1",value=value)
        self.Window.after(self.delayInterval,self.getMCStates)

    def setPWM2Val(self):
        try:
            pwmVal = self.setPWM2Entry.get()
            value = int(pwmVal)

            if value > 100 or value < -1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Please enter an integer between 0-100")
            return

        self.setMCStates("PWM2",value=value)
        self.Window.after(self.delayInterval,self.getMCStates)



    #sends pin and corresponding value for the MC to update
    def setMCStates(self, pin, value):
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Reciever_ID":self.MCID,"Client_Command":"Set State", "Message":{pin:value}})

    #takes new pin states, and updates display windows accordingly
    def fillMCStates(self, states):
        #get current label states for comparsion
        currentDI1 = self.digIn1State.cget("text")
        currentDI2 = self.digIn2State.cget("text")
        currentDO1 = self.digOut1State.cget("text")
        currentDO2 = self.digOut2State.cget("text")
        currentPWM1 = self.PWM1State.cget("text")
        currentPWM2 = self.PWM2State.cget("text")

        #get new states for comparison
        newDI1 = states.get("DI1","None")
        newDI2 = states.get("DI2","None")
        newDO1 = states.get("DO1","None")
        newDO2 = states.get("DO2","None")
        newPWM1 = states.get("PWM1","None")
        newPWM2= states.get("PWM2","None")

        #check if new state provided, if so check if display would change, if so update accordingly 

        if newDI1 != "None":
            if currentDI1 != newDI1:
                self.digIn1State.config(text=newDI1)

        if newDI2 != "None":
            if currentDI2 != newDI2:
                self.digIn2State.config(text=newDI2)

        if newDO1 != "None":
            if currentDO1 != newDO1:
                self.digOut1State.config(text=newDO1)

        if newDO2 != "None":
            if currentDO2 != newDO2:
                self.digOut2State.config(text=newDO2)

        if newPWM1 != "None":
            if currentPWM1 != newPWM1:
                self.PWM1State.config(text=str(newPWM1))
        
        if newPWM2 != "None":
            if currentPWM2 != newPWM2:
                self.PWM2State.config(text=str(newPWM2))

    #sends message to server then MC requesting MC current states
    def getMCStates(self):
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Reciever_ID":self.MCID,"Client_Command":"Get State"})

    #closes the GUI window
    def closeWindow(self):
        if self.terminated == False:
            self.terminated = True
            self.ConnWindow.after(0,self.ConnWindow.destroy)
   
#Concrete GUI class for ESP32
class ESP32GUI(abstractMCDisplayGUI):
     #initalizes class
    def __init__(self,connectionHandler):
        self.WindowID = "ESP32 Dashboard"
        self.ConnectionHandler = connectionHandler
        self.ConnectionHandler.setActiveWindow(self)
        MC = self.ConnectionHandler.getActiveMC()
        self.MCID = MC[0]
        self.delayInterval = 50
        self.terminated = False
    
    #sets up the layout of the GUI and runs the GUI
    def runGUI(self):
        self.Window = tk.Tk()
        self.Window.geometry(newGeometry="680x360")
        self.Window.title("Microcontroller Prototyping Tool")
        self.Window.resizable(False,False)

        self.frame = tk.Frame(self.Window)

        self.xpad = 10
        self.ypad = 10

        #set up rows and columns for grid layout
        self.frame.columnconfigure(index=0, weight=1)
        self.frame.columnconfigure(index=1, weight=1)
        self.frame.columnconfigure(index=2, weight=1)
        self.frame.columnconfigure(index=3, weight=1)
        self.frame.columnconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=0, weight=1)
        self.frame.rowconfigure(index=2, weight=1)
        self.frame.rowconfigure(index=3, weight=1)
        self.frame.rowconfigure(index=4, weight=1)
        self.frame.rowconfigure(index=5, weight=1)
        self.frame.rowconfigure(index=6, weight=1)

        #create header labels and place in grid
        self.currStateLabel = tk.Label(self.frame,text="Current State",font=("TkDefaultFont",12,"bold"))
        self.currStateLabel.grid(row=0, column=0, columnspan=2, pady=self.ypad)
        self.setStateLabel = tk.Label(self.frame, text="Set States",font=("TkDefaultFont",12,"bold"))
        self.setStateLabel.grid(row=0, column=2, columnspan=2,pady=self.ypad)

        #creates elements for current state and place in grid
        self.digIn1Label = tk.Label(self.frame, text="Digital Input 1: ")
        self.digIn1Label.grid(row=1, column=0,pady=self.ypad)
        self.digIn1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digIn1State.grid(row=1, column=1,pady=self.ypad)

        self.digIn2Label = tk.Label(self.frame, text="Digital Input 2: ")
        self.digIn2Label.grid(row=2, column=0,pady=self.ypad)
        self.digIn2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digIn2State.grid(row=2, column=1,pady=self.ypad)

        self.digOut1Label = tk.Label(self.frame, text="Digital Output 1: ")
        self.digOut1Label.grid(row=3, column=0,pady=self.ypad)
        self.digOut1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digOut1State.grid(row=3, column=1,pady=self.ypad)

        self.digOut2Label = tk.Label(self.frame, text="Digital Output 2: ")
        self.digOut2Label.grid(row=4, column=0,pady=self.ypad)
        self.digOut2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.digOut2State.grid(row=4, column=1,pady=self.ypad)

        self.PWM1Label = tk.Label(self.frame, text="Digital PMW 1: ")
        self.PWM1Label.grid(row=5, column=0,pady=self.ypad)
        self.PWM1State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.PWM1State.grid(row=5, column=1,pady=self.ypad)

        self.PWM2Label = tk.Label(self.frame, text="Digital PMW 2: ")
        self.PWM2Label.grid(row=6, column=0,pady=self.ypad)
        self.PWM2State = tk.Label(self.frame, text="None", borderwidth= 2, relief="groove",width=25,bg="white")
        self.PWM2State.grid(row=6, column=1,pady=self.ypad)

        #creates elements for current state and place in grid
        
        self.digitalOutputOptions = ["HIGH","LOW"]
        self.setDigOut1Label = tk.Label(self.frame, text="Digital Output 1: ")
        self.setDigOut1Label.grid(row=3,column=2,pady=self.ypad)
        self.DigOut1Val = tk.StringVar(value=self.digitalOutputOptions[0])
        self.setDigOut1Combobox = ttk.Combobox(self.frame,textvariable=self.DigOut1Val,values=self.digitalOutputOptions,state="readonly")
        self.setDigOut1Combobox.grid(row=3,column=3,pady=self.ypad)
        self.setDigOut1Button = tk.Button(self.frame, text="Set",width=10, relief="groove",command=self.setDigOut1Val)
        self.setDigOut1Button.grid(row=3,column=4,pady=self.ypad)

        self.setDigOut2Label = tk.Label(self.frame, text="Digital Output 2: ")
        self.setDigOut2Label.grid(row=4,column=2,pady=self.ypad)
        self.DigOut2Val = tk.StringVar(value=self.digitalOutputOptions[0])
        self.setDigOut2Combobox = ttk.Combobox(self.frame,textvariable=self.DigOut2Val,values=self.digitalOutputOptions,state='readonly')
        self.setDigOut2Combobox.grid(row=4,column=3,pady=self.ypad)
        self.setDigOut2Button = tk.Button(self.frame, text="Set",width=10, relief="groove",command=self.setDigOut2Val)
        self.setDigOut2Button.grid(row=4,column=4,pady=self.ypad)

        self.setPWM1Label = tk.Label(self.frame, text="PWM 1: ")
        self.setPWM1Label.grid(row=5,column=2,pady=self.ypad)
        self.setPWM1Entry = tk.Entry(self.frame)
        self.setPWM1Entry.grid(row=5,column=3,pady=self.ypad)
        self.setPWM1Button = tk.Button(self.frame, text="Set",width=10, relief="groove", command=self.setPWM1Val)
        self.setPWM1Button.grid(row=5,column=4,pady=self.ypad)

        self.setPWM2Label = tk.Label(self.frame, text="PWM 2: ")
        self.setPWM2Label.grid(row=6,column=2,pady=self.ypad)
        self.setPWM2Entry = tk.Entry(self.frame)
        self.setPWM2Entry.grid(row=6,column=3,pady=self.ypad)
        self.setPWM2Button = tk.Button(self.frame, text="Set",width=10, relief="groove", command=self.setPWM2Val)
        self.setPWM2Button.grid(row=6,column=4,pady=self.ypad)

        #places UI elements into window
        self.frame.pack(fill="x",expand=False)
        
        #starts execution
        self.Window.mainloop()
        
        
    #button command methods that will forward pin and value to set MC states

    def setDigOut1Val(self):
        val = self.setDigOut1Combobox.get()
        self.setMCStates("DO1",val)
        self.Window.after(self.delayInterval,self.getMCStates)


    def setDigOut2Val(self):
        val = self.setDigOut2Combobox.get()
        self.setMCStates("DO2",val)
        self.Window.after(self.delayInterval,self.getMCStates)

    def setPWM1Val(self):
        try:
            pwmVal = self.setPWM1Entry.get()
            value = int(pwmVal)

            if value > 100 or value < -1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Please enter an integer between 0-100")
            return

        self.setMCStates("PWM1",value=value)
        self.Window.after(self.delayInterval,self.getMCStates)

    def setPWM2Val(self):
        try:
            pwmVal = self.setPWM2Entry.get()
            value = int(pwmVal)

            if value > 100 or value < -1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error","Please enter an integer between 0-100")
            return

        self.setMCStates("PWM2",value=value)
        self.Window.after(self.delayInterval,self.getMCStates)



    #sends pin and corresponding value for the MC to update
    def setMCStates(self, pin, value):
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Reciever_ID":self.MCID,"Client_Command":"Set State", "Message":{pin:value}})

    #takes new pin states, and updates display windows accordingly
    def fillMCStates(self, states):
        #get current label states for comparsion
        currentDI1 = self.digIn1State.cget("text")
        currentDI2 = self.digIn2State.cget("text")
        currentDO1 = self.digOut1State.cget("text")
        currentDO2 = self.digOut2State.cget("text")
        currentPWM1 = self.PWM1State.cget("text")
        currentPWM2 = self.PWM2State.cget("text")

        #get new states for comparison
        newDI1 = states.get("DI1","None")
        newDI2 = states.get("DI2","None")
        newDO1 = states.get("DO1","None")
        newDO2 = states.get("DO2","None")
        newPWM1 = states.get("PWM1","None")
        newPWM2= states.get("PWM2","None")

        #check if new state provided, if so check if display would change, if so update accordingly 

        if newDI1 != "None":
            if currentDI1 != newDI1:
                self.digIn1State.config(text=newDI1)

        if newDI2 != "None":
            if currentDI2 != newDI2:
                self.digIn2State.config(text=newDI2)

        if newDO1 != "None":
            if currentDO1 != newDO1:
                self.digOut1State.config(text=newDO1)

        if newDO2 != "None":
            if currentDO2 != newDO2:
                self.digOut2State.config(text=newDO2)

        if newPWM1 != "None":
            if currentPWM1 != newPWM1:
                self.PWM1State.config(text=str(newPWM1))
        
        if newPWM2 != "None":
            if currentPWM2 != newPWM2:
                self.PWM2State.config(text=str(newPWM2))

    #sends message to server then MC requesting MC current states
    def getMCStates(self):
        self.ConnectionHandler.sendMessage({"Server_Command":"Send_Message","Reciever_ID":self.MCID,"Client_Command":"Get State"})

    #closes the GUI window
    def closeWindow(self):
        if self.terminated == False:
            self.terminated = True
            self.ConnWindow.after(0,self.ConnWindow.destroy)


#Abstract Factory for GUI Creation
class abstractGuiFactory(ABC):
    @abstractmethod
    def createGUI(self,connectionHandler) -> abstractMCDisplayGUI:
        pass

#Concrete factory for creating GUI instances for Raspberry Pi Zero
class RpiZeroFactory(abstractGuiFactory):
    def __init__(self):
        self.FactoryID = "RpiZero"
        

    def createGUI(self, connectionHandler) ->abstractMCDisplayGUI:
        return RpiZeroGUI(connectionHandler)

#Concrete Factory for creating GUI instances for Raspberry Pi Pico
class RpiPicoFactory(abstractGuiFactory):
    def __init__(self):
        self.FactoryID = "RpiPico"
        

    def createGUI(self, connectionHandler) ->abstractMCDisplayGUI:
        return RpiPicoGUI(connectionHandler)

#Concrete Factory for creating GUI instances for ESP32
class ESP32Factory(abstractGuiFactory):
    def __init__(self):
        self.FactoryID = "ESP32"
        

    def createGUI(self, connectionHandler) ->abstractMCDisplayGUI:
        return ESP32GUI(connectionHandler)        



#create connection and proxy instances
conn = ConnectionHandler()
proxy = authenticationProxy()
proxy.initialize(conn=conn)


#create factories and dictionary of factories to help create new GUI instances when needed 
rpiZFactory = RpiZeroFactory()
rpiPFactory = RpiPicoFactory()
espFactory = ESP32Factory()
factoryDict={"RpiZero":rpiZFactory, "Pico":rpiPFactory, "ESP32":espFactory}

#create initial connection window
ConnWindow = ConnectionDashboard(conn)


#create new window once connection window closes
newWindowInfo = conn.getActiveMC()
newWindowType = newWindowInfo[1]

if newWindowType:
    factory = factoryDict.get(newWindowType,None)
    if factory:
        newWindow = factory.createGUI(conn)
        newWindow.runGUI()

