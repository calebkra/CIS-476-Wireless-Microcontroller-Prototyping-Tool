import paho.mqtt.client as mqtt
from queue import Queue
import json
import classes


def on_message(client, userdata, msg):
    msgJson = json.loads(msg.payload.decode('utf-8'))
    ProxyInstance.authenticate(msgJson)

client = mqtt.Client()
client.on_message = on_message
client.connect('127.0.0.1', 1883)

#msgQueue = Queue()
ConnectionInstance = classes.Connection(client)
ProxyInstance = classes.connProxy("1234",ConnectionInstance)

client.loop_start()

#subscribe to server topic to listen to incoming messages
client.subscribe("Test/Server",qos=2)

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

e1 = eFactory.createMicrocontroller("01")
p1 = pFactory.createMicrocontroller("02")
g1 = gFactory.createGUI("03")
#may need to add r1 for RpiZero or remove three lines above

mediator = classes.Mediator(ConnectionInstance,factoryDictionary)


mediator.startMediation()

client.loop_end()