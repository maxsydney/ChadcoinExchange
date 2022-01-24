import pytest
import time
from backend.test.testHelpers import Indexer, Sandbox, Account, Client, Transaction, wait
from backend.services.chadExchangeService import ChadExchangeService
from backend.contracts.delegatedSignature import DelegatedSignature
from backend.services.transactionService import get_default_suggested_params
from algosdk import constants
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction
import base64
import hashlib

class TestDelegatedSignatureContractBuyChad:
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

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(cls.client, cls.user1.pubKey, cls.user1.pubKey, cls.user1.privKey, 0, cls.chadID)
    
    @classmethod
    def teardown_class(cls):
        Sandbox.command("down")

    def test_algoSig_success(self):
        """
        Successful buy chad with algo using delegated signature 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic succeeds
        self.client.send_transactions(signedGroup)

        # Replay attack fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_wrongNumberTransactions(self):
        """
        Buying chad with algo - atomic group size is not 3
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=get_default_suggested_params(self.client),
            receiver=self.admin.pubKey,
            amt=100
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=get_default_suggested_params(self.client),
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
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_twoPaymentTransactions(self):
        """
        Contract rejects transaction where first two transactions are algo payments
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        algoPaymentTx2 = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            algoPaymentTx2,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        algoPaymentTx2.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        algoPaymentTx2Signed = algoPaymentTx2.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            algoPaymentTx2Signed,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_paymentToWrongAddress(self):
        """
        Algo withdrawn from users account may only be transferred to exchange account 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.user2.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_userFeeTooHigh(self):
        """
        Delegated signature fails when user transaction fee is too high 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        # Increase fee above limit
        algoPaymentTx.fee = 5000

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_userCostGreaterThanLimit(self):
        """
        Delegated signature fails when requesting more algo from user than agreed 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=110,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_closeRemainderTo(self):
        """
        Delegated signature fails when attempting to close users acc remainder to 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
            close_remainder_to=self.user2.pubKey
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)
    
    def test_algoSig_userRekeyTo(self):
        """
        Delegated signature fails when attempting to rekey users acc 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
            rekey_to=self.user2.pubKey
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_incorrectLease(self):
        """
        Delegated signature fails when incorrect lease is used
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("Incorrect".encode()).digest(),
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)
    
    def test_algoSig_noLease(self):
        """
        Delegated signature fails when no lease is used
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_assetReceiverNotAlgoSender(self):
        """
        Delegated signature rejects transaction when asset receiver is not algo sender
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user2.pubKey,
            amt=500,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_algoSig_incorrectChadAmount(self):
        """
        Delegated signature rejects transaction when chad amount is incorrect
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.algoSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        algoPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=90,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=400,
            index=self.chadID
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            validationPaymentTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        algoPaymentTxSigned = transaction.LogicSigTransaction(algoPaymentTx, delSig)
        chadPaymentTxSigned = chadPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

class TestDelegatedSignatureContractBuyAlgo:
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

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(cls.client, cls.user1.pubKey, cls.user1.pubKey, cls.user1.privKey, 0, cls.chadID)

        # Send user 1 some chadcoin to play with
        Transaction.sendAsset(cls.client, cls.admin.pubKey, cls.user1.pubKey, cls.admin.privKey, 1000000, cls.chadID)
    
    @classmethod
    def teardown_class(cls):
        Sandbox.command("down")

    def test_chadSig_success(self):
        """
        Successful buy algo with chad using delegated signature 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic succeeds
        self.client.send_transactions(signedGroup)

        # Replay attack fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_wrongNumberTransactions(self):
        """
        Buy algo with chadcoin - no validation transaction
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_twoChadcoinTransactions(self):
        """
        Buy algo with chadcoin - both transactions are chadcoin 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        chadPaymentTx2 = transaction.AssetTransferTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            chadPaymentTx2,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        chadPaymentTx2.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        chadPaymentTx2Signed = chadPaymentTx2.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            chadPaymentTx2Signed,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_paymentToWrongAddress(self):
        """
        Chads withdrawn from users account may only be transferred to exchange account  
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Opt user 2 into chadcoin
        Transaction.sendAsset(self.client, self.user2.pubKey, self.user2.pubKey, self.user2.privKey, 0, self.chadID)

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.user2.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_userFeeTooHigh(self):
        """
        Delegated signature rejects transaction when user fee is too high 
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        chadPaymentTx.fee = 5000

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_userCostIncorrect(self):
        """
        Delegated signature rejects transaction when user chad cost is too great
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=510,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest()
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_assetCloseTo(self):
        """
        Delegated signature rejects transaction when attempting to close assets to nonzero address
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
            close_assets_to=self.user1.pubKey
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_userRekeyTo(self):
        """
        Delegated signature rejects transaction when attempting to rekey users account
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
            rekey_to=self.user2.pubKey
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_incorrectLease(self):
        """
        Delegated signature fails when incorrect lease is used
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("Incorrect".encode()).digest(),
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_noLease(self):
        """
        Delegated signature fails when no lease is used
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_algoReceiverNotAssentSender(self):
        """
        Delegated signature rejects transaction when algo receiver is not the user
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user2.pubKey,
            amt=110
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_chadSig_incorrectAlgoAmount(self):
        """
        Delegated signature fails when user receives an incorrect amount of Algo
        """
        # Wait 2 rounds
        wait(self.client, 2)

        # Get delegated signature from user
        tealContract = DelegatedSignature.chadSig(self.admin.pubKey, 100, 500, self.chadID)
        program = base64.decodebytes(self.client.compile(tealContract)['result'].encode())
        delSig = transaction.LogicSig(program)
        delSig.sign(self.user1.privKey)

        sp = get_default_suggested_params(self.client)
        sp.last = self.client.status()['last-round'] + 2

        # Create atomic group
        chadPaymentTx = transaction.AssetTransferTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=500,
            index=self.chadID,
            lease=hashlib.sha256("ChadCoin".encode()).digest(),
        )

        algoPaymentTx = transaction.PaymentTxn(
            sender=self.admin.pubKey,
            sp=sp,
            receiver=self.user1.pubKey,
            amt=90
        )

        validationPaymentTx = transaction.PaymentTxn(
            sender=self.user1.pubKey,
            sp=sp,
            receiver=self.admin.pubKey,
            amt=0
        )

        # Atomic transfer
        gid = transaction.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            validationPaymentTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        validationPaymentTx.group = gid

        # Sign transactions
        chadPaymentTxSigned = transaction.LogicSigTransaction(chadPaymentTx, delSig)
        algoPaymentTxSigned = algoPaymentTx.sign(self.admin.privKey)
        validationPaymentTxSigned = validationPaymentTx.sign(self.user1.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            validationPaymentTxSigned
        ]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)
