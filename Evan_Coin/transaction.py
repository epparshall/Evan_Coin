import time
import json
import base64
import ecdsa
import binascii

SECP256K1_PRIVATE_KEY_BYTES = 32
SECP256K1_PUBLIC_KEY_BYTES = 64


def _validate_hex_key(key, name, expected_bytes=None):
    if not key:
        raise ValueError(f"Invalid {name}: cannot be empty")
    if not isinstance(key, str):
        raise ValueError(f"Invalid {name}: must be a string")
    try:
        decoded = binascii.unhexlify(key)
    except binascii.Error as e:
        raise ValueError(f"Invalid {name}: must be valid hex-encoded") from e
    if expected_bytes is not None and len(decoded) != expected_bytes:
        raise ValueError(
            f"Invalid {name}: expected {expected_bytes * 2} hex characters, "
            f"got {len(key)}"
        )
    return decoded


def _validate_amount(amount):
    if not isinstance(amount, (int, float)):
        raise ValueError("Invalid amount: must be a number")
    if amount <= 0:
        raise ValueError("Invalid amount: must be greater than 0")


class Transaction:
    def __init__(self, sender_public_address, receiver_public_address, amount, is_coinbase=False):
        self.sender = sender_public_address
        self.receiver = receiver_public_address
        self.amount = amount
        self.timestamp = time.time()
        self.is_coinbase = is_coinbase

    def validate(self):
        """Validate transaction fields. Raises ValueError on invalid input."""
        _validate_amount(self.amount)
        if not self.receiver:
            raise ValueError("Invalid receiver address: cannot be empty")
        _validate_hex_key(
            self.receiver,
            "receiver public key",
            SECP256K1_PUBLIC_KEY_BYTES,
        )
        if not self.is_coinbase:
            if not self.sender:
                raise ValueError("Invalid sender address: cannot be empty")
            _validate_hex_key(
                self.sender,
                "sender public key",
                SECP256K1_PUBLIC_KEY_BYTES,
            )

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
        required_fields = ('sender', 'receiver', 'amount', 'timestamp')
        missing = [field for field in required_fields if field not in transaction_dict]
        if missing:
            raise ValueError(f"Invalid transaction data: missing fields {missing}")
        try:
            tx = Transaction(
                sender_public_address=transaction_dict['sender'],
                receiver_public_address=transaction_dict['receiver'],
                amount=transaction_dict['amount'],
                is_coinbase=transaction_dict.get('is_coinbase', False)
            )
            tx.timestamp = transaction_dict['timestamp']
            return tx
        except (TypeError, KeyError) as e:
            raise ValueError(f"Invalid transaction data: {e}") from e

    @staticmethod
    def sign_transaction(transaction, sender_private_key):
        if transaction.is_coinbase:
            return None
        try:
            transaction.validate()
            transaction_str = json.dumps(transaction.to_dict(), sort_keys=True)
            signing_key = ecdsa.SigningKey.from_string(
                _validate_hex_key(
                    sender_private_key,
                    "private key",
                    SECP256K1_PRIVATE_KEY_BYTES,
                ),
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
            return True
        if not signature:
            return False
        try:
            transaction.validate()
            transaction_str = json.dumps(transaction.to_dict(), sort_keys=True)
            verifying_key = ecdsa.VerifyingKey.from_string(
                _validate_hex_key(
                    transaction.sender,
                    "sender public key",
                    SECP256K1_PUBLIC_KEY_BYTES,
                ),
                curve=ecdsa.SECP256k1
            )
            verifying_key.verify(
                base64.b64decode(signature),
                transaction_str.encode()
            )
            return True
        except ecdsa.BadSignatureError:
            return False
        except (binascii.Error, ValueError) as e:
            raise ValueError(f"Signature verification failed: {e}") from e