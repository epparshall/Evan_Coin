# Server and Client need to:
    # Update the Blockchain
    # Broadcast transactions

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
