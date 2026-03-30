import tkinter as tk
import paho.mqtt.client as mqtt
import json
from tkinter import ttk

class ConnectionHandler:
    def __init__(self):
        self.ServerTopic = "Test/Server"
        self.Connected = False

    def connect(self,server_ip,port,server_key,gui_id):
        self.SelfTopic = f"GUI/{gui_id}"
        self.Server_Key = server_key
        self.GUIID = gui_id
        self.client = mqtt.Client()
        self.client.on_message = self.__on_message
        self.client.connect(server_ip, port)
        self.client.subscribe(self.SelfTopic,qos=2)
        self.client.loop_start()
        #need to send connect message here
        self.client.publish(self.ServerTopic,json.dumps({"ID":f"{self.GUIID}","Device_Type":"GUI","Key":f"{self.Server_Key}","Server_Command":"Connect"}),qos=2)

    def sendMessage(self,msg):
        #finish send messages
        header = {"ID":f"{self.GUIID}","Key":f"{self.Server_Key}","Device_Type":"GUI"}
        finalmsg = header | msg 
        self.client.publish(self.ServerTopic,json.dumps(finalmsg),qos=2)
        
    def isConnected(self):
        return self.Connected
    
    def __on_message(self,client, userdata, msg):
        msgJson = json.loads(msg.payload.decode('utf-8'))
        if msgJson["Client_Command"] == "Connection Success":
            self.Connected = True
        if self.CurrentWindow.WindowID == "Connection Dashboard":
             if msgJson["Client_Command"] == "Recieve_Microcontrollers":
                 microcontrollerDict = dict()
                 microcontrollerDict = eval(msgJson["Message"])
                 self.CurrentWindow.setMicrocontrollerCombobox(microcontrollerDict)
                 self.CurrentWindow.MCselectionFieldButton.state(['!disabled'])

    def setActiveWindow(self,currWindow):
        self.CurrentWindow = currWindow

    def setActiveMC(self, id, mctype):
        self.MCID = id
        self.MCType = mctype


class ConnectionDashboard:
    def __init__(self,connHandler):
        self.WindowID = "Connection Dashboard"
        self.ConnectionHandler = connHandler
        
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
        self.frame.rowconfigure(index=6, weight=1 )
        

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
    
    def findMicrocontrollers(self):
        if self.ConnectionHandler.isConnected() == False:
            IP = self.ipField.get().strip()
            PORT = int(self.portField.get().strip())
            SERVER_KEY = self.keyEntry.get().strip()
            GUI_ID = self.GuiIdEntry.get().strip()
            self.ConnectionHandler.connect(IP,PORT,SERVER_KEY,GUI_ID)
            connStatus = self.ConnectionHandler.isConnected()
            while connStatus is False:
                connStatus = self.ConnectionHandler.isConnected()
            self.ConnectionHandler.sendMessage({"Server_Command":"Get_Microcontrollers"})
            #updating combobox will be handled by on message

    def setMicrocontrollerCombobox(self,IdDict):
        IdListItems = list(IdDict.items())
        IdList = list()

        for item in IdListItems:
            IdList.append(str(item))

        self.MCselectionField["values"]=IdList

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




conn = ConnectionHandler()
ConnWindow = ConnectionDashboard(conn)

