"""
    Python 3
    Usage: python3 TCPClient3.py localhost 12000
    coding: utf-8
    
    Author: Wei Song (Tutor for COMP3331/9331)
"""
from socket import *
import sys
import threading
from threading import Thread
import os
import curses
import time
import signal
import datetime

lock = threading.Lock()
timeout_id = 0
p2ptarget = []
receiving = False
commandAlive = True

def runClient(Host, TCPPort, UDPPort):
    global timeout_id
    serverHost = Host
    serverTCPPort = TCPPort
    clientUDPPort = UDPPort
    serverAddress = (serverHost, serverTCPPort)

    UDPThread = threading.Thread(target=UDPSocketRunner, args=(serverHost, clientUDPPort, ),daemon=True)
    UDPThread.start()

    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect(serverAddress)
    hostname=gethostname()
    IPAddr=gethostbyname(hostname)
    print("Your Computer Name is:"+hostname)
    message = 'login'
    print("[send] " + message)
    clientSocket.send(message.encode())

    while True:
        try:
            clientSocket.settimeout(2)
            data = clientSocket.recv(1024)
            timeout_id = 0
            receivedMessage = data.decode()
            time.sleep(0.1)
            if receivedMessage == "":
                pass
            elif receivedMessage == "user credentials request":
                print("[recv] You need to provide username and password to login")
                credentials_username(clientSocket)
            elif receivedMessage.startswith("invalid user credentials"):
                print("[recv] The username provided was invalid. please try again")
                credentials_username(clientSocket)
            elif receivedMessage == "password request":
                print("[recv] Username has been found on the server!")
                credentials_password(clientSocket)
            elif receivedMessage == "authentication complete":
                print("[recv] Authentication complete! You are successfully logged in as '"+ username +"'")
                commandThread = threading.Thread(target=command_hub, args=(clientSocket,), daemon=True)
                commandThread.start()
                message = 'user udp port:' + str(clientUDPPort)
                clientSocket.send(message.encode())
            elif receivedMessage == "download filename":
                print("[recv] You need to provide the file name you want to download")
            elif receivedMessage == 'logout successful':
                print('You have been logged out successfully. We hope to see you soon!')
                clientSocket.shutdown(SHUT_RDWR)
                clientSocket.close()
                sys.exit()
                # os.kill(os.getpid(), signal.SIGINT)
            elif receivedMessage.startswith('p2p request'):
                splitted = receivedMessage.split(':')
                lock.acquire()
                p2ptarget.append(str(splitted[1]))
                p2ptarget.append(str(splitted[2]))
                lock.release()
            elif receivedMessage == 'group msg sent':
                print("Group message has successfully been sent")
            elif receivedMessage.startswith('groupmsg'):
                args = receivedMessage.split(':')
                printmessage = str(datetime.datetime.now()) + ', ' + args[1] + ', ' + args[2] + ': ' + args[3] 
                print(printmessage + '\n(' + "\033[1;37;42m"  +username + "\033[0m" + ') ', end="") 
            elif receivedMessage.startswith('not joined group'):
                args = receivedMessage.split(':')
                print("You must first join this group to send messages. To join run /joingroup " + args[1])
            elif receivedMessage.startswith('incoming invite'):
                print("You have an incoming invite to join the group chat: " + receivedMessage.split(':')[1] + '. To join, enter /joingroup ' + receivedMessage.split(':')[1] + '\n(' + "\033[1;37;42m"  +username + "\033[0m" + ') ', end="")
            elif receivedMessage == 'joined group':
                print("You have successfully joined this group, you can now send messages in this group chat.")
            elif receivedMessage == 'no group invite':
                print("You are not added in this group by the creator")
            elif receivedMessage == 'already accepted':
                print("You have already joined this group")
            elif receivedMessage == 'group does not exist':
                print("The group chat does not exist")
            elif receivedMessage.startswith('Group chat (Name'):
                print(receivedMessage)
            elif receivedMessage == 'receiver unavaliable':
                print("[recv] User is either invalid or not online")
            elif receivedMessage == 'pm sent':
                print("[recv] Message has been sucessfully sent at " + str(datetime.datetime.now()))
            elif receivedMessage.startswith('incoming private message'):
                print("\n[recv] Private message from " + "\033[1;37;42m" + receivedMessage.split(":")[2] + "\033[0m" + ' (' + str(datetime.datetime.now()) + ')'+': ' + receivedMessage.split(":")[1] + '\n(' + "\033[1;37;42m"  +username + "\033[0m" + ') ', end="")
                message = 'message received:' + receivedMessage.split(":")[2]
                clientSocket.send(message.encode())

            elif receivedMessage.startswith("activeuserlist"):
                users = receivedMessage.split('%')
                counter = 0
                time.sleep(0.05)
                print('\n== ACTIVE USERS')
                for user in users[1:]:
                    if not user.startswith("username: " + username):
                        counter += 1
                        print(user)
                if counter == 0:
                    print("There are no other users online")
            elif receivedMessage.startswith("group chat created"):
                args = receivedMessage.split(':')
                printMessage = "Group chat room has been created, room name: " + args[1] + ', users in this room: '
                for user in args[2:]:
                    printMessage = printMessage + user + ' '
                print(printMessage)
            elif receivedMessage.startswith("timed out"):
                print("[recv] This user is currently " + receivedMessage)
                credentials_password(clientSocket)
            elif receivedMessage.startswith("retry password attempt"):
                print("[recv] The password you entered was wrong. You have " + receivedMessage.split(':')[1] + " tries remaining")
                credentials_password(clientSocket)
            else:
                print("[recv] Message makes no sense")
        except timeout:
            if (timeout_id == 1):
                print("\nMessage could not be delivered\n(" + "\033[1;37;42m" + username + "\033[0m" + ") ", end="")
            timeout_id = 0

def credentials_username(socket):
    global username
    #Remove whitespaces
    username = input("Please enter your username: ")
    message = 'user credential fulfilled:' + username
    print("[send] Verifying username on the server...")
    socket.send(message.encode())
    
def credentials_password(socket):
    password = input("Please enter your password: ")
    message = 'user password fulfilled:' + password
    print("[send] Verifying password on the server...")
    socket.send(message.encode())

# Maybe replace this with a graceful shutdown
def continue_prompt():
    ans = input('\nDo you want to continue(y/n) :')
    if ans == 'y' or ans == 'yes':
        return
    else:
        # close the socket
        clientSocket.close()
        exit()

def command_hub(socket):
    global timeout_id
    flag = False
    global commandAlive
    while commandAlive:
        # os.system('cls' if os.name == 'nt' else 'clear')
        print("Please enter one of the following commands:")
        print("/msgto")
        print("/activeuser")
        print("/creategroup")
        print("/joingroup")
        print("/groupmsg")
        print("/logout")
        print("/p2pvideo")
        if (flag == True):
            print("Please ensure the command entered is correct")
            flag = False
        time.sleep(0.35)
        command = input("(" + "\033[1;37;42m" +username + "\033[0m" + ") ")
        cmdArgs = command.strip().split(' ')
        if (cmdArgs[0] == '/msgto' and len(cmdArgs) >= 3):
            chatMessage = ' '.join(cmdArgs[2:])
            message = 'pm:' + str(cmdArgs[1]) + ':' + str(chatMessage)
            timeout_id = 1
            socket.send(message.encode())
            print('Sending message . . .')
        elif (command == '/activeuser'):
            message = 'active userlist'
            socket.send(message.encode())
        elif (cmdArgs[0] == '/creategroup' and len(cmdArgs) > 2):  
            message = 'create group:' + cmdArgs[1]
            for user in cmdArgs[2:]:
                message = message + ':' + user
            socket.send(message.encode())
        elif (cmdArgs[0] == '/joingroup' and len(cmdArgs) == 2):
            message = 'join group:' + cmdArgs[1]
            socket.send(message.encode())
        elif (cmdArgs[0] == '/groupmsg' and len(cmdArgs) >= 3):
            message = 'group message:' + cmdArgs[1]
            for arg in cmdArgs[2:]:
                message = message + ':' + arg
            socket.send(message.encode())
        elif (command == '/logout'):
            message = 'logout'
            socket.send(message.encode())
            commandAlive = False
        elif (cmdArgs[0] == '/p2pvideo' and len(cmdArgs) == 3):
            # Only checking if user is active and get their Address and UDP Port from server
            message = 'p2pcheck:' +  cmdArgs[1]
            lock.acquire()
            p2ptarget.append(cmdArgs[2])
            lock.release()
            socket.send(message.encode())
        else:
            flag = True



def UDPSocketRunner(Host, UDPPort):
    global receiving
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.bind(('127.0.0.1', UDPPort))
    send_checker = threading.Thread(target=UDPSendRunner, args=(clientSocket,),daemon=True)
    send_checker.start()
    received = 0
    buf = 8192
    queue = []
    while commandAlive == True:
        # clientSocket.listen()
        # clientSocket, clientAddress = clientSocket.accept()
        header, clientAddress = clientSocket.recvfrom(buf)
        decoded_header = header.decode('latin-1')
        filename = decoded_header.split(':')[0]
        filesize = int(decoded_header.split(':')[1])
        sending_user = decoded_header.split(':')[2]
        print("== Receiving file from " + sending_user + ': ' + filename + ' (size: ' + str(filesize) + ' bytes)')
        clientSocket.settimeout(0.5)
        lock.acquire()
        receiving = True
        lock.release()
        f = open('received_' + filename, 'wb')
        data, addr = clientSocket.recvfrom(buf)
        lock.acquire()
        queue.append(data)
        lock.release()
        counter = 0
        queuethread = threading.Thread(target=queueManager, args=(filename, queue, f), daemon=True)
        queuethread.start()
        while(data != ''):
            # print(data.decode('latin-1'))                
            if (received / filesize > counter):
                    # print('yoo: ' + str(received/filesize) + 'b' + str(filesize))
                    print(str(int(counter * 100)) + '% Received')
                    counter += 0.1
            received += buf
            try:
                data, addr = clientSocket.recvfrom(buf)
                # lock.acquire()
                queue.append(data)
                # lock.release()
            except timeout as e:
                print('downloaded')
                break
        lock.acquire()
        receiving = False
        lock.release()
        f.close()
        received = 0
        clientSocket.settimeout(None)


def queueManager(filename, queue, file):
    # Constantly monitor queue while actively receiving or while queue is not empty
    while (len(queue) != 0 or receiving == True) and commandAlive == True:
        # print('queue:' + str(len(queue)) + ': ' + str(receiving))# end='')
        if len(queue) != 0:
            lock.acquire()
            file.write(queue.pop(0))
            lock.release()


def UDPSendRunner(socket):
    global p2ptarget
    while commandAlive == True:
        buf = 8192
        lock.acquire()
        senderUpdate = p2ptarget
        lock.release()
        if (len(senderUpdate) > 1):
            time.sleep(0.5)
            print('\n== SENDING FILE')
            print('== PLEASE DO NOT ENTER COMMANDS UNTIL SENDING IS COMPLETE')
            address = (senderUpdate[1], int(senderUpdate[2]))
            socket.connect(address)
            filesize = os.path.getsize(senderUpdate[0])
            message = senderUpdate[0] + ':' + str(filesize) + ':' + username
            socket.sendto(message.encode('latin-1'), address)
            file = open(senderUpdate[0], "rb")
            data = file.read(buf)
            sent = 0
            counter = 0
            socket.settimeout(1)
            while(data.decode('latin-1') != ''):
                if (sent / filesize > counter):
                    print(str(int(counter * 100)) + '% Sent')
                    counter += 0.1
                socket.sendto(data, address)
                time.sleep(0.01)
                data = file.read(buf)
                sent += buf
            print('File successfully sent' + '\n(' + "\033[1;37;42m"  +username + "\033[0m" + ') ', end="")
            p2ptarget = []
