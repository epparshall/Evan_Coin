import time
import json
import random

from Evan_Coin import Block
from Evan_Coin import Transaction
from Evan_Coin import Wallet


class Blockchain:
    DIFFICULTY_ADJUSTMENT_INTERVAL = 10
    TARGET_BLOCK_TIME = 600  # 10 minutes per block
    MIN_DIFFICULTY = 1
    MAX_DIFFICULTY = 32

    def __init__(
        self,
        reward_amount=10,
        genesis_reward_address=None,
        initial_difficulty=4,
    ):
        self.chain = []
        self.pending_transactions = []
        self.signatures = []
        self.balances = {}
        self.genesis_reward_address = genesis_reward_address
        self.initial_difficulty = initial_difficulty
        self.difficulty = initial_difficulty
        self.reward_amount = reward_amount  # Configurable block reward
        self.create_genesis_block()

    def create_genesis_block(self):
        if self.genesis_reward_address:
            # Include coinbase reward in genesis block (as requested in #9)
            genesis_coinbase = Transaction(
                sender_public_address=None,
                receiver_public_address=self.genesis_reward_address,
                amount=self.reward_amount,
                is_coinbase=True
            )
            genesis_block = Block(
                0,
                "0",
                [genesis_coinbase],
                [None],
                difficulty=self.initial_difficulty,
            )
        else:
            genesis_block = Block(
                0, "0", [], [], difficulty=self.initial_difficulty
            )
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

    @classmethod
    def calculate_difficulty_for_index(cls, chain, index, initial_difficulty=4):
        """Return the proof-of-work difficulty for the block at `index`."""
        if index == 0:
            return initial_difficulty

        period = (index - 1) // cls.DIFFICULTY_ADJUSTMENT_INTERVAL
        if period == 0:
            return initial_difficulty

        difficulty = initial_difficulty
        for period_number in range(1, period + 1):
            start_idx = (period_number - 1) * cls.DIFFICULTY_ADJUSTMENT_INTERVAL
            end_idx = period_number * cls.DIFFICULTY_ADJUSTMENT_INTERVAL
            if end_idx > len(chain):
                return difficulty

            actual_time = chain[end_idx - 1].timestamp - chain[start_idx].timestamp
            expected_time = cls.DIFFICULTY_ADJUSTMENT_INTERVAL * cls.TARGET_BLOCK_TIME
            if actual_time > 0:
                adjusted = difficulty * expected_time / actual_time
                difficulty = max(
                    cls.MIN_DIFFICULTY,
                    min(cls.MAX_DIFFICULTY, round(adjusted)),
                )

        return difficulty

    def get_difficulty_for_next_block(self):
        return self.calculate_difficulty_for_index(
            self.chain,
            len(self.chain),
            self.initial_difficulty,
        )

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
        block_index = len(self.chain)
        difficulty = self.get_difficulty_for_next_block()
        self.difficulty = difficulty

        while True:
            nonce = random.randint(0, 1000000000)
            block_timestamp = time.time()
            block_data = {
                "index": block_index,
                "previous_hash": last_block.hash,
                "transactions": [tx.to_dict() for tx in all_transactions],
                "signatures": all_signatures,
                "timestamp": block_timestamp,
                "nonce": nonce,
                "difficulty": difficulty,
            }

            hash_result = Block.calculate_hash_from_dict(block_data)

            if hash_result[:difficulty] == '0' * difficulty:
                new_block = Block(
                    block_index,
                    last_block.hash,
                    all_transactions,
                    all_signatures,
                    nonce=nonce,
                    difficulty=difficulty,
                    timestamp=block_timestamp,
                )
                if not self.save_to_txt(new_block):
                    return None
                self.chain.append(new_block)
                self._update_balances(new_block)
                self.pending_transactions = []
                self.signatures = []
                print(
                    f"\nMined Block {block_index} with hash {hash_result} "
                    f"(difficulty {difficulty})\n"
                )
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

    def _verify_block_proof_of_work(self, block_dict, chain, initial_difficulty):
        block_index = block_dict['index']
        if block_index == 0:
            return True

        if 'difficulty' not in block_dict or 'nonce' not in block_dict:
            # Legacy blocks mined before dynamic difficulty stored PoW metadata.
            return True

        expected_difficulty = self.calculate_difficulty_for_index(
            chain,
            block_index,
            initial_difficulty,
        )
        actual_difficulty = block_dict['difficulty']
        if actual_difficulty != expected_difficulty:
            print(
                "Protocol verification failed: incorrect difficulty at "
                f"index {block_index} (expected {expected_difficulty}, "
                f"got {actual_difficulty})"
            )
            return False

        block_hash = Block.calculate_hash_from_dict(block_dict)
        if block_hash[:actual_difficulty] != '0' * actual_difficulty:
            print(
                "Protocol verification failed: proof-of-work not satisfied at "
                f"index {block_index}"
            )
            return False

        return True

    def get_chain_height(self):
        """Return the current chain length (height)."""
        return len(self.chain)

    def serialize_chain(self):
        """Return the full chain as a list of block dictionaries."""
        return [block.to_dict() for block in self.chain]

    def _validate_block_signatures(self, block):
        signatures = block.signatures
        transactions = block.transactions
        if len(signatures) != len(transactions):
            return False

        for sig_idx, (tx, sig) in enumerate(zip(transactions, signatures)):
            if tx.is_coinbase:
                if sig is not None:
                    return False
            else:
                try:
                    if not Transaction.verify_signature(tx, sig):
                        return False
                except ValueError:
                    return False
        return True

    def _validate_block_balances(self, block):
        """Verify sender balances for all non-coinbase transactions in a block."""
        balances = dict(self.balances)
        for tx in block.transactions:
            if not tx.is_coinbase:
                sender_balance = balances.get(tx.sender)
                if sender_balance is None:
                    sender_balance = Wallet.get_balance(self, tx.sender)
                total_cost = tx.amount + tx.fee
                if sender_balance < total_cost:
                    return False
                balances[tx.sender] = sender_balance - total_cost
            if tx.receiver:
                balances[tx.receiver] = balances.get(tx.receiver, 0) + tx.amount
        return True

    def add_block(self, block):
        """Append a block that extends the current chain. Returns True on success."""
        if not self.chain:
            return False
        if block.index != len(self.chain):
            return False
        if block.previous_hash != self.chain[-1].hash:
            return False

        block_dict = block.to_dict()
        if not self._verify_block_proof_of_work(
            block_dict, self.chain, self.initial_difficulty
        ):
            return False
        if not self._validate_block_signatures(block):
            return False
        if not self._validate_block_balances(block):
            return False

        if not self.save_to_txt(block):
            return False

        self.chain.append(block)
        self._update_balances(block)
        return True

    def replace_chain(self, blocks):
        """Replace the local chain with a longer valid chain. Returns True on success."""
        if len(blocks) <= len(self.chain):
            return False

        chain_content = '\n'.join(json.dumps(block.to_dict()) for block in blocks)
        if not self.verify_protocol(chain_content):
            return False

        self.chain = list(blocks)
        self.balances = {}
        for block in self.chain:
            self._update_balances(block)
        self.pending_transactions = []
        self.signatures = []
        self.difficulty = self.get_difficulty_for_next_block()
        return True

    def verify_protocol(self, content, initial_difficulty=None):
        if not content or not content.strip():
            print("Protocol verification failed: empty blockchain data")
            return False

        split_content = content.splitlines()
        if len(split_content) < 1:
            print("Protocol verification failed: no blocks found")
            return False

        if initial_difficulty is None:
            initial_difficulty = self.initial_difficulty

        try:
            chain = []
            for line_idx, line in enumerate(split_content):
                block_dict = json.loads(line)
                block = Block.from_dict(block_dict)

                if block.index != line_idx:
                    print(
                        "Protocol verification failed: block index mismatch at "
                        f"line {line_idx}"
                    )
                    return False

                if line_idx > 0:
                    expected_hash = Block.calculate_hash_from_dict(
                        json.loads(split_content[line_idx - 1])
                    )
                    if block.previous_hash != expected_hash:
                        print(
                            "Protocol verification failed: incorrect hash at "
                            f"index {line_idx}"
                        )
                        return False

                if not self._verify_block_proof_of_work(
                    block_dict, chain, initial_difficulty
                ):
                    return False

                signatures = block.signatures
                transactions = block.transactions
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
                                    f"at block index {block.index}, transaction {sig_idx}"
                                )
                                return False
                        except ValueError as e:
                            print(f"Protocol verification failed: {e}")
                            return False

                chain.append(block)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Protocol verification failed: malformed block data ({e})")
            return False

        return True