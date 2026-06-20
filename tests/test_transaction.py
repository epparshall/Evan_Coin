import pytest

from Evan_Coin.transaction import Transaction
from Evan_Coin.wallet import Wallet


@pytest.fixture
def keys():
    sender = Wallet()
    receiver = Wallet()
    return sender, receiver


class TestTransactionCreation:
    def test_regular_transaction_fields(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 5.0)

        assert tx.sender == sender.public_address
        assert tx.receiver == receiver.public_address
        assert tx.amount == 5.0
        assert tx.fee == 0
        assert tx.is_coinbase is False
        assert tx.timestamp > 0

    def test_coinbase_transaction_fields(self, keys):
        _, receiver = keys
        tx = Transaction(None, receiver.public_address, 10, is_coinbase=True)

        assert tx.sender is None
        assert tx.receiver == receiver.public_address
        assert tx.amount == 10
        assert tx.is_coinbase is True


class TestTransactionValidation:
    def test_valid_regular_transaction(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 1)
        tx.validate()

    def test_valid_coinbase_transaction(self, keys):
        _, receiver = keys
        tx = Transaction(None, receiver.public_address, 10, is_coinbase=True)
        tx.validate()

    def test_invalid_amount_zero(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 0)
        with pytest.raises(ValueError, match="amount"):
            tx.validate()

    def test_invalid_amount_negative(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, -5)
        with pytest.raises(ValueError, match="amount"):
            tx.validate()

    def test_empty_receiver(self, keys):
        sender, _ = keys
        tx = Transaction(sender.public_address, "", 1)
        with pytest.raises(ValueError, match="receiver"):
            tx.validate()

    def test_invalid_receiver_hex(self, keys):
        sender, _ = keys
        tx = Transaction(sender.public_address, "not-hex", 1)
        with pytest.raises(ValueError, match="receiver"):
            tx.validate()

    def test_empty_sender_for_regular_tx(self, keys):
        _, receiver = keys
        tx = Transaction("", receiver.public_address, 1)
        with pytest.raises(ValueError, match="sender"):
            tx.validate()

    def test_invalid_sender_hex(self, keys):
        _, receiver = keys
        tx = Transaction("badkey", receiver.public_address, 1)
        with pytest.raises(ValueError, match="sender"):
            tx.validate()

    def test_invalid_fee_negative(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 1, fee=-1)
        with pytest.raises(ValueError, match="fee"):
            tx.validate()

    def test_valid_transaction_with_fee(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 1, fee=0.5)
        tx.validate()
        assert tx.fee == 0.5


class TestTransactionSerialization:
    def test_to_dict_contains_expected_fields(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 3.5)
        data = tx.to_dict()

        assert data["sender"] == sender.public_address
        assert data["receiver"] == receiver.public_address
        assert data["amount"] == 3.5
        assert data["fee"] == 0
        assert data["timestamp"] == tx.timestamp
        assert data["is_coinbase"] is False

    def test_from_dict_roundtrip(self, keys):
        sender, receiver = keys
        original = Transaction(sender.public_address, receiver.public_address, 7)
        restored = Transaction.from_dict(original.to_dict())

        assert restored.sender == original.sender
        assert restored.receiver == original.receiver
        assert restored.amount == original.amount
        assert restored.fee == original.fee
        assert restored.timestamp == original.timestamp
        assert restored.is_coinbase == original.is_coinbase

    def test_from_dict_defaults_fee_to_zero(self, keys):
        _, receiver = keys
        data = {
            "sender": None,
            "receiver": receiver.public_address,
            "amount": 10,
            "timestamp": 12345.0,
        }
        tx = Transaction.from_dict(data)
        assert tx.fee == 0

    def test_from_dict_coinbase_defaults_is_coinbase_false(self, keys):
        _, receiver = keys
        data = {
            "sender": None,
            "receiver": receiver.public_address,
            "amount": 10,
            "timestamp": 12345.0,
        }
        tx = Transaction.from_dict(data)
        assert tx.is_coinbase is False

    def test_from_dict_missing_fields(self):
        with pytest.raises(ValueError, match="missing fields"):
            Transaction.from_dict({"sender": "abc", "amount": 1})


class TestTransactionSigning:
    def test_sign_and_verify_valid_transaction(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 2)
        signature = Transaction.sign_transaction(tx, sender.private_key)

        assert signature is not None
        assert Transaction.verify_signature(tx, signature) is True

    def test_sign_coinbase_returns_none(self, keys):
        _, receiver = keys
        tx = Transaction(None, receiver.public_address, 10, is_coinbase=True)
        assert Transaction.sign_transaction(tx, "00" * 32) is None

    def test_verify_coinbase_always_true(self, keys):
        _, receiver = keys
        tx = Transaction(None, receiver.public_address, 10, is_coinbase=True)
        assert Transaction.verify_signature(tx, None) is True
        assert Transaction.verify_signature(tx, "invalid") is True

    def test_verify_invalid_signature_returns_false(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 2)
        assert Transaction.verify_signature(tx, "dGVzdA==") is False

    def test_verify_empty_signature_returns_false(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 2)
        assert Transaction.verify_signature(tx, None) is False
        assert Transaction.verify_signature(tx, "") is False

    def test_tampered_transaction_fails_verification(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 2)
        signature = Transaction.sign_transaction(tx, sender.private_key)

        tx.amount = 100
        assert Transaction.verify_signature(tx, signature) is False

    def test_sign_with_invalid_private_key(self, keys):
        sender, receiver = keys
        tx = Transaction(sender.public_address, receiver.public_address, 2)
        with pytest.raises(ValueError, match="private key"):
            Transaction.sign_transaction(tx, "not-a-valid-key")