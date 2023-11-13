from socket import *
from threading import Thread
from exceptions import *
from datetime import datetime
import threading
import authenticate
import logger
import time
# from clientClass import ClientThread

lock = threading.Lock()

# Setup loggers
userLogger = logger.setupLogger('userlog', 'userlog.txt')
messageLogger = logger.setupLogger('messagelog', 'messagelog.txt')
groupchatLogger = logger.setupLogger('groupchatlog', 'groupchat.txt')
file = open('groupchat.txt', 'w')
file.close()
blocked = []
start = time.time()
onlineClients = []

def startServer(Host, Port, max_attempt):
    serverHost = Host
    serverPort = Port
    serverAddress = (serverHost, serverPort)
    # define socket for the server side and bind address
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(serverAddress)
    print("===== Server is running =====")
    print("===== Waiting for connection request from clients... =====")
    print("===== The server is running on IP Address: " + serverHost + " ====")
    print("===== The server is listening for TCP requests on port: " + str(serverPort) + " =====")
    while True:
        try:
            serverSocket.listen()
            clientSockt, clientAddress = serverSocket.accept()
            clientThread = ClientThread(clientAddress, clientSockt, max_attempt)
            clientThread.start()
            # lock.acquire()
            onlineClients.append(clientThread)
            # lock.release()
        except ConnectionResetError as err:
            # Maybe add graceful shutdown later
            print("A user has disconnected ungracefully")

