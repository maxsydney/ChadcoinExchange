import pytest
import time
from backend.test.testHelpers import Indexer, Sandbox, Account, Client, Convert, Transaction
from backend.services.chadExchangeService import ChadExchangeService
from backend.contracts.delegatedSignature import DelegatedSignature
from backend.services.transactionService import get_default_suggested_params
from algosdk import constants
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction
import base64

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

    def test_algoSig_wrongNumberTransactions(self):
        """
        Buying algo with chad - atomic group size is not 3
        """
        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSigSigned = delSig.sign(self.user1.privKey)

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=get_default_suggested_params(),
            receiver=self.admin.pubKey,
            amt=100
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=get_default_suggested_params(),
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSigSigned)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.pubKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)