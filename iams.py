import socket
import json
import time

class ChrisIPCServer:

    def __init__(self, address, port=0, unix=False):
        """Initializes the server object with address/location to listen on.

        Keyword arguments:
        address -- the ip address or location of the socket to listen on.
        port -- the port to listen on, defaults to 0 so it can be omitted when
        using unix sockets..
        unix -- Whether this is a unix socket or not, defaults to false.

        """
        socket.setdefaulttimeout(0.01)
        if unix:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(address)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((address, port))

        self.sock.listen(1)
        self.connections = []
        self.messageQueue = MessageQueue()
        self.connectionCount = 0

    def update(self):
        """Checks for new connections or data to the socket.

        Any new connections are added to connections list as (socket, 
        socketID) , and any received messages will go in messageQueue as a 
        tuple (message, messageID, socketID)

        """
        newConns = True
        while(newConns):
            try:
                conn,addr = self.sock.accept()
                self.connections.append((conn, self.connectionCount))
                self.connectionCount+=1
            except socket.timeout:
                newConns = False
        #splitlines() is used because multiple sends before a recv causes it
        #to read them all as a single send.
        for conn in self.connections:
            try:
                message = conn[0].recv(4096)
                messages = message.splitlines()
                for message in messages:
                    decodedMessage = json.loads(message)
                    self.messageQueue.enqueue((decodedMessage[0], decodedMessage[1], decodedMessage[2], conn[1]))
                    if not decodedMessage[2]:
                        self.reply(None, decodedMessage[1], conn[1])
            except socket.timeout:
                pass

    def nextMessage(self):
        """Gets the next message from the queue, returns nothing when the
        queue is empty.

        Returns a tuple in the form of (message, messageID, responseExpected,
        socketID)
        
        """
        return self.messageQueue.dequeue()

    def reply(self, message, messageID, socketID):
        """Sends a reply to the client socket where message was recieved
        
        Keyword arguements:
        message -- can not be None, as that signifies an acknowledgement.
        messageID -- ID of the message that this reply is in response to.
        socketID -- ID of the socket where the message can from.

        """
        encodedMessage = json.dumps((message, messageID))
        self.connections[socketID][0].send(encodedMessage + '\n')

class ChrisIPCClient:
    
    def __init__(self, address, port=0, unix=False, maxMessageID=65535, timeout=1):
        """Initializes the client object with where to connect to.

        Keyword arguments:
        address -- the ip address or location of the socket to connect to.
        port -- the port to connect to, defaults to 0 so it can be omitted when
        using unix sockets.
        unix -- Whether this is a unix socket or not, defaults to false.
        maxMessageID -- this is the point at which the message IDs roll over.
        timeout -- this is how long in seconds to wait before resending a
        message that may have been lost.

        """
        if unix:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(address)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((address,port))
        self.messagesSent = []
        self.responseQueue = []
        self.nextID = 0
        self.maxID = maxMessageID

    def send(self, message, response=False):
        """Sends a message to the server.

        Keyword arguments:
        message -- message to be sent, any base object can be sent.
        response -- whether the message is expecting a response, will be sent
        to the server.

        Returns: returns the ID of the message that was sent.

        """
        messageID = self.getNextID()
        encodedMessage = json.dumps((message,messageID,response))
        self.messagesSent.append((encodedMessage, messageID, response, time.time()))
        #'\n' is appended so the server class can split up the different sends.
        self.sock.send(encodedMessage + '\n')
        return messageID


    def update(self):
        """checks for messages that have timed out and resends them, and for 
        responses to sent messages.
        
        """
        response = self.sock.recv(4096)
        responses = response.splitlines()
        for response in responses:
            decodedResponse = json.loads(response)
            if decodedResponse[0] != None:
                self.responseQueue.append((decodedResponse[0],decodedResponse[1]))
            self.removeMessage(decodedResponse[1])
        
        for message in self.messagesSent:
            if (time.time() - message[3]) >= self.timeout:
                self.sock.send(message[0])
                self.messagesSent[self.messagesSent.index(message)][3] = time.time()


    def getNextID(self):
        """Generator for message IDs"""
        if self.nextID > self.maxID:
            self.nextID = 0
        nextID = self.nextID
        self.nextID+=1
        return nextID

    def removeMessage(self, messageID):
        """takes the ID of a message, looks it up and removes it"""
        for message in self.messagesSent:
            if message[1] == messageID:
                self.messagesSent.remove(message)

    def getResponse(self, messageID):
        """Gets a message from the responseQueeu by messageID"""
        for response in self.responseQueue:
            if response[1] == messageID:
                return response[0]

        
class MessageQueue:

    def __init__(self):
        """message queue with guarenteed unique messages."""
        self.queue = []
        self.set = set()

    def enqueue(self,object):
        """adds object to the queue.

        keyword arguments:
        object -- must be immutable.

        """
        if object not in self.set:
            self.set.add(object)
            self.queue.append(object)

    def dequeue(self):
        """gets the next item from the queue."""
        if len(self.queue) > 0 and len(self.set) > 0:
            nextmessage = self.queue.pop(0)
            self.set.remove(nextmessage)
            return nextmessage
