import socket

class Client:
    def __init__(self, SERVER='localhost', PORT=5050, FORMAT='utf-8', HEADER_LENGTH=64):
        self.SERVER = SERVER
        self.PORT = PORT
        self.FORMAT = FORMAT
        self.HEADER_LENGTH = HEADER_LENGTH
        self.ADDR = (SERVER, PORT)
        self.DISCONNECT_MESSAGE = "!DISCONNECT"

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(self.ADDR)

    def send_message(self, msg):
        message = msg.encode(self.FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.FORMAT)
        send_length += b' ' * (self.HEADER_LENGTH - len(send_length))
        self.client.send(send_length)
        self.client.send(message)

        print(self.client.recv(2048).decode(self.FORMAT))


client = Client()
client.send_message("Evan is super cool")