class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket, max_attempt):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        self.usernameattempt = 'unidentified'
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
                global start
                lock.acquire()
                blocked.append(self.username)
                start = time.time()
                starttime = start
                lock.release()
                print(str(self.clientAddress) + ':{' + self.username + '}' + " [send] " + self.username + " has exceeded the maximum number of password attempts. They are timed out for 10 seconds.")
                self.clientSocket.settimeout(0.1)
                # Returns time left until unblock
                while (time.time() - starttime < 9):
                    try:
                        data = self.clientSocket.recv(1024)
                        message = data.decode()
                        if (message.startswith('user password fulfilled')):
                            message = 'timed out for ' + str(int(10 - (time.time() - starttime))) + ' seconds for too many incorrect attempts'
                            self.clientSocket.send(message.encode())
                    except timeout:
                        pass
                lock.acquire()
                blocked.remove(self.username)
                lock.release()
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
                lock.acquire()
                userLogger.info(self.userLogFormat(message.split(":")[1]))
                lock.release()
                message = 'authenticated'

            # Message
            elif message.startswith('pm'):
                try:
                    receiverSocket = self.socketFinder(message.split(":")[1])
                    lock.acquire()
                    messageLogger.info(self.messageLogFormat(message.split(":")[2], message.split(":")[1]))
                    lock.release()
                    messageReceiver = 'incoming private message:' + message.split(":")[2] + ':' + self.username
                    receiverSocket.send(messageReceiver.encode())
                except InvalidSocket:
                    errorMessage = 'receiver unavaliable'
                    self.clientSocket.send(errorMessage.encode())
            elif message.startswith('message received'):
                # Assuming this socket will always be valid (no try except)
                senderSocket = self.socketFinder(message.split(":")[1])
                senderMessage = 'pm sent'
                senderSocket.send(senderMessage.encode())
            
            # activeuser
            elif message == 'active userlist':
                message = self.activeUsers()
                self.clientSocket.send(message.encode())
            
            # Group message
            elif message.startswith('create group'):
                args = message.split(':')
                invalidFlag = False
                if self.checkGroupexists(args[1]):
                    sendMessage = 'Group chat (Name: ' + args[1] + ') already exists'
                    self.clientSocket.send(sendMessage.encode())
                    invalidFlag = True
                for user in args[2:]:
                    if not self.checkUserValid(user):
                        self.clientSocket.send('receiver unavaliable'.encode())
                        invalidFlag = True
                        break
                if invalidFlag == False:
                    self.createGroup(args)

            elif message.startswith('join group'):
                args = message.split(':')
                if not self.checkGroupexists(args[1]):
                    self.clientSocket.send('group does not exist'.encode())
                else:
                    self.joinGroup(args[1])

            elif message.startswith('group message'):
                args = message.split(':')
                flag = True
                if not self.checkGroupexists(args[1]):
                    sendMessage = 'group does not exist'
                    self.clientSocket.send(sendMessage.encode())
                    flag = False
                groupStatus = self.checkUserInGroup(args[1])
                # print("beeboo:" + groupStatus)
                if groupStatus == -1 and flag == True:
                    self.clientSocket.send('no group invite'.encode())
                elif groupStatus == 0 and flag == True:
                    messagesend = 'not joined group:' + args[1]
                    self.clientSocket.send(messagesend.encode())
                elif groupStatus == 1 and flag == True:
                    templogger = logger.setupLogger('messagelogger', args[1] + '_messagelog.txt')
                    templogger.info(self.groupMessageFormat(args))
                    templogger.handlers.clear()
                    self.clientSocket.send('group msg sent'.encode())
                    # lock.acquire()
                    users = self.getUsersInGroup(args[1])
                    for user in users:
                        print(user)
                        if user != self.username:
                            messagesend = 'groupmsg:' + args[1] + ':' + str(self.username) + ':'
                            for arg in args[2:]:
                                messagesend = messagesend + arg + ' ' 
                            self.socketFinder(user).send(messagesend.encode())
                    # lock.release()

            # Logout

            elif message == 'logout':
                print("===== user "+ self.username +" disconnected - ", self.clientAddress)
                self.removeUser()
                self.clientSocket.send('logout successful'.encode())
                self.clientSocket.shutdown(SHUT_RDWR)
                self.clientSocket.close()
                self.clientAlive = False

            # p2p request
            elif message.startswith('p2pcheck'):
                splitted = message.split(':')
                if self.checkOnline(splitted[1]):
                    message = 'p2p request:' + self.getUserInfo(splitted[1])
                    print('quiff' + message)
                    self.clientSocket.send(message.encode())
                else:
                    message = 'receiver unavaliable'
                    self.clientSocket.send(message.encode())

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
            self.usernameattempt = username
            print(str(self.clientAddress) + ':{' + self.usernameattempt + '}' + ' [send] ' + 'Username found in system! Requesting password...')
            self.clientSocket.send(message.encode())
            return
        except InvalidUsername as err:
            print(str(self.clientAddress) + ':{' + self.usernameattempt + '}' + " [send] Username was invalid, requesting username again...")
            message = 'invalid user credentials'
            self.clientSocket.send(message.encode())

    def process_password(self, password):
        try:
            print("buckets")
            if (self.is_blocked()):
                print("buckets")
                lock.acquire()
                message = 'timed out for ' + str(int(10 - (time.time() - start))) + ' seconds for too many incorrect attempts'
                lock.release()
                self.clientSocket.send(message.encode())
                return
            print("buckets")
            authenticate.verify_pass(self.usernameattempt, password)
            message = 'authentication complete'
            self.username = self.usernameattempt
            print("buckets")
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
    
    def is_blocked(self):
        print("bunnies")
        # lock.acquire()
        print("bunnies")
        for i in blocked:
            print("oogabooga: " + i)
            print("oogabooga: " + self.username)
            if self.username == i:
                # lock.release()
                return True
        # lock.release()
        return False

    def userLogFormat(self, UDPPort):
        string = logger.getSeqNum('userlog.txt') + '; ' + str(datetime.now()) + '; ' + self.username + '; ' + self.clientAddress[0] + '; ' + str(UDPPort)
        return string

    def messageLogFormat(self, message, receiver):
        string = logger.getSeqNum('messagelog.txt') + '; ' + str(datetime.now()) + '; ' + receiver + '; ' + message
        return string

    def groupchatLogFormat(self, users, groupname, numUsers):
        string = groupname + ' 1'
        num = 0
        while num < numUsers - 1:
            string = string + '0'
            num += 1
        for user in users:
            string = string + ' ' + user
        return string

    def groupMessageFormat(self, args):
        lock.acquire()
        string = logger.getSeqNum(args[1] + '_messagelog.txt') + '; ' + str(datetime.now()) + '; ' + self.username + ';'
        for arg in args[2:]:
            string = string + ' ' + arg
        lock.release()
        return string

    def socketFinder(self, username):
        lock.acquire()
        for thread in onlineClients:
            if (thread.username == username):
                lock.release()
                return thread.clientSocket
        lock.release()
        raise InvalidSocket

    def activeUsers(self):
        counter = 0
        users = 'activeuserlist'
        with open('userlog.txt', 'r') as f:
            for line in f:
                counter += 1
                user = line.split('; ')
                string = "username: " + user[2] + "; Online for: " + str(datetime.now() - datetime.strptime(user[1][:-7], '%Y-%m-%d %H:%M:%S')) + "; IP Address: " + user[3] + '; Port Number: ' + user[4]
                users = users + '%' + string
        return users
    
    def checkGroupexists(self, groupname):
        lock.acquire()
        with open('groupchat.txt', 'r') as f:
            for line in f:
                user = line.split(' ')
                if user[0] == groupname: 
                    lock.release()
                    return True
        lock.release()
        return False

    def checkUserValid(self, user):
    # Checks if the user is online
        lock.acquire()
        with open('userlog.txt', 'r') as f:
            for line in f:
                loguser = line.split('; ')
                # print("ioyaaa:" + str(loguser[2]) + ':' + str(user))
                if loguser[2] == user:
                    lock.release()
                    return True
        lock.release()
        return False
    
    def createGroup(self, args):
        lock.acquire()
        # print('wappin:' + args[0] + ' ' + args[1] + ' ' + args[2])
        usernames = args[2:]
        # Assuming creator of the group does not have to join his own group
        usernames.insert(0, self.username)
        # print('ayo:' + self.username)
        # for arg in usernames:
            # print("shheedh:" + arg)
        groupchatLogger.info(self.groupchatLogFormat(usernames, args[1], len(usernames)))
        file = open(args[1] + '_messagelog.txt', 'w')
        file.close()
        message = 'group chat created:' + args[1]
        for user in args[2:]:
            message = message + ':' + user
        self.clientSocket.send(message.encode())
        for user in args[2:]:
            for client in onlineClients:
                if client.username == user:
                    sendMessage = 'incoming invite:' + args[1]
                    client.clientSocket.send(sendMessage.encode())
        lock.release()

    def joinGroup(self, groupname):
        lock.acquire()
        flag = False
        with open('groupchat.txt', 'r') as fr:
            lines = fr.readlines()
            with open('groupchat.txt', 'w') as fw:
                for line in lines:
                    if line.startswith(groupname):
                        updatedLine = self.getUpdated(line, groupname)
                        if updatedLine == line:
                            flag = True
                        fw.write(updatedLine)
                    else:
                        fw.write(line)
        if (flag == False):
            self.clientSocket.send('joined group'.encode())
        lock.release()
    
    def getUpdated(self, line, groupname):
        checkFlag = False
        updatePos = len(groupname) + 1
        users = line.strip().split(' ')
        linelist = list(line)
        for user in users:
            # print('booga:'+user+';'+self.username)
            if (user == self.username):
                checkFlag = True
                break
            updatePos += 1    
        updatePos -= 2
        if checkFlag == False:
            self.clientSocket.send('no group invite'.encode())
            return line
        if (linelist[updatePos] == '1'):
            self.clientSocket.send('already accepted'.encode())
            return line
        linelist[updatePos] = '1'
        return ''.join(linelist)

    def checkUserInGroup(self, groupname):
        # returns -1 if not in group, 0 if in group but not joined, 1 if joined group
        # Assumes group exists
        lock.acquire()
        with open('groupchat.txt', 'r') as f:
            for line in f:
                group = line.strip().split(' ')
                if group[0] == groupname: 
                    linelist = list(line)
                    counter = 0
                    for userlog in group[1:]:
                        counter += 1
                        if userlog == self.username:
                            lock.release()
                            return int(linelist[len(groupname) + counter - 1])
        lock.release()
        return -1

    def getUsersInGroup(self, groupname):
        lock.acquire()
        users = []
        with open('groupchat.txt', 'r') as f:
            for line in f:
                group = line.strip().split(' ')
                if group[0] == groupname: 
                    for userlog in group[2:]:
                        if (self.checkOnline(userlog)):
                            users.append(userlog)
        lock.release()
        return users
    
    def checkOnline(self, user):
        # lock.acquire()
        for client in onlineClients:
            if client.username == user:
                # lock.release()
                return True
        # lock.release()
        return False

    def getUserInfo(self, user):
        lock.acquire()
        users = []
        string = ''
        with open('userlog.txt', 'r') as f:
            for line in f:
                userlog = line.strip().split('; ')
                if userlog[2] == user: 
                    print('cc:' + userlog[2] + userlog[3] + userlog[4])
                    string = userlog[3] + ':' + userlog[4]
        lock.release()
        return string

    def removeUser(self):
        lock.acquire()
        flag = False
        counter = 0
        for client in onlineClients:
            if client.username == self.username:
                onlineClients.remove(client)
        with open('userlog.txt', 'r') as fr:
            lines = fr.readlines()
            with open('userlog.txt', 'w') as fw:
                for line in lines:
                    splitted = line.strip().split('; ')
                    if splitted[2] == self.username:
                        counter = -1
                    else:
                        linelist = list(line)
                        linelist[0] = str(int(linelist[0]) + counter)
                        fw.write(''.join(linelist))
        lock.release()