import time
import json
import hashlib
import random

from Evan_Coin import Block
from Evan_Coin import Transaction
from Evan_Coin import Wallet


class Blockchain:
    def __init__(self, reward_amount=10, genesis_reward_address=None):
        self.chain = []
        self.pending_transactions = []
        self.signatures = []
        self.balances = {}
        self.genesis_reward_address = genesis_reward_address
        self.create_genesis_block()
        self.difficulty = 4
        self.reward_amount = reward_amount  # Configurable block reward

    def create_genesis_block(self):
        if self.genesis_reward_address:
            # Include coinbase reward in genesis block (as requested in #9)
            genesis_coinbase = Transaction(
                sender_public_address=None,
                receiver_public_address=self.genesis_reward_address,
                amount=self.reward_amount,
                is_coinbase=True
            )
            genesis_block = Block(0, "0", [genesis_coinbase], [None])
        else:
            genesis_block = Block(0, "0", [], [])
        self.save_to_txt(genesis_block, rwa='w')
        self.chain.append(genesis_block)
        self.balances = {}  # reset on genesis
        if self.genesis_reward_address:
            self._update_balances(genesis_block)

    def _update_balances(self, block):
        """Update running balance cache for all transactions in a block."""
        for tx in block.transactions:
            if tx.receiver:
                self.balances[tx.receiver] = self.balances.get(tx.receiver, 0) + tx.amount
            if tx.sender:
                self.balances[tx.sender] = self.balances.get(tx.sender, 0) - tx.amount

    def add_transaction(self, transaction: Transaction, sender_private_key):
        if transaction.is_coinbase:
            print("Coinbase transactions cannot be added manually")
            return

        if transaction.amount <= 0:
            print("Transaction amount must be greater than 0")
            return

        try:
            signature = Transaction.sign_transaction(transaction, sender_private_key)
        except ValueError as e:
            print(f"Failed to sign transaction: {e}")
            return

        try:
            is_valid = Transaction.verify_signature(transaction, signature)
        except ValueError as e:
            print(f"Failed to verify transaction signature: {e}")
            return

        if not is_valid:
            print("Invalid transaction signature")
            return

        sender_balance = Wallet.get_balance(self, transaction.sender)
        if sender_balance < transaction.amount:
            print(f"Insufficient balance: sender has {sender_balance}, tried to send {transaction.amount}")
            return

        self.signatures.append(signature)
        self.pending_transactions.append(transaction)

    def mine_block(self, miner: Wallet):
        """Mine a new block with a coinbase reward transaction."""
        last_block = self.chain[-1]

        # Create coinbase transaction (block reward)
        coinbase_tx = Transaction(
            sender_public_address=None,
            receiver_public_address=miner.public_address,
            amount=self.reward_amount,
            is_coinbase=True
        )

        # Add coinbase as the first transaction
        all_transactions = [coinbase_tx] + self.pending_transactions
        all_signatures = [None] + self.signatures  # Coinbase has no signature

        while True:
            nonce = random.randint(0, 1000000000)
            block_data = {
                "index": len(self.chain),
                "previous_hash": last_block.hash,
                "transactions": [tx.to_dict() for tx in all_transactions],
                "signatures": all_signatures,
                "timestamp": time.time(),
                "nonce": nonce,
            }

            block_string = json.dumps(block_data, sort_keys=True).encode('utf-8')
            hash_result = hashlib.sha256(block_string).hexdigest()

            if hash_result[:self.difficulty] == '0' * self.difficulty:
                new_block = Block(len(self.chain), last_block.hash, all_transactions, all_signatures)
                self.save_to_txt(new_block)
                self.chain.append(new_block)
                self._update_balances(new_block)
                self.pending_transactions = []
                self.signatures = []
                print(f"\nMined Block {len(self.chain) - 1} with hash {hash_result}\n")
                return new_block

    def save_to_txt(self, new_block, rwa='a'):
        with open("./Blockchain.txt", rwa) as file:
            json.dump(new_block.to_dict(), file)
            file.write("\n")

    def verify_protocol(self, content):
        split_content = content.splitlines()
        for line_idx in range(len(split_content) - 1):
            line1 = split_content[line_idx]
            line2 = split_content[line_idx + 1]
            block1 = Block.from_dict(json.loads(line1))
            block2 = Block.from_dict(json.loads(line2))

            # Verify previous hash
            assert block2.previous_hash == hashlib.sha256(
                json.dumps(json.loads(line1), sort_keys=True).encode('utf-8')
            ).hexdigest(), f"Incorrect Hash at Index: {line_idx + 1}"

            signatures = block2.signatures
            transactions = block2.transactions
            assert len(signatures) == len(transactions), "Must have equal number of signatures as transactions"

            for sig_idx in range(len(signatures)):
                tx = transactions[sig_idx]
                sig = signatures[sig_idx]
                if tx.is_coinbase:
                    assert sig is None, "Coinbase transaction should not have a signature"
                else:
                    assert Transaction.verify_signature(tx, sig), "Invalid transaction signature"

        return True
