# import threading
# import time
# import socket
#
# class Network:
#     def __init__(self, host='localhost', port=5000):
#         self.host = host
#         self.port = port
#         self.server = None
#         self.lock = threading.Lock()
#         self.message_length = 1024
#         self.message_format = 'utf-8'
#         self.server_ready_event = threading.Event()  # Event to signal when the server is ready
#
#     def start_server(self):
#         # Create a server socket to listen for incoming connections
#         self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.server.bind((self.host, self.port))
#         self.server.listen(5)
#         print(f"\n\nServer started at {self.host}:{self.port}\n")
#
#         # Signal that the server is ready to accept connections
#         self.server_ready_event.set()  # This will let the client know the server is ready
#
#         # Accept connections in a loop
#         while True:
#             client_socket, client_address = self.server.accept()
#             print(f"\nNew connection from {client_address}\n")
#             thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
#             thread.start()
#             print("\nActive connections: " + str(threading.active_count() - 2) + "\n")
#
#     def handle_client(self, client_socket, client_address):
#         print(f"\nNew connection at address: {client_address}\n")
#         connected = True
#
#         while connected:
#             msg = client_socket.recv(self.message_length).decode(self.message_format)
#             if not msg:  # If no message, the client disconnected
#                 print(f"\nClient {client_address} disconnected.\n")
#                 break
#             print(f"\nReceived message from {client_address}: {msg}\n")
#
#         client_socket.close()
#
#     def send_data(self, data, target_ip='localhost', target_port=5000):
#         # Send data to a specific peer
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#             sock.connect((target_ip, target_port))
#             sock.sendall(data.encode('utf-8'))
#
# # Server thread function
# def start_server_thread(network_server):
#     network_server.start_server()
#
# # Client thread function
# def start_client_thread(network_client, port_num, data=""):
#     # network_client.server_ready_event.wait()  # Wait for the server to be ready
#     network_client.send_data(data, target_ip='localhost', target_port=port_num)
#
#
# if __name__ == "__main__":
#     port_num = 5001
#
#     # Create server instance
#     network_server = Network(host='localhost', port=port_num)
#
#     # Start the server in a new thread
#     server_thread = threading.Thread(target=start_server_thread, args=(network_server,))
#     server_thread.daemon = True  # Daemonize the server so it exits when the program ends
#     server_thread.start()
#
#     # Create client instance
#     network_client = Network(host='localhost', port=port_num)
#
#     # Start the client in a new thread
#     client_thread = threading.Thread(target=start_client_thread, args=(network_client, port_num, "Evan is so cool"))
#     client_thread.daemon = True  # Daemonize the client so it exits when the program ends
#     client_thread.start()
#
#     input("Press Enter to exit...")  # Keep the program running

# import socket
# import threading
# import time
#
# HEADER = 64
# PORT = 5050
# SERVER = 'localhost'
# SERVER = socket.gethostbyname(socket.gethostname())
# ADDR = (SERVER, PORT)
# FORMAT = 'utf-8'
# DISCONNECT_MESSAGE = "!DISCONNECT"
#
# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server.bind(ADDR)
#
# def handle_client(conn, addr):
#     print(f"[NEW CONNECTION] {addr} connected")
#     connected = True
#
#     while connected:
#         msg_length = conn.recv(HEADER).decode(FORMAT)
#
#         if msg_length:
#             msg_length = int(msg_length)
#             msg = conn.recv(msg_length).decode(FORMAT)
#
#             if msg == DISCONNECT_MESSAGE:
#                 connected = False
#
#             print(f"[{addr}] {msg}")
#             conn.send("Msg received".encode(FORMAT))
#
#     conn.close()
#
#
# def start():
#     server.listen()
#     print(f"[LISTENING] Server is listening on {SERVER}")
#     while True:
#         conn, addr = server.accept()
#         thread = threading.Thread(target=handle_client, args=(conn, addr))
#         thread.start()
#         print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
#
# print("[STARTING] server is starting")
# start()

import socket
import threading
import time

class Server:
    def __init__(self, SERVER='localhost', PORT=5050, FORMAT='utf-8', HEADER_LENGTH=64):
        self.SERVER = SERVER
        self.PORT = PORT
        self.FORMAT = FORMAT
        self.HEADER_LENGTH = HEADER_LENGTH
        self.ADDR = (SERVER, PORT)
        self.DISCONNECT_MESSAGE = "!DISCONNECT"

    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(self.ADDR)
        self.server.listen()
        print(f"[LISTENING] Server is listening on {self.SERVER}")

        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    def handle_client(self, conn, addr):
        print(f"[NEW CONNECTION] {addr} connected")
        connected = True

        while connected:
            msg_length = conn.recv(self.HEADER_LENGTH).decode(self.FORMAT)

            if msg_length:
                msg_length = int(msg_length)
                msg = conn.recv(msg_length).decode(self.FORMAT)

                if msg == self.DISCONNECT_MESSAGE:
                    connected = False

                print(f"[{addr}] {msg}")
                conn.send("Msg received".encode(self.FORMAT))

        conn.close()

server = Server()
server.start_server()
