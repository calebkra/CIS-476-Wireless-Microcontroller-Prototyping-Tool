import paho.mqtt.client as mqtt
from queue import Queue
import json
import classes


#Constants
SERVER_IP = '192.168.8.101'
PORT = 1883
SERVER_TOPIC = "Test/Server"
SERVER_KEY = "1234"

#defines the on_message handler for the mqtt client
#forwards message to proxy for authetication
def on_message(client, userdata, msg):
    msgJson = json.loads(msg.payload.decode('utf-8'))
    ProxyInstance.authenticate(msgJson)

#initalizes the mqtt client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1) 
# OR use VERSION2 if you plan to update your callback signatures
client.on_message = on_message
client.connect(SERVER_IP, PORT)

#initializes the connection and proxy objects
ConnectionInstance = classes.Connection()
ConnectionInstance.initialize(client)
ProxyInstance = classes.connProxy()
ProxyInstance.initialize(SERVER_KEY,ConnectionInstance)

#starts mqtt client message handling
client.loop_start()

#subscribe to server topic to listen to incoming messages
client.subscribe(SERVER_TOPIC,qos=2)

#instaniate the MC and GUI factories and create a dictionary to pass to the mediator so it can create GUI and MC objects
eFactory = classes.Esp32Factory(ConnectionInstance)
pFactory = classes.PicoFactory(ConnectionInstance)
gFactory = classes.GUIFactory(ConnectionInstance)
rFactory = classes.RpiZeroFactory(ConnectionInstance)

factoryDictionary = {
    "ESP32": eFactory,
    "Pico" : pFactory,
    "RpiZero" : rFactory,
    "GUI" : gFactory
}


#instatiate the mediator object and start mediation
mediator = classes.Mediator(ConnectionInstance,factoryDictionary)
mediator.startMediation()

client.loop_end()