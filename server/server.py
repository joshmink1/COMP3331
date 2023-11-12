import sys
from serverProcess import startServer

server_IP = "127.0.0.1"
if (len(sys.argv) != 3):
    print("Please run the command in the following format:\npython3 server.py server_port number_of_consecutive_failed_attempts")
    exit()
if not (sys.argv[2].isnumeric() and 0<int(sys.argv[2])<6):
    print("Invalid number of allowed failed consecutive attempt: "+sys.argv[2]+". The valid value of argument number is an integer between 1 and 5")
    exit()
startServer(server_IP, int(sys.argv[1]), int(sys.argv[2]))