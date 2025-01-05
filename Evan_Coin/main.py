from Evan_Coin import Wallet
from Evan_Coin import Transaction
from Evan_Coin import Blockchain

# TO DO
    # Make a seed generator for the wallets

if __name__ == "__main__":
    # Create two wallets
    evan_wallet = Wallet()
    evan2_wallet = Wallet()

    # Create the blockchain and mine block
    blockchain = Blockchain()

    # Mine block, add transactions, and make sure it is right
    blockchain.mine_block(evan_wallet)
    evan_wallet_balance = Wallet.get_balance(blockchain, evan_wallet.public_address)

    blockchain.add_transaction(Transaction(sender_public_address=evan_wallet.public_address, receiver_public_address=evan2_wallet.public_address, amount=5), sender_private_key=evan_wallet.private_key)
    blockchain.mine_block(evan_wallet)

    blockchain.add_transaction(Transaction(sender_public_address=evan_wallet.public_address, receiver_public_address=evan2_wallet.public_address, amount=5), sender_private_key=evan_wallet.private_key)
    blockchain.add_transaction(Transaction(sender_public_address=evan_wallet.public_address, receiver_public_address=evan2_wallet.public_address, amount=5), sender_private_key=evan_wallet.private_key)
    blockchain.mine_block(evan2_wallet)

    with open("./Blockchain.txt", 'r') as file:
        content = file.read()

    print("Is protocol followed: " + str(blockchain.verify_protocol(content)))
    print("Evan Wallet Balance: " + str(Wallet.get_balance(blockchain, evan_wallet.public_address)))
    print("Evan2 Wallet Balance: " + str(Wallet.get_balance(blockchain, evan2_wallet.public_address)))
