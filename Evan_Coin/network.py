class Network:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.peers = []  # List of connected peers
        self.server = None
        self.lock = threading.Lock()

    def start_server(self):
        # Create a server socket to listen for incoming connections
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"Server started at {self.host}:{self.port}")

        # Accept connections in a loop
        while True:
            client_socket, client_address = self.server.accept()
            print(f"New connection from {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        data = client_socket.recv(1024).decode('utf-8')
        if data:
            print(f"Received data: {data}")
            # Handle incoming data (transactions or blocks)
            # Here you can add logic to parse the data and update the blockchain
        client_socket.close()

    def send_data(self, data, target_ip='localhost', target_port=5000):
        # Send data to a specific peer
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((target_ip, target_port))
            sock.sendall(data.encode('utf-8'))
