import time
import json
import hashlib

from Evan_Coin.transaction import Transaction

class Block:
    def __init__(self, index, previous_hash, transactions):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = time.time()
        self.transactions = transactions
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps(self.to_dict(), sort_keys=True).encode('utf-8')
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
        }

    @staticmethod
    def from_dict(block_dict):
        transactions = [Transaction.from_dict(tx) for tx in block_dict['transactions']]
        block = Block(block_dict['index'], block_dict['previous_hash'], transactions)
        return block
