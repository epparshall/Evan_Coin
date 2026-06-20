import sys
from unittest.mock import MagicMock

# Evan_Coin.__init__ imports server, which binds a socket at import time.
sys.modules.setdefault("Evan_Coin.server", MagicMock())

import pytest

from Evan_Coin.blockchain import Blockchain
from Evan_Coin.wallet import Wallet


@pytest.fixture
def wallet():
    return Wallet()


@pytest.fixture
def wallet_pair():
    return Wallet(), Wallet()


@pytest.fixture
def blockchain(tmp_path, monkeypatch):
    """Blockchain with file I/O redirected to a temp directory."""
    monkeypatch.chdir(tmp_path)
    bc = Blockchain(reward_amount=10)
    bc.difficulty = 1
    return bc


@pytest.fixture
def funded_blockchain(blockchain, wallet):
    """Blockchain with one mined block granting the wallet its coinbase reward."""
    blockchain.mine_block(wallet)
    return blockchain, wallet