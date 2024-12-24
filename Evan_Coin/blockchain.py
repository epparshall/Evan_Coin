import time
import json
import hashlib
import random

from Evan_Coin import Block
from Evan_Coin import Transaction
from Evan_Coin import Wallet

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = [None]
        self.signatures = [None]
        self.create_genesis_block()
        self.difficulty = 4  # Difficulty of the PoW (target hash prefix length)
        self.mine_reward_wallet = Wallet()

    def create_genesis_block(self):
        genesis_block = Block(0, "0", [], [])
        self.save_to_txt(genesis_block, rwa='w')
        self.chain.append(genesis_block)

    def add_transaction(self, transaction: Transaction, sender_private_key):
        signature = Transaction.sign_transaction(transaction, sender_private_key)
        self.signatures.append(signature)
        is_valid = Transaction.verify_signature(transaction, signature)
        sender_balance = Wallet.get_balance(self, transaction.sender)

        if (is_valid and (sender_balance >= transaction.amount)):
            self.pending_transactions.append(transaction)
        else:
            print("Failed to add Transaction")

    def mine_block(self, miner: Wallet):
        # Proof of Work: Find a hash that starts with 'difficulty' number of zeros
        last_block = self.chain[-1]
        self.pending_transactions[0] = Transaction(sender_public_address=self.mine_reward_wallet.public_address, receiver_public_address=miner.public_address, amount=10)
        self.signatures[0] = Transaction.sign_transaction(self.pending_transactions[0], self.mine_reward_wallet.private_key)

        while True:
            nonce = random.randint(0, 1000000000)  # Random nonce to alter block's hash
            block_data = {
                "index": len(self.chain),
                "previous_hash": last_block.hash,
                "transactions": [tx.to_dict() for tx in self.pending_transactions],
                "signatures": self.signatures,
                "timestamp": time.time(),
                "nonce": nonce,
            }

            block_string = json.dumps(block_data, sort_keys=True).encode('utf-8')
            hash_result = hashlib.sha256(block_string).hexdigest()

            if hash_result[:self.difficulty] == '0' * self.difficulty:
                new_block = Block(len(self.chain), last_block.hash, self.pending_transactions, self.signatures)
                self.save_to_txt(new_block)
                self.chain.append(new_block)
                self.pending_transactions = [None]  # Clear pending transactions after mining
                self.signatures = [None]
                print(f"\nMined Block {len(self.chain) - 1} with hash {hash_result}\n")
                return new_block

    def save_to_txt(self, new_block, rwa='a'):
        with open("./Blockchain.txt", rwa) as file:
            json.dump(new_block.to_dict(), file)
            file.write("\n")

    def verify_protocol(self):
        with open("./Blockchain.txt", 'r') as file:
            content = file.read()

        split_content = content.splitlines()
        for line_idx in range(len(split_content) - 1):
            # Verify that previous block hashes are correct
            line1 = split_content[line_idx]
            line2 = split_content[line_idx + 1]
            block1 = Block.from_dict(json.loads(line1))
            block2 = Block.from_dict(json.loads(line2))
            assert block2.previous_hash == hashlib.sha256(json.dumps(json.loads(line1), sort_keys=True).encode('utf-8')).hexdigest(), "Incorrect Hash at Index: " + str(line_idx+1)

            # Verify that all signatures are legitimate
            signatures = block2.signatures
            transactions = block2.transactions
            assert len(signatures) == len(transactions), "Must have equal number of signatures as transactions"
            for sig_idx in range(len(signatures)):
                assert Transaction.verify_signature(transactions[sig_idx], signatures[sig_idx]), "Transaction has incorrect digital signature not authenticated"

        # If all is good and no errors
        return True
