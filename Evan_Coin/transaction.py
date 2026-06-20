import time
import json
import base64
import ecdsa
import binascii


class Transaction:
    def __init__(self, sender_public_address, receiver_public_address, amount, is_coinbase=False):
        self.sender = sender_public_address
        self.receiver = receiver_public_address
        self.amount = amount
        self.timestamp = time.time()
        self.is_coinbase = is_coinbase

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "is_coinbase": self.is_coinbase
        }

    @staticmethod
    def from_dict(transaction_dict):
        tx = Transaction(
            sender_public_address=transaction_dict['sender'],
            receiver_public_address=transaction_dict['receiver'],
            amount=transaction_dict['amount'],
            is_coinbase=transaction_dict.get('is_coinbase', False)
        )
        tx.timestamp = transaction_dict['timestamp']
        return tx

    @staticmethod
    def sign_transaction(transaction, sender_private_key):
        if transaction.is_coinbase:
            return None  # Coinbase transactions don't need signatures
        try:
            transaction_str = json.dumps(transaction.to_dict(), sort_keys=True)
            signing_key = ecdsa.SigningKey.from_string(
                binascii.unhexlify(sender_private_key),
                curve=ecdsa.SECP256k1
            )
            signature = base64.b64encode(
                signing_key.sign(transaction_str.encode())
            ).decode()
            return signature
        except binascii.Error as e:
            raise ValueError("Invalid private key: must be a valid hex-encoded key") from e

    @staticmethod
    def verify_signature(transaction, signature):
        if transaction.is_coinbase:
            return True  # Coinbase transactions are always valid
        if not signature:
            return False
        try:
            transaction_str = json.dumps(transaction.to_dict(), sort_keys=True)
            verifying_key = ecdsa.VerifyingKey.from_string(
                binascii.unhexlify(transaction.sender),
                curve=ecdsa.SECP256k1
            )
            verifying_key.verify(
                base64.b64decode(signature),
                transaction_str.encode()
            )
            return True
        except ecdsa.BadSignatureError:
            return False
        except binascii.Error as e:
            raise ValueError("Invalid sender public key or signature format") from e
