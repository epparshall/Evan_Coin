import time
import json
import hashlib

from Evan_Coin.transaction import Transaction

class Block:
    def __init__(
        self,
        index,
        previous_hash,
        transactions,
        signatures,
        nonce=0,
        difficulty=4,
        timestamp=None,
    ):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.transactions = transactions
        self.signatures = signatures
        self.nonce = nonce
        self.difficulty = difficulty
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        return self.calculate_hash_from_dict(self.to_dict())

    @staticmethod
    def calculate_hash_from_dict(block_dict):
        block_string = json.dumps(block_dict, sort_keys=True).encode('utf-8')
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "signatures": self.signatures,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
        }

    @staticmethod
    def from_dict(block_dict):
        required_fields = ('index', 'previous_hash', 'transactions', 'signatures')
        missing = [field for field in required_fields if field not in block_dict]
        if missing:
            raise ValueError(f"Invalid block data: missing fields {missing}")
        try:
            transactions = [
                Transaction.from_dict(tx) for tx in block_dict['transactions']
            ]
            return Block(
                block_dict['index'],
                block_dict['previous_hash'],
                transactions,
                block_dict['signatures'],
                nonce=block_dict.get('nonce', 0),
                difficulty=block_dict.get('difficulty', 4),
                timestamp=block_dict.get('timestamp'),
            )
        except (TypeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid block data: {e}") from e