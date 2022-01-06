import pytest
import time
from backend.test.testHelpers import Indexer, Sandbox, Account, Client, Convert, Transaction, createExchange
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction as algo_txn


class TestChadExchangeContract:
    """
    Unit tests for the chad exchange contract
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
        cls.minChadThresh = Convert.chad2uChad(20)
        cls.exchange = createExchange(cls.client, cls.admin, cls.minChadThresh, chadID=cls.chadID)
    
    @classmethod
    def teardown_class(cls):
        Sandbox.command("down")

    def test_swapAlgoForChad_validSwap(self):
        """
        Swap logic approves valid swap
        """
        # Send some chads and algos to exchange to use for swaps
        self.exchange.depositAlgo(Convert.algo2uAlgo(10))
        self.exchange.depositChad(Convert.chad2uChad(50))

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # Wait for above transaction to confirm
        time.sleep(5)

        # Get account states before swap
        contractAccInfoStart = Indexer.accountInfo(self.exchange.escrowAddress)
        buyerAccInfoStart = Indexer.accountInfo(self.user1.pubKey)

        # Send a valid swap
        self.exchange.swapAlgoForChad(algoAmount=10, chadsPerAlgo=3, buyerKey=self.user1)

        # Allow transactions time to confirm
        time.sleep(5)

        # Get account states after swap
        contractAccInfoEnd = Indexer.accountInfo(self.exchange.escrowAddress)
        buyerAccInfoEnd = Indexer.accountInfo(self.user1.pubKey)

        # Compute balance changes
        deltaAlgoBuyer = buyerAccInfoEnd['account']['amount'] - buyerAccInfoStart['account']['amount']
        deltaAlgoContract = contractAccInfoEnd['account']['amount'] - contractAccInfoStart['account']['amount']
        deltaChadBuyer = buyerAccInfoEnd['account']['assets'][0]['amount']
        deltaChadContract = contractAccInfoEnd['account']['assets'][0]['amount'] - contractAccInfoStart['account']['assets'][0]['amount']
        fee = 1000

        # Buyer account has spent 10 Algo
        assert deltaAlgoBuyer == Convert.algo2uAlgo(-10) - fee

        # Buyer account has received 30 CHADS
        assert deltaChadBuyer == Convert.chad2uChad(30)

        # Contract account has spent 30 CHADS
        assert deltaChadContract == -Convert.chad2uChad(30)

        # Contract account has received 10 Algo
        assert deltaAlgoContract == Convert.algo2uAlgo(10) - fee

    def test_swapAlgoForChad_incorrectFee(self):
        """
        Swap logic fails when atomic group fees are not correct
        """
        pass

    def test_swapAlgoForChad_algoReceiverNotChadSender(self):
        """
        Swap logic fails when Algo receiver is not CHAD sender. In this test, an atomic group
        is created where the contract pays the user both algo and CHADS.
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract. Set the payment
        # to be from contract to 
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            sp=params
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)


    def test_swapAlgoForChad_algoSenderNotChadReceiver(self):
        """
        Swap logic fails when Algo sender is not CHAD receiver. In this test, user1 sends the
        algo to the contract, but the CHADS are paid to user2
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 2 into ChadCoin
        Transaction.sendAsset(self.client, self.user2.pubKey, self.user2.pubKey, self.user2.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to user 2
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user2.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            sp=params
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_swapAlgoForChad_wrongAsset(self):
        """
        Swap logic fails when swap asset is not CHAD
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID + 1,
            sp=params
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_swapAlgoForChad_assetSender(self):
        """
        Swap logic fails when asset_sender is not zero address
        """
        pass

    def test_swapAlgoForChad_assetCloseTo(self):
        """
        Swap logic fails when asset_close_to address is not zero address
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            close_assets_to=self.user1.pubKey,
            sp=params
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_swapAlgoForChad_rekeyAsset(self):
        """
        Swap logic fails when rekey_address is not zero address
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            rekey_to=self.user1.pubKey,
            sp=params
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_swapAlgoForChad_belowMinThresh(self):
        """
        Swap logic fails when CHAD amount is below minimum threshold
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = self.minChadThresh - 1
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            sp=params
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_swapAlgoForChad_approvalNotAdmin(self):
        """
        Swap logic fails when approval transaction doesn't come from admin
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            sp=params
        )

        # Approval transaction doesn't come from admin account
        approvalTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=0,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_swapAlgoForChad_approvalAmount(self):
        """
        Swap logic fails when approval transaction amount is not 0 Algo
        """
        # Convert amounts to native units
        algoAmount = Convert.algo2uAlgo(10)
        chadAmount = algoAmount * 3
        params = self.client.suggested_params()

        # Opt user 1 into ChadCoin
        Transaction.sendAsset(self.client, self.user1.pubKey, self.user1.pubKey, self.user1.privKey, 0, self.exchange.chadID)

        # First transaction is payment of algoAmount to contract.
        algoPaymentTx = algo_txn.PaymentTxn(
            sender=self.user1.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=algoAmount,
            sp=params,
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=chadAmount,
            index=self.exchange.chadID,
            sp=params
        )

        # Third transaction is 1 algo tx from admin approving exchange rate
        approvalTx = algo_txn.PaymentTxn(
            sender=self.admin.pubKey,
            receiver=self.exchange.escrowAddress,
            amt=1,
            sp=params,
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([algoPaymentTx, chadPaymentTx, approvalTx])
        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(self.user1.privKey)
        chadPaymentTxLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)
        approvalTxSigned = approvalTx.sign(self.admin.privKey)
        signedGroup = [algoPaymentTxSigned, chadPaymentTxSigned, approvalTxSigned]

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transactions(signedGroup)

    def test_adminAlgoWithdraw(self):
        """
        Withdraw algos from the exchange using the admin account
        """
        fee = 1000

        # Fund the exchange with some algo to withdraw later
        self.exchange.depositAlgo(Convert.algo2uAlgo(10))

        # Wait for above transaction to confirm
        time.sleep(5)

        # Get account state before withdrawal
        contractAccInfoStart = Indexer.accountInfo(self.exchange.escrowAddress)
        adminAccInfoStart = Indexer.accountInfo(self.admin.pubKey)

        # Withdraw some algo from contract
        self.exchange.withdrawAlgo(Convert.algo2uAlgo(5))

        # Wait for above transaction to confirm
        time.sleep(5)

        # Get contract account state before withdrawal
        contractAccInfoEnd = Indexer.accountInfo(self.exchange.escrowAddress)
        adminAccInfoEnd = Indexer.accountInfo(self.admin.pubKey)

        deltaAlgoContract = contractAccInfoEnd['account']['amount'] - contractAccInfoStart['account']['amount']
        deltaAlgoAdmin = adminAccInfoEnd['account']['amount'] - adminAccInfoStart['account']['amount']

        assert deltaAlgoContract == Convert.algo2uAlgo(-5) - fee
        assert deltaAlgoAdmin == Convert.algo2uAlgo(5)


    def test_userAlgoWithdraw(self):
        """
        Non-admin accounts attempting to withdraw algo should cause
        logic failure
        """
        # Fund the exchange with some algo
        self.exchange.depositAlgo(Convert.algo2uAlgo(10))

        # Create a transaction withdrawing algo from the contract to a non-user account
        tx = algo_txn.PaymentTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=Convert.algo2uAlgo(5),
            sp=self.client.suggested_params()
        )

        txLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        txSigned = algo_txn.LogicSigTransaction(tx, txLogSig)

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transaction(txSigned)

    def test_adminChadWithdraw(self):
        """
        Withdraw CHADS from the exchange using the admin account
        """
        # Fund the exchange with some CHADS to withdraw later
        self.exchange.depositChad(Convert.chad2uChad(10))

        # Wait for above transaction to confirm
        time.sleep(5)

        # Get account state before withdrawal
        contractAccInfoStart = Indexer.accountInfo(self.exchange.escrowAddress)
        adminAccInfoStart = Indexer.accountInfo(self.admin.pubKey)

        # Withdraw some algo from contract
        self.exchange.withdrawChad(Convert.chad2uChad(5))

        # Wait for above transaction to confirm
        time.sleep(5)

        # Get contract account state before withdrawal
        contractAccInfoEnd = Indexer.accountInfo(self.exchange.escrowAddress)
        adminAccInfoEnd = Indexer.accountInfo(self.admin.pubKey)

        deltaChadContract = contractAccInfoEnd['account']['assets'][0]['amount'] - contractAccInfoStart['account']['assets'][0]['amount']
        deltaChadAdmin = adminAccInfoEnd['account']['assets'][0]['amount'] - adminAccInfoStart['account']['assets'][0]['amount']

        assert deltaChadContract == Convert.chad2uChad(-5)
        assert deltaChadAdmin == Convert.chad2uChad(5)

    def test_userChadWithdraw(self):
        """
        Non-admin accounts attempting to withdraw CHADS should cause
        logic failure
        """
        # Fund the exchange with some algo
        self.exchange.depositChad(Convert.chad2uChad(10))

        # Create a transaction withdrawing chad from the contract to a non-user account
        tx = algo_txn.AssetTransferTxn(
            sender=self.exchange.escrowAddress,
            receiver=self.user1.pubKey,
            amt=Convert.algo2uAlgo(5),
            index=self.exchange.chadID,
            sp=self.client.suggested_params()
        )

        txLogSig = algo_txn.LogicSig(self.exchange.escrowBytes)
        txSigned = algo_txn.LogicSigTransaction(tx, txLogSig)

        # Check logic fails
        with pytest.raises(AlgodHTTPError):
            self.client.send_transaction(txSigned)