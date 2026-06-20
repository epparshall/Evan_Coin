import ecdsa

class Wallet:
    def __init__(self):
        self.private_key, self.public_address = self.generate_keys()

    def get_address(self):
        return self.public_address

    def generate_keys(self):
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        private_key = sk.to_string().hex()
        public_address = vk.to_string().hex()
        return private_key, public_address

    @staticmethod
    def get_balance(blockchain, public_address):
        if not public_address:
            raise ValueError("Invalid address: cannot be empty")
        if not isinstance(public_address, str):
            raise ValueError("Invalid address: must be a string")
        if not hasattr(blockchain, 'chain'):
            raise ValueError("Invalid blockchain: missing chain data")

        if hasattr(blockchain, 'balances') and public_address in blockchain.balances:
            return blockchain.balances[public_address]

        balance = 0
        for block in blockchain.chain:
            for tx in block.transactions:
                if tx.receiver == public_address:
                    balance += tx.amount
                if tx.sender == public_address:
                    balance -= tx.amount + getattr(tx, 'fee', 0)
        return balance