import pytest

from Evan_Coin.wallet import Wallet


class TestWalletKeyGeneration:
    def test_generates_valid_key_pair(self):
        wallet = Wallet()

        assert len(wallet.private_key) == 64
        assert len(wallet.public_address) == 128
        assert all(c in "0123456789abcdef" for c in wallet.private_key)
        assert all(c in "0123456789abcdef" for c in wallet.public_address)

    def test_get_address_returns_public_address(self):
        wallet = Wallet()
        assert wallet.get_address() == wallet.public_address

    def test_each_wallet_has_unique_keys(self):
        w1, w2 = Wallet(), Wallet()
        assert w1.private_key != w2.private_key
        assert w1.public_address != w2.public_address