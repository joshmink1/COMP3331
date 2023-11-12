"""
    Sample code for Multi-Threaded Server
    Python 3
    Usage: python3 TCPserver3.py localhost 12000
    coding: utf-8
    
    Author: Wei Song (Tutor for COMP3331/9331)
"""
from socket import *
from threading import Thread
from exceptions import *
from logger import setupLogger
import threading
import authenticate
import sys, select
import time

"""
    Define multi-thread class for client
    This class would be used to define the instance for each connection from each client
    For example, client-1 makes a connection request to the server, the server will call
    class (ClientThread) to define a thread for client-1, and when client-2 make a connection
    request to the server, the server will call class (ClientThread) again and create a thread
    for client-2. Each client will be runing in a separate therad, which is the multi-threading
"""
lock = threading.Lock()

# Setup loggers and files
userLogger = setupLogger('userlog', 'userlog.txt')
messageLogger = setupLogger('messagelog', 'messagelog.txt')

class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket, max_attempt):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        self.username = 'unidentified'
        self.authenticated = False
        self.max_fail_attempt = max_attempt
        self.num_attempt = 0
        self.sleep = False

        print("===== New connection created for: ", clientAddress)
        self.clientAlive = True
        
    def run(self):
        message = ''
        
        while self.clientAlive:
            if (self.sleep == True):
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] " + self.username + " has exceeded the maximum number of password attempts. They are timed out for 10 seconds.")
                start = time.time()
                self.clientSocket.settimeout(0.1)
                # Returns time left until unblock
                while (time.time() - start < 9):
                    try:
                        data = self.clientSocket.recv(1024)
                        message = data.decode()
                        if (message.startswith('user password fulfilled')):
                            message = 'timed out for ' + str(int(10 - (time.time() - start))) + ' seconds for too many incorrect attempts'
                            self.clientSocket.send(message.encode())
                    except timeout:
                        pass
                self.sleep = False
                self.num_attempt = 0
                self.clientSocket.settimeout(None)

            # Receive message from client
            data = self.clientSocket.recv(1024)
            message = data.decode()
            
            # if the message from client is empty, the client would be off-line then set the client as offline (alive=Flase)
            if message == '':
                self.clientAlive = False
                print("===== the user disconnected - ", self.clientAddress)
                break
            
            # Authentication
            if message == 'login':
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [recv] New login request")
                self.process_login()
            elif message.startswith('user credential fulfilled'):
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [recv] User username received. Authenticating username... ")
                username = message.split(":")[1]
                self.process_username(username)
            elif message.startswith('user password fulfilled'):
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [recv] User password received. Authenticating password... ")
                self.process_password(message.split(":")[1])
            elif message.startswith('user udp port'):
                
            # elif message.starts

            # Section 
            elif message == 'download':
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [recv] Download request")
                message = 'download filename'
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] " + message)
                self.clientSocket.send(message.encode())
            else:
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [recv] " + message)
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] Cannot understand this message")
                message = 'Cannot understand this message'
                self.clientSocket.send(message.encode())
    
    """
        You can create more customized APIs here, e.g., logic for processing user authentication
        Each api can be used to handle one specific function, for example:
        def process_login(self):
            message = 'user credentials request'
            self.clientSocket.send(message.encode())
    """
    def process_login(self):
        message = 'user credentials request'
        print('[send] ' + message)
        self.clientSocket.send(message.encode())

    def process_username(self, username):
        try:
            authenticate.verify_user(username)
            message = 'password request'
            print(str(self.clientAddress) + ':{' + self.username + '}' + ' [send] ' + 'Username found in system! Requesting password...')
            self.clientSocket.send(message.encode())
            self.username = username
            return
        except InvalidUsername as err:
            print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] Username was invalid, requesting username again...")
            message = 'invalid user credentials'
            self.clientSocket.send(message.encode())

    def process_password(self, password):
        try:
            authenticate.verify_pass(self.username, password)
            message = 'authentication complete'
            print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] User '" + self.username + "'(" + str(self.clientAddress) + ") has been sucessfully authenticated")
            self.clientSocket.send(message.encode())
            self.authenticated == True
        except InvalidPassword as err:
            self.num_attempt += 1
            print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] Password was invalid, client has " + str(self.max_fail_attempt - self.num_attempt) + " attempts remaining")
            if (self.num_attempt == self.max_fail_attempt):
                message = 'timed out for 10 seconds due to too many failed password attempts'
                self.clientSocket.send(message.encode())
                self.sleep = True
            else:
                message = 'retry password attempt:' + str(self.max_fail_attempt - self.num_attempt)
                self.clientSocket.send(message.encode())
            