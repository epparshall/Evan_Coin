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
                self.balances[tx.sender] = self.balances.get(tx.sender, 0) - tx.amount - tx.fee

    def add_transaction(self, transaction: Transaction, sender_private_key):
        if transaction.is_coinbase:
            print("Coinbase transactions cannot be added manually")
            return False

        try:
            transaction.validate()
        except ValueError as e:
            print(f"Invalid transaction: {e}")
            return False

        try:
            signature = Transaction.sign_transaction(transaction, sender_private_key)
        except ValueError as e:
            print(f"Failed to sign transaction: {e}")
            return False

        try:
            is_valid = Transaction.verify_signature(transaction, signature)
        except ValueError as e:
            print(f"Failed to verify transaction signature: {e}")
            return False

        if not is_valid:
            print("Invalid transaction signature")
            return False

        try:
            sender_balance = Wallet.get_balance(self, transaction.sender)
        except ValueError as e:
            print(f"Failed to check sender balance: {e}")
            return False

        total_cost = transaction.amount + transaction.fee
        if sender_balance < total_cost:
            print(
                f"Insufficient balance: sender has {sender_balance}, "
                f"tried to send {transaction.amount} with fee {transaction.fee}"
            )
            return False

        self.signatures.append(signature)
        self.pending_transactions.append(transaction)
        return True

    def mine_block(self, miner: Wallet):
        """Mine a new block with a coinbase reward transaction."""
        if not miner or not miner.public_address:
            print("Invalid miner: wallet must have a public address")
            return None

        if not self.chain:
            print("Cannot mine block: blockchain has no genesis block")
            return None

        last_block = self.chain[-1]

        # Create coinbase transaction (block reward + transaction fees)
        total_fees = sum(tx.fee for tx in self.pending_transactions)
        coinbase_tx = Transaction(
            sender_public_address=None,
            receiver_public_address=miner.public_address,
            amount=self.reward_amount + total_fees,
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
                if not self.save_to_txt(new_block):
                    return None
                self.chain.append(new_block)
                self._update_balances(new_block)
                self.pending_transactions = []
                self.signatures = []
                print(f"\nMined Block {len(self.chain) - 1} with hash {hash_result}\n")
                return new_block

    def save_to_txt(self, new_block, rwa='a'):
        try:
            with open("./Blockchain.txt", rwa) as file:
                json.dump(new_block.to_dict(), file)
                file.write("\n")
            return True
        except (OSError, TypeError, ValueError) as e:
            print(f"Failed to save block to file: {e}")
            return False

    def verify_protocol(self, content):
        if not content or not content.strip():
            print("Protocol verification failed: empty blockchain data")
            return False

        split_content = content.splitlines()
        if len(split_content) < 1:
            print("Protocol verification failed: no blocks found")
            return False

        try:
            for line_idx in range(len(split_content) - 1):
                line1 = split_content[line_idx]
                line2 = split_content[line_idx + 1]
                block1 = Block.from_dict(json.loads(line1))
                block2 = Block.from_dict(json.loads(line2))

                expected_hash = hashlib.sha256(
                    json.dumps(json.loads(line1), sort_keys=True).encode('utf-8')
                ).hexdigest()
                if block2.previous_hash != expected_hash:
                    print(f"Protocol verification failed: incorrect hash at index {line_idx + 1}")
                    return False

                signatures = block2.signatures
                transactions = block2.transactions
                if len(signatures) != len(transactions):
                    print(
                        "Protocol verification failed: unequal number of "
                        "signatures and transactions"
                    )
                    return False

                for sig_idx in range(len(signatures)):
                    tx = transactions[sig_idx]
                    sig = signatures[sig_idx]
                    if tx.is_coinbase:
                        if sig is not None:
                            print(
                                "Protocol verification failed: coinbase transaction "
                                "should not have a signature"
                            )
                            return False
                    else:
                        try:
                            if not Transaction.verify_signature(tx, sig):
                                print(
                                    f"Protocol verification failed: invalid signature "
                                    f"at block index {block2.index}, transaction {sig_idx}"
                                )
                                return False
                        except ValueError as e:
                            print(f"Protocol verification failed: {e}")
                            return False
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Protocol verification failed: malformed block data ({e})")
            return False

        return True