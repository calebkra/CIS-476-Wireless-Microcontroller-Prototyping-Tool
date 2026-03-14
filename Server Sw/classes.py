from queue import Queue

class Connection:
    MessageList = Queue()

    def recieveMessage(self,msg):
        self.MessageList.put(msg)
    
    def getMessage(self):
        if not self.MessageList.empty():
            return self.MessageList.get()
        else:
            return None


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

