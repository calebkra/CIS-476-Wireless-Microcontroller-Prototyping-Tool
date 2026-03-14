import paho.mqtt.client as mqtt
from queue import Queue
import json
import classes


            

msgQueue = Queue()
ConnectionInstance = classes.Connection()
ProxyInstance = classes.connProxy("1234",ConnectionInstance)


def on_message(client, userdata, msg):
    msgJson = json.loads(msg.payload.decode('utf-8'))
    ProxyInstance.authenticate(msgJson)

client = mqtt.Client()
client.on_message = on_message
client.connect('127.0.0.1', 1883)

client.loop_start()

client.subscribe("Test/Server")

while True:
   msg = ConnectionInstance.getMessage()
   if not msg == None:
       print(msg["Message"])

client.loop_end()