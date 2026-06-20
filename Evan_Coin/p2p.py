import json
import socket
import struct
import threading

from Evan_Coin.block import Block
from Evan_Coin.transaction import Transaction

# Message types exchanged between peers.
MSG_NEW_TRANSACTION = "NEW_TRANSACTION"
MSG_NEW_BLOCK = "NEW_BLOCK"
MSG_CHAIN_REQUEST = "CHAIN_REQUEST"
MSG_CHAIN_RESPONSE = "CHAIN_RESPONSE"
MSG_PEER_DISCOVERY = "PEER_DISCOVERY"
MSG_PEER_LIST = "PEER_LIST"
MSG_PING = "PING"
MSG_PONG = "PONG"


class P2PNode:
    """TCP P2P node for block/transaction propagation and chain synchronization."""

    def __init__(self, blockchain, host="127.0.0.1", port=5050, bootstrap_peers=None):
        self.blockchain = blockchain
        self.host = host
        self.port = port
        self.bootstrap_peers = list(bootstrap_peers or [])

        # _blockchain_lock: serializes every read/write of blockchain state touched
        # by this node — chain height, pending_transactions, signatures, balances,
        # add_block(), replace_chain(), and serialize_chain().
        self._blockchain_lock = threading.Lock()
        # _peers_lock: serializes every read/write of self.peers (add, remove,
        # snapshot for gossip/sync, and peer-discovery responses).
        self._peers_lock = threading.Lock()

        self.peers = set()
        self._server_socket = None
        self._running = False
        self._server_thread = None

    def start(self):
        """Start the TCP server, connect to bootstrap peers, and sync chains."""
        self._running = True
        self._server_thread = threading.Thread(
            target=self._run_server, name=f"p2p-server-{self.port}", daemon=True
        )
        self._server_thread.start()

        for peer_host, peer_port in self.bootstrap_peers:
            if (peer_host, peer_port) != (self.host, self.port):
                self._connect_to_peer(peer_host, peer_port)

        self.sync_with_peers()

    def stop(self):
        """Stop accepting connections and close the server socket."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

    def get_chain_height(self):
        """Return chain height under _blockchain_lock."""
        with self._blockchain_lock:
            return self.blockchain.get_chain_height()

    def sync_with_peers(self):
        """Request chains from all known peers and adopt the longest valid chain."""
        with self._peers_lock:
            peers = list(self.peers)

        for peer in peers:
            self._request_chain_sync(peer)

    def broadcast_new_block(self, block):
        """Gossip a newly mined block to all known peers."""
        message = {
            "type": MSG_NEW_BLOCK,
            "payload": {"block": block.to_dict()},
        }
        self._gossip(message)

    def broadcast_new_transaction(self, transaction, signature):
        """Gossip a new pending transaction to all known peers."""
        message = {
            "type": MSG_NEW_TRANSACTION,
            "payload": {
                "transaction": transaction.to_dict(),
                "signature": signature,
            },
        }
        self._gossip(message)

    def _gossip(self, message, exclude_peer=None):
        """Broadcast a message to every known peer (gossip-style)."""
        with self._peers_lock:
            peers = list(self.peers)

        for peer in peers:
            if peer == exclude_peer:
                continue
            try:
                self._send_to_peer_one_way(peer, message)
            except (OSError, json.JSONDecodeError, ValueError):
                self._remove_peer(peer)

    def _run_server(self):
        """Accept inbound TCP connections (thread-per-connection)."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen()
        self._server_socket.settimeout(1.0)

        while self._running:
            try:
                conn, addr = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            thread = threading.Thread(
                target=self._handle_connection,
                args=(conn, addr, None),
                daemon=True,
            )
            thread.start()

    def _connect_to_peer(self, host, port):
        """Open an outbound TCP connection to a peer."""
        if (host, port) == (self.host, self.port):
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        try:
            sock.connect((host, port))
        except OSError:
            sock.close()
            return

        self._add_peer(host, port)
        thread = threading.Thread(
            target=self._handle_connection,
            args=(sock, (host, port), (host, port)),
            daemon=True,
        )
        thread.start()

    def _handle_connection(self, conn, addr, peer_address):
        """Process messages on a single TCP connection."""
        remote_peer = peer_address or (addr[0], addr[1])
        if remote_peer != (self.host, self.port):
            self._add_peer(*remote_peer)

        try:
            if peer_address is not None:
                # Outbound connections announce this node and request chain sync.
                self._send_peer_discovery(conn)
                self._request_chain_sync_on_socket(conn)

            while self._running:
                message = self._recv_message(conn)
                if message is None:
                    break
                self._dispatch_message(message, conn, remote_peer)
        except (OSError, json.JSONDecodeError, ValueError, struct.error):
            pass
        finally:
            conn.close()
            self._remove_peer(remote_peer)

    def _dispatch_message(self, message, conn, remote_peer):
        """Route an incoming message to the appropriate handler."""
        msg_type = message.get("type")
        payload = message.get("payload", {})

        if msg_type == MSG_NEW_TRANSACTION:
            self._handle_new_transaction(payload)
            self._gossip(message, exclude_peer=remote_peer)
        elif msg_type == MSG_NEW_BLOCK:
            if self._handle_new_block(payload):
                self._gossip(message, exclude_peer=remote_peer)
        elif msg_type == MSG_CHAIN_REQUEST:
            self._handle_chain_request(conn)
        elif msg_type == MSG_CHAIN_RESPONSE:
            self._handle_chain_response(payload)
        elif msg_type == MSG_PEER_DISCOVERY:
            peer_list = self._handle_peer_discovery(payload)
            self._send_message(
                conn,
                {"type": MSG_PEER_LIST, "payload": {"peers": peer_list}},
            )
        elif msg_type == MSG_PEER_LIST:
            self._handle_peer_list(payload)
        elif msg_type == MSG_PING:
            self._send_message(conn, {"type": MSG_PONG, "payload": {}})
        elif msg_type == MSG_PONG:
            pass

    def _handle_new_transaction(self, payload):
        """Add a received transaction to the pending pool under _blockchain_lock."""
        try:
            transaction = Transaction.from_dict(payload["transaction"])
            signature = payload["signature"]
        except (KeyError, TypeError, ValueError):
            return

        with self._blockchain_lock:
            if transaction in self.blockchain.pending_transactions:
                return
            try:
                if not Transaction.verify_signature(transaction, signature):
                    return
            except ValueError:
                return

            sender_balance = self.blockchain.balances.get(transaction.sender)
            if sender_balance is None:
                from Evan_Coin.wallet import Wallet

                sender_balance = Wallet.get_balance(self.blockchain, transaction.sender)
            if sender_balance < transaction.amount + transaction.fee:
                return

            self.blockchain.signatures.append(signature)
            self.blockchain.pending_transactions.append(transaction)

    def _handle_new_block(self, payload):
        """Validate and append a received block under _blockchain_lock."""
        try:
            block = Block.from_dict(payload["block"])
        except (KeyError, TypeError, ValueError):
            return False

        with self._blockchain_lock:
            return self.blockchain.add_block(block)

    def _handle_chain_request(self, conn):
        """Respond with the local chain under _blockchain_lock."""
        with self._blockchain_lock:
            chain = self.blockchain.serialize_chain()
            height = self.blockchain.get_chain_height()

        self._send_message(
            conn,
            {
                "type": MSG_CHAIN_RESPONSE,
                "payload": {"chain": chain, "height": height},
            },
        )

    def _handle_chain_response(self, payload):
        """Replace the local chain if the remote chain is longer and valid."""
        try:
            remote_height = payload["height"]
            chain_data = payload["chain"]
        except (KeyError, TypeError):
            return

        try:
            blocks = [Block.from_dict(block_dict) for block_dict in chain_data]
        except (TypeError, ValueError):
            return

        if len(blocks) != remote_height:
            return

        # Compare height and replace atomically to avoid TOCTOU races.
        with self._blockchain_lock:
            local_height = self.blockchain.get_chain_height()
            if remote_height <= local_height:
                return
            self.blockchain.replace_chain(blocks)

    def _handle_peer_discovery(self, payload):
        """Register a discovered peer and respond with our peer list."""
        try:
            host = payload["host"]
            port = int(payload["port"])
        except (KeyError, TypeError, ValueError):
            return []

        should_connect = False
        with self._peers_lock:
            if (host, port) != (self.host, self.port):
                self.peers.add((host, port))
                should_connect = (host, port) not in self.bootstrap_peers
            peer_list = [
                {"host": peer_host, "port": peer_port}
                for peer_host, peer_port in self.peers
                if (peer_host, peer_port) != (self.host, self.port)
            ]

        if should_connect:
            self._connect_to_peer(host, port)

        return peer_list

    def _handle_peer_list(self, payload):
        """Merge peers from a PEER_LIST message into the local peer set."""
        peers_to_add = []
        for peer_info in payload.get("peers", []):
            try:
                host = peer_info["host"]
                port = int(peer_info["port"])
            except (KeyError, TypeError, ValueError):
                continue

            if (host, port) == (self.host, self.port):
                continue

            peers_to_add.append((host, port))

        with self._peers_lock:
            self.peers.update(peers_to_add)

    def _send_peer_discovery(self, conn):
        """Announce this node and exchange peer lists."""
        self._send_message(
            conn,
            {
                "type": MSG_PEER_DISCOVERY,
                "payload": {"host": self.host, "port": self.port},
            },
        )

    def _request_chain_sync(self, peer):
        """Open a short-lived connection to request chain sync from a peer."""
        try:
            response = self._send_to_peer(
                peer, {"type": MSG_CHAIN_REQUEST, "payload": {}}
            )
        except (OSError, json.JSONDecodeError, ValueError):
            self._remove_peer(peer)
            return

        if response and response.get("type") == MSG_CHAIN_RESPONSE:
            self._handle_chain_response(response.get("payload", {}))

    def _request_chain_sync_on_socket(self, conn):
        """Request chain sync on an existing connection."""
        self._send_message(conn, {"type": MSG_CHAIN_REQUEST, "payload": {}})

    def _send_to_peer(self, peer, message):
        """Connect to a peer, send one message, and read the response."""
        host, port = peer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        try:
            sock.connect((host, port))
            self._send_message(sock, message)
            return self._recv_message(sock)
        finally:
            sock.close()

    def _send_to_peer_one_way(self, peer, message):
        """Connect to a peer, send one message, and close without waiting."""
        host, port = peer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        try:
            sock.connect((host, port))
            self._send_message(sock, message)
        finally:
            sock.close()

    def _add_peer(self, host, port):
        """Add a peer to the in-memory peer list under _peers_lock."""
        peer = (host, port)
        if peer == (self.host, self.port):
            return
        with self._peers_lock:
            self.peers.add(peer)

    def _remove_peer(self, peer):
        """Remove a peer from the in-memory peer list under _peers_lock."""
        with self._peers_lock:
            self.peers.discard(peer)

    @staticmethod
    def _send_message(sock, message):
        """Send a JSON message over length-prefixed TCP."""
        data = json.dumps(message).encode("utf-8")
        sock.sendall(struct.pack(">I", len(data)) + data)

    @staticmethod
    def _recv_message(sock):
        """Receive a length-prefixed JSON message from TCP."""
        header = P2PNode._recv_exact(sock, 4)
        if not header:
            return None
        length = struct.unpack(">I", header)[0]
        if length == 0:
            return None
        payload = P2PNode._recv_exact(sock, length)
        if not payload:
            return None
        return json.loads(payload.decode("utf-8"))

    @staticmethod
    def _recv_exact(sock, num_bytes):
        """Read exactly num_bytes from a socket."""
        chunks = []
        remaining = num_bytes
        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)