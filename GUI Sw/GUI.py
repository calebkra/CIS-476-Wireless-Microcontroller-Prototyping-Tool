import tkinter as tk
import paho.mqtt.client as mqtt
import json
from tkinter import ttk

class ConnectionHandler:
    def __init__(self,server_ip, port, server_key):
        Server_Key = server_key
        client = mqtt.Client()
        client.on_message = self.__on_message
        client.connect(server_ip, port)
        client.loop_start()

    def __on_message(client, userdata, msg):
        pass

    def setActiveWindow(self,currWindow):
        self.CurrentWindow = currWindow

class ConnectionDashboard:
    def __init__(self,connHandler):
        self.WindowID = "Connection Dashboard"
        self.ConnectionHandler = connHandler
        
        self.ConnectionHandler.setActiveWindow(self)

        ConnWindow = tk.Tk()
        ConnWindow.geometry(newGeometry="300x275")
        ConnWindow.title("Microcontroller Prototyping Tool")
        ConnWindow.resizable(False,False)

        frame = tk.Frame(ConnWindow)
        
        
        frame.columnconfigure(index=0,weight=1)
        frame.columnconfigure(index=1,weight=2)
        frame.rowconfigure(index=1, weight=1)
        frame.rowconfigure(index=2, weight=1)
        frame.rowconfigure(index=3, weight=1)
        frame.rowconfigure(index=4, weight=1)
        frame.rowconfigure(index=5, weight=1)
        

        ipLabel = tk.Label(frame,text="Server IP Address: ")
        ipLabel.grid(row=0,column=0,sticky=tk.W,pady=5)
        ipField = tk.Entry(frame)
        ipField.grid(row=0, column=1,sticky=tk.W,pady=5)

        portLabel = tk.Label(frame, text="Port Number: ")
        portLabel.grid(row=1,column=0,sticky=tk.W,pady=5)
        portField = tk.Entry(frame)
        portField.grid(row=1,column=1,sticky=tk.W,pady=5)

        keyLabel = tk.Label(frame, text="Server Key: ")
        keyLabel.grid(row=2,column=0,sticky=tk.W,pady=5)
        keyEntry = tk.Entry(frame)
        keyEntry.grid(row=2,column=1,sticky=tk.W,pady=5)

        findButton = tk.Button(frame,text="Find Microcontrollers")
        findButton.grid(row=3,column=0,columnspan=3,pady=5)

        MCselectionLabel = tk.Label(frame, text="Microcontrollers Available: ")
        MCselectionLabel.grid(row=4,column=0,sticky=tk.W,pady=10)
        MCselectionField = ttk.Combobox(frame)
        MCselectionField.grid(row=4,column=1,sticky=tk.W,pady=10)

        MCselectionFieldButton = tk.Button(frame, text="Connect")
        MCselectionFieldButton.grid(row=5,column=0,columnspan=3,pady=5)

        frame.pack(fill="x",expand=False)

        ConnWindow.mainloop()


conn = ConnectionHandler("127.0.0.1",1883,"1234")
ConnWindow = ConnectionDashboard(conn)

