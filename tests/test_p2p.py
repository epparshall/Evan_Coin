import socket
import threading
import time

import pytest

from Evan_Coin.block import Block
from Evan_Coin.blockchain import Blockchain
from Evan_Coin.p2p import (
    MSG_CHAIN_REQUEST,
    MSG_CHAIN_RESPONSE,
    MSG_NEW_BLOCK,
    MSG_PING,
    MSG_PONG,
    P2PNode,
)
from Evan_Coin.transaction import Transaction
from Evan_Coin.wallet import Wallet


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def low_difficulty_blockchain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bc = Blockchain(reward_amount=10)
    bc.difficulty = 1
    return bc


@pytest.fixture
def p2p_node_factory(low_difficulty_blockchain):
    nodes = []

    def _create_node(port=None, bootstrap_peers=None, blockchain=None):
        port = port or _free_port()
        node = P2PNode(
            blockchain=blockchain or low_difficulty_blockchain,
            host="127.0.0.1",
            port=port,
            bootstrap_peers=bootstrap_peers or [],
        )
        node.start()
        nodes.append(node)
        time.sleep(0.15)
        return node

    yield _create_node

    for node in nodes:
        node.stop()


class TestBlockchainP2PMethods:
    def test_add_block_extends_chain(self, low_difficulty_blockchain, wallet):
        blockchain = low_difficulty_blockchain
        mined = blockchain.mine_block(wallet)
        assert blockchain.add_block(mined) is False

        blockchain2 = Blockchain(reward_amount=10)
        blockchain2.difficulty = 1
        next_block = blockchain.mine_block(wallet)
        assert blockchain2.add_block(next_block) is False

        assert blockchain.add_block(next_block) is True
        assert blockchain.get_chain_height() == 3

    def test_replace_chain_adopts_longer_valid_chain(self, tmp_path, monkeypatch, wallet):
        monkeypatch.chdir(tmp_path)
        local = Blockchain(reward_amount=10)
        local.difficulty = 1
        remote = Blockchain(reward_amount=10)
        remote.difficulty = 1

        remote.mine_block(wallet)
        remote.mine_block(wallet)

        assert local.get_chain_height() == 1
        assert remote.replace_chain(local.chain) is False
        assert local.replace_chain(remote.chain) is True
        assert local.get_chain_height() == 3


class TestP2PNetworking:
    def test_length_prefixed_message_roundtrip(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        port = server_sock.getsockname()[1]
        server_sock.listen(1)
        received = {}

        def server():
            conn, _ = server_sock.accept()
            received["message"] = P2PNode._recv_message(conn)
            conn.close()
            server_sock.close()

        threading.Thread(target=server, daemon=True).start()
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", port))
        payload = {"type": MSG_PING, "payload": {"nonce": 1}}
        P2PNode._send_message(client, payload)
        client.close()
        time.sleep(0.1)
        assert received["message"] == payload

    def test_ping_pong_over_tcp(self, p2p_node_factory):
        node = p2p_node_factory()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((node.host, node.port))
        P2PNode._send_message(sock, {"type": MSG_PING, "payload": {}})
        response = P2PNode._recv_message(sock)
        sock.close()
        assert response["type"] == MSG_PONG

    def test_chain_sync_on_startup(self, tmp_path, monkeypatch, wallet, p2p_node_factory):
        monkeypatch.chdir(tmp_path)
        leader_bc = Blockchain(reward_amount=10)
        leader_bc.difficulty = 1
        leader_port = _free_port()
        leader = p2p_node_factory(port=leader_port, blockchain=leader_bc)
        leader_bc.mine_block(wallet)
        leader_bc.mine_block(wallet)

        follower_bc = Blockchain(reward_amount=10)
        follower_bc.difficulty = 1
        follower = p2p_node_factory(
            bootstrap_peers=[("127.0.0.1", leader_port)],
            blockchain=follower_bc,
        )
        follower.sync_with_peers()
        time.sleep(0.3)

        assert follower.get_chain_height() == leader.get_chain_height() == 3

    def test_block_gossip_propagation(self, tmp_path, monkeypatch, wallet, p2p_node_factory):
        monkeypatch.chdir(tmp_path)
        node_a_bc = Blockchain(reward_amount=10)
        node_a_bc.difficulty = 1
        port_a = _free_port()
        node_a = p2p_node_factory(port=port_a, blockchain=node_a_bc)

        node_b_bc = Blockchain(reward_amount=10)
        node_b_bc.difficulty = 1
        node_b = p2p_node_factory(
            bootstrap_peers=[("127.0.0.1", port_a)],
            blockchain=node_b_bc,
        )
        time.sleep(0.2)

        new_block = node_a_bc.mine_block(wallet)
        node_a.broadcast_new_block(new_block)
        time.sleep(0.5)

        assert node_b.get_chain_height() == 2

    def test_peer_discovery_via_bootstrap(self, p2p_node_factory):
        port_a = _free_port()
        node_a = p2p_node_factory(port=port_a)
        port_b = _free_port()
        node_b = p2p_node_factory(
            port=port_b,
            bootstrap_peers=[("127.0.0.1", port_a)],
        )
        time.sleep(0.3)

        with node_a._peers_lock:
            assert ("127.0.0.1", port_b) in node_a.peers
        with node_b._peers_lock:
            assert ("127.0.0.1", port_a) in node_b.peers

    def test_chain_request_response(self, tmp_path, monkeypatch, wallet, p2p_node_factory):
        monkeypatch.chdir(tmp_path)
        bc = Blockchain(reward_amount=10)
        bc.difficulty = 1
        node = p2p_node_factory(blockchain=bc)
        bc.mine_block(wallet)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((node.host, node.port))
        P2PNode._send_message(sock, {"type": MSG_CHAIN_REQUEST, "payload": {}})
        response = P2PNode._recv_message(sock)
        sock.close()

        assert response["type"] == MSG_CHAIN_RESPONSE
        assert response["payload"]["height"] == 2


class TestP2PThreadSafety:
    def test_concurrent_block_additions_are_safe(self, low_difficulty_blockchain, wallet):
        blockchain = low_difficulty_blockchain
        blockchain.mine_block(wallet)
        successes = []
        lock = threading.Lock()

        def try_add_block(block):
            result = blockchain.add_block(block)
            with lock:
                successes.append(result)

        block_one = blockchain.mine_block(wallet)
        blockchain.mine_block(wallet)
        block_three = blockchain.mine_block(wallet)

        threads = [
            threading.Thread(target=try_add_block, args=(block_one,)),
            threading.Thread(target=try_add_block, args=(block_three,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()

        assert sum(successes) == 1
        assert blockchain.get_chain_height() == 3

    def test_concurrent_p2p_block_handling_without_deadlock(
        self, tmp_path, monkeypatch, wallet, p2p_node_factory
    ):
        monkeypatch.chdir(tmp_path)
        bc = Blockchain(reward_amount=10)
        bc.difficulty = 1
        node = p2p_node_factory(blockchain=bc)
        bc.mine_block(wallet)

        errors = []
        done = threading.Event()

        def spam_blocks():
            try:
                for _ in range(8):
                    block = bc.mine_block(wallet)
                    message = {
                        "type": MSG_NEW_BLOCK,
                        "payload": {"block": block.to_dict()},
                    }
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5.0)
                    sock.connect((node.host, node.port))
                    P2PNode._send_message(sock, message)
                    sock.close()
                    time.sleep(0.02)
            except OSError as exc:
                errors.append(exc)
            finally:
                done.set()

        def spam_sync():
            try:
                for _ in range(8):
                    node.sync_with_peers()
                    with node._blockchain_lock:
                        _ = node.blockchain.get_chain_height()
                    with node._peers_lock:
                        _ = set(node.peers)
                    time.sleep(0.02)
            except OSError as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=spam_blocks),
            threading.Thread(target=spam_sync),
            threading.Thread(target=spam_sync),
        ]
        for thread in threads:
            thread.start()

        deadline = time.time() + 10
        while time.time() < deadline and any(thread.is_alive() for thread in threads):
            time.sleep(0.1)

        for thread in threads:
            thread.join(timeout=1)
            assert not thread.is_alive(), "P2P operations deadlocked"

        assert not errors
        assert node.get_chain_height() >= 2

    def test_concurrent_height_reads_under_lock(self, p2p_node_factory):
        node = p2p_node_factory()
        heights = []
        barrier = threading.Barrier(6)

        def read_height():
            barrier.wait(timeout=5)
            for _ in range(20):
                heights.append(node.get_chain_height())
                time.sleep(0.001)

        threads = [threading.Thread(target=read_height) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            assert not thread.is_alive()

        assert heights
        assert all(height == 1 for height in heights)