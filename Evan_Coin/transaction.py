import time
import json
import base64
import ecdsa
import binascii

class Transaction:
    def __init__(self, sender_public_address, receiver_public_address, amount):
        self.sender = sender_public_address
        self.receiver = receiver_public_address
        self.amount = amount
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(transaction_dict):
        transaction = Transaction(
            sender_public_address=transaction_dict['sender'],
            receiver_public_address=transaction_dict['receiver'],
            amount=transaction_dict['amount']
        )
        transaction.timestamp = transaction_dict['timestamp']
        return transaction

    @staticmethod
    def sign_transaction(transaction, sender_private_key):
        transaction_str = json.dumps(transaction.to_dict(), sort_keys=True)
        signature = base64.b64encode(ecdsa.SigningKey.from_string(binascii.unhexlify(sender_private_key), curve=ecdsa.SECP256k1).sign(transaction_str.encode())).decode()
        return signature

    @staticmethod
    def verify_signature(transaction, sender_public_address, signature):
        transaction_str = json.dumps(transaction.to_dict(), sort_keys=True)
        try:
            ecdsa.VerifyingKey.from_string(binascii.unhexlify(sender_public_address), curve=ecdsa.SECP256k1).verify(base64.b64decode(signature), transaction_str.encode())
            return True
        except ecdsa.BadSignatureError:
            return False
