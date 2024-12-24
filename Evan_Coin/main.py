from Evan_Coin import Wallet
from Evan_Coin import Transaction
from Evan_Coin import Blockchain

if __name__ == "__main__":
    evan_wallet = Wallet()
    print(evan_wallet.private_key)
    blockchain = Blockchain()

    blockchain.mine_block(evan_wallet)
    blockchain.verify_protocol()

    evan_wallet_balance = Wallet.get_balance(blockchain, evan_wallet.public_address)
    print(evan_wallet_balance)

    evan2_wallet = Wallet()

    blockchain.add_transaction(Transaction(sender_public_address=evan_wallet.public_address, receiver_public_address=evan2_wallet.public_address, amount=5), sender_public_address=evan_wallet.public_address, sender_private_key=evan_wallet.private_key)

    blockchain.mine_block(evan_wallet)

    print(Wallet.get_balance(blockchain, evan_wallet.public_address))
    print(Wallet.get_balance(blockchain, evan2_wallet.public_address))
