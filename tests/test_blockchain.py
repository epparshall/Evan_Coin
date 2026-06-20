import pytest

from Evan_Coin.block import Block
from Evan_Coin.blockchain import Blockchain
from Evan_Coin.transaction import Transaction
from Evan_Coin.wallet import Wallet


class TestGenesisBlock:
    def test_genesis_block_created_on_init(self, blockchain):
        assert len(blockchain.chain) == 1
        assert blockchain.chain[0].index == 0
        assert blockchain.chain[0].previous_hash == "0"

    def test_genesis_block_has_no_transactions_by_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        bc = Blockchain()
        assert bc.chain[0].transactions == []

    def test_genesis_coinbase_transaction_structure(self):
        miner = Wallet()
        coinbase = Transaction(
            sender_public_address=None,
            receiver_public_address=miner.public_address,
            amount=10,
            is_coinbase=True,
        )
        coinbase.validate()
        assert Transaction.sign_transaction(coinbase, miner.private_key) is None
        assert Transaction.verify_signature(coinbase, None) is True

    def test_genesis_coinbase_updates_balances(self, blockchain, wallet):
        coinbase = Transaction(
            sender_public_address=None,
            receiver_public_address=wallet.public_address,
            amount=blockchain.reward_amount,
            is_coinbase=True,
        )
        block = Block(0, "0", [coinbase], [None])
        blockchain.balances = {}
        blockchain._update_balances(block)

        assert blockchain.balances[wallet.public_address] == 10
        assert Wallet.get_balance(blockchain, wallet.public_address) == 10


class TestAddTransaction:
    def test_add_valid_transaction(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair
        # Fund sender from miner's block reward
        tx_fund = Transaction(miner.public_address, sender.public_address, 5)
        blockchain.add_transaction(tx_fund, miner.private_key)
        blockchain.mine_block(miner)

        tx = Transaction(sender.public_address, receiver.public_address, 3)
        result = blockchain.add_transaction(tx, sender.private_key)

        assert result is True
        assert len(blockchain.pending_transactions) == 1
        assert len(blockchain.signatures) == 1

    def test_reject_insufficient_balance(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair
        tx = Transaction(sender.public_address, receiver.public_address, 100)
        result = blockchain.add_transaction(tx, sender.private_key)

        assert result is False
        assert len(blockchain.pending_transactions) == 0

    def test_reject_invalid_signature_key(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair
        tx = Transaction(sender.public_address, receiver.public_address, 1)
        result = blockchain.add_transaction(tx, receiver.private_key)

        assert result is False

    def test_reject_coinbase_transaction(self, funded_blockchain, wallet_pair):
        blockchain, _ = funded_blockchain
        _, receiver = wallet_pair
        coinbase = Transaction(None, receiver.public_address, 10, is_coinbase=True)
        result = blockchain.add_transaction(coinbase, receiver.private_key)

        assert result is False

    def test_reject_invalid_amount(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair
        tx = Transaction(sender.public_address, receiver.public_address, -1)
        result = blockchain.add_transaction(tx, sender.private_key)

        assert result is False


class TestMining:
    def test_mine_block_appends_to_chain(self, blockchain, wallet):
        assert len(blockchain.chain) == 1
        new_block = blockchain.mine_block(wallet)

        assert new_block is not None
        assert len(blockchain.chain) == 2
        assert new_block.index == 1

    def test_mined_block_includes_coinbase_reward(self, blockchain, wallet):
        new_block = blockchain.mine_block(wallet)

        assert len(new_block.transactions) >= 1
        coinbase = new_block.transactions[0]
        assert coinbase.is_coinbase is True
        assert coinbase.receiver == wallet.public_address
        assert coinbase.amount == blockchain.reward_amount
        assert new_block.signatures[0] is None

    def test_mine_block_links_to_previous(self, blockchain, wallet):
        genesis_hash = blockchain.chain[0].hash
        new_block = blockchain.mine_block(wallet)

        assert new_block.previous_hash == genesis_hash

    def test_mine_clears_pending_transactions(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair

        tx_fund = Transaction(miner.public_address, sender.public_address, 5)
        blockchain.add_transaction(tx_fund, miner.private_key)
        blockchain.mine_block(miner)

        tx = Transaction(sender.public_address, receiver.public_address, 2)
        blockchain.add_transaction(tx, sender.private_key)
        assert len(blockchain.pending_transactions) == 1

        blockchain.mine_block(miner)
        assert blockchain.pending_transactions == []
        assert blockchain.signatures == []

    def test_mine_invalid_miner_returns_none(self, blockchain):
        assert blockchain.mine_block(None) is None

    def test_mine_includes_pending_transactions(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair

        tx_fund = Transaction(miner.public_address, sender.public_address, 5)
        blockchain.add_transaction(tx_fund, miner.private_key)
        blockchain.mine_block(miner)

        tx = Transaction(sender.public_address, receiver.public_address, 2)
        blockchain.add_transaction(tx, sender.private_key)
        new_block = blockchain.mine_block(miner)

        pending_in_block = [
            t for t in new_block.transactions if not t.is_coinbase
        ]
        assert len(pending_in_block) == 1
        assert pending_in_block[0].amount == 2


class TestBalanceCalculations:
    def test_balance_after_single_mine(self, blockchain, wallet):
        blockchain.mine_block(wallet)

        assert Wallet.get_balance(blockchain, wallet.public_address) == 10
        assert blockchain.balances[wallet.public_address] == 10

    def test_balance_after_transfer(self, funded_blockchain, wallet_pair):
        blockchain, miner = funded_blockchain
        sender, receiver = wallet_pair

        tx_fund = Transaction(miner.public_address, sender.public_address, 7)
        blockchain.add_transaction(tx_fund, miner.private_key)
        blockchain.mine_block(miner)

        tx = Transaction(sender.public_address, receiver.public_address, 4)
        blockchain.add_transaction(tx, sender.private_key)
        blockchain.mine_block(miner)

        assert Wallet.get_balance(blockchain, sender.public_address) == 3
        assert Wallet.get_balance(blockchain, receiver.public_address) == 4
        # miner: 10 (block 1) + 10 - 7 (block 2) + 10 (block 3) = 23
        assert Wallet.get_balance(blockchain, miner.public_address) == 23

    def test_balance_uses_cached_balances_when_available(self, funded_blockchain, wallet):
        blockchain, miner = funded_blockchain
        cached = blockchain.balances[miner.public_address]

        assert Wallet.get_balance(blockchain, miner.public_address) == cached

    def test_balance_rejects_empty_address(self, blockchain):
        with pytest.raises(ValueError, match="address"):
            Wallet.get_balance(blockchain, "")

    def test_balance_rejects_invalid_blockchain(self):
        with pytest.raises(ValueError, match="blockchain"):
            Wallet.get_balance(object(), "abc")


class TestCoinbaseHandling:
    def test_coinbase_has_no_sender(self, blockchain, wallet):
        new_block = blockchain.mine_block(wallet)
        coinbase = new_block.transactions[0]

        assert coinbase.sender is None
        assert coinbase.is_coinbase is True

    def test_coinbase_not_counted_as_sender_debit(self, blockchain, wallet):
        blockchain.mine_block(wallet)
        # Miner should receive full reward, not lose amount due to None sender
        assert Wallet.get_balance(blockchain, wallet.public_address) == 10

    def test_multiple_blocks_accumulate_rewards(self, blockchain, wallet):
        blockchain.mine_block(wallet)
        blockchain.mine_block(wallet)

        assert Wallet.get_balance(blockchain, wallet.public_address) == 20