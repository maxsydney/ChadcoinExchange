import pytest
import time
from backend.test.testHelpers import Indexer, Sandbox, Account, Client, Convert, Transaction
from backend.services.chadExchangeService import ChadExchangeService
from backend.services.transactionService import get_default_suggested_params
from algosdk import constants
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction as algo_txn


class TestDelegatedSignatureContract:
    """
    Unit tests for the delegated signature contract
    """
    @classmethod
    def setup_class(cls):
        """
        Initialize tests with sandbox running and get test accounts
        """
        Sandbox.command("up", "release")
        Sandbox.command("reset")
        cls.client = Client.getClient()
        cls.admin, cls.user1, cls.user2 = Account.getTestAccounts()
        cls.chadID = Transaction.createChadToken(client=cls.client, owner=cls.admin)
    
    @classmethod
    def teardown_class(cls):
        Sandbox.command("down")

    