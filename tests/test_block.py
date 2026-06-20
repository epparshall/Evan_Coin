import pytest

from Evan_Coin.block import Block
from Evan_Coin.transaction import Transaction
from Evan_Coin.wallet import Wallet


@pytest.fixture
def sample_block():
    receiver = Wallet()
    tx = Transaction(None, receiver.public_address, 10, is_coinbase=True)
    return Block(0, "0", [tx], [None])


class TestBlockHashing:
    def test_calculate_hash_returns_sha256_hex(self, sample_block):
        block_hash = sample_block.calculate_hash()
        assert len(block_hash) == 64
        assert all(c in "0123456789abcdef" for c in block_hash)

    def test_hash_set_on_init(self, sample_block):
        assert sample_block.hash == sample_block.calculate_hash()

    def test_hash_is_deterministic(self, sample_block):
        assert sample_block.calculate_hash() == sample_block.calculate_hash()

    def test_hash_changes_when_index_changes(self, sample_block):
        original_hash = sample_block.hash
        sample_block.index = 1
        assert sample_block.calculate_hash() != original_hash

    def test_hash_changes_when_previous_hash_changes(self, sample_block):
        original_hash = sample_block.hash
        sample_block.previous_hash = "deadbeef"
        assert sample_block.calculate_hash() != original_hash

    def test_hash_changes_when_transactions_change(self, sample_block):
        original_hash = sample_block.hash
        sender, receiver = Wallet(), Wallet()
        sample_block.transactions.append(
            Transaction(sender.public_address, receiver.public_address, 1)
        )
        assert sample_block.calculate_hash() != original_hash


class TestBlockSerialization:
    def test_to_dict_structure(self, sample_block):
        data = sample_block.to_dict()

        assert data["index"] == 0
        assert data["previous_hash"] == "0"
        assert data["timestamp"] == sample_block.timestamp
        assert len(data["transactions"]) == 1
        assert data["signatures"] == [None]

    def test_from_dict_roundtrip(self, sample_block):
        restored = Block.from_dict(sample_block.to_dict())

        assert restored.index == sample_block.index
        assert restored.previous_hash == sample_block.previous_hash
        assert len(restored.transactions) == len(sample_block.transactions)
        assert restored.transactions[0].amount == sample_block.transactions[0].amount
        assert restored.transactions[0].is_coinbase == sample_block.transactions[0].is_coinbase
        assert restored.signatures == sample_block.signatures

    def test_from_dict_missing_fields(self):
        with pytest.raises(ValueError, match="missing fields"):
            Block.from_dict({"index": 0, "previous_hash": "0"})

    def test_from_dict_invalid_transaction_data(self):
        with pytest.raises(ValueError, match="Invalid block data"):
            Block.from_dict({
                "index": 1,
                "previous_hash": "abc",
                "transactions": [{"sender": "x"}],
                "signatures": [],
            })


class TestBlockValidation:
    def test_block_links_to_previous_hash(self):
        receiver = Wallet()
        genesis = Block(0, "0", [], [])
        coinbase = Transaction(None, receiver.public_address, 10, is_coinbase=True)
        block1 = Block(1, genesis.hash, [coinbase], [None])

        assert block1.previous_hash == genesis.hash
        assert block1.index == 1

    def test_signatures_match_transaction_count(self):
        sender, receiver = Wallet(), Wallet()
        tx = Transaction(sender.public_address, receiver.public_address, 5)
        signature = Transaction.sign_transaction(tx, sender.private_key)
        block = Block(1, "prev", [tx], [signature])

        assert len(block.signatures) == len(block.transactions)