from clientProcess import runClient
import sys

if len(sys.argv) != 4:
    print("Please run the command in the following format:\npython3 client.py server_IP server_port client_udp_server_port")
    exit()

try:
    runClient(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
except ConnectionRefusedError as e:
    print("There was an error attempting to connect to the server. Please ensure the following:\n - The server is running before attempting to run a client instance\n - The server IP address is correctly given as an argument")