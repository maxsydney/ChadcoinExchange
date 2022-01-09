import yaml
import os
from pyteal import compileTeal, Mode
from backend.services.networkInteraction import NetworkInteraction
from backend.services.transactionService import PaymentTransactionRepository, ASATransactionRepository
from backend.services.keyPair import KeyPair
from backend.contracts.chadExchange import ChadExchangeASC1
from algosdk import logic, kmd
from algosdk.v2client import algod
from algosdk.future import transaction as algo_txn

class ChadExchangeService:

    def __init__(self, client: algod.AlgodClient, admin: KeyPair, minChadTxThresh: int, chadID: int):
        self.client = client
        self.admin = admin
        self.minChadtxThresh = minChadTxThresh
        self.chadID = chadID
        self.contract = ChadExchangeASC1(adminAddr=self.admin.pubKey, chadID=self.chadID, minChadTxThresh=self.minChadtxThresh)

    @property
    def escrowBytes(self):
        exchangeCompiled = compileTeal(
            self.contract.program(),
            mode=Mode.Signature,
            version=5,
        )

        return NetworkInteraction.compile_program(
            client=self.client, source_code=exchangeCompiled
        )

    @property
    def escrowAddress(self):
        return logic.address(self.escrowBytes)

    def depositChad(self, amount: int) -> str:
        """
        Transfer chads from admin address to exchange
        """
        # Send some chads to exchange
        chadTxSigned = ASATransactionRepository.asa_transfer(
            client=self.client,
            sender_address=self.admin.pubKey,
            receiver_address=self.escrowAddress,
            asa_id=self.chadID,
            amount=amount,
            revocation_target=None,
            sender_private_key=self.admin.privKey,
            sign_transaction=True
        )

        print(f"\nFunding exchange with {amount} CHADS")
        txID = NetworkInteraction.submit_transaction(
            self.client, transaction=chadTxSigned
        )

        return txID
    
    def depositAlgo(self, amount: int) -> str:
        """
        Transfer Algos from admin address to exchange
        """
        txSigned = PaymentTransactionRepository.payment(
            client=self.client, 
            sender_address=self.admin.pubKey, 
            receiver_address=self.escrowAddress, 
            amount=amount, 
            sender_private_key=self.admin.privKey, 
            sign_transaction=True
        )
        
        print(f"\nFunding contract {self.escrowAddress}")
        txID = NetworkInteraction.submit_transaction(
            self.client, transaction=txSigned
        )

        return txID

    def withdrawChad(self, amount: int) -> str:
        withdrawChadTx = ASATransactionRepository.asa_transfer(
            client=self.client,
            sender_address=self.escrowAddress,
            receiver_address=self.admin.pubKey,
            asa_id=self.chadID,
            amount=amount,
            revocation_target=None,
            sender_private_key=None,
            sign_transaction=False
        )

        withdrawChadTxLogSig = algo_txn.LogicSig(self.escrowBytes)
        withdrawChadTxSigned = algo_txn.LogicSigTransaction(withdrawChadTx, withdrawChadTxLogSig)

        print(f"\nWithdrawing {amount} CHADs from exhange")
        txID = NetworkInteraction.submit_transaction(
            self.client, transaction=withdrawChadTxSigned
        )

        return txID

    def withdrawAlgo(self, amount: int) -> str:
        withdrawTx = PaymentTransactionRepository.payment(
            client=self.client,
            sender_address=self.escrowAddress, 
            receiver_address=self.admin.pubKey, 
            amount=amount, 
            sender_private_key=None, 
            sign_transaction=False
        )

        withdrawTxLogSig = algo_txn.LogicSig(self.escrowBytes)
        withdrawTxSigned = algo_txn.LogicSigTransaction(withdrawTx, withdrawTxLogSig)

        print(f"\nWithdrawing {amount} Algo from exhange")
        txID = NetworkInteraction.submit_transaction(
            self.client, transaction=withdrawTxSigned
        )

        return txID

    def swapAlgoForChad(self, algoAmount: float, chadsPerAlgo: float, buyerKey: KeyPair) -> str:

        # Convert amounts to native units
        algoAmount = int(algoAmount * 1e6)
        chadAmount = int(algoAmount * chadsPerAlgo)

        # First transaction is payment of algoAmount to contract
        algoPaymentTx = PaymentTransactionRepository.payment(
            client=self.client,
            sender_address=buyerKey.pubKey,
            receiver_address=self.escrowAddress,
            amount=algoAmount,
            sender_private_key=None,
            sign_transaction=False
        )

        # Second transaction is transfer of algo to buyer
        chadPaymentTx = ASATransactionRepository.asa_transfer(
            client=self.client,
            sender_address=self.escrowAddress,
            receiver_address=buyerKey.pubKey,
            amount=chadAmount,
            asa_id=self.chadID,
            sender_private_key=None,
            revocation_target=None,
            sign_transaction=False
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = PaymentTransactionRepository.payment(
            client=self.client,
            sender_address=self.admin.pubKey,
            receiver_address=self.escrowAddress,
            amount=0,
            sender_private_key=None,
            sign_transaction=False
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([
            algoPaymentTx,
            chadPaymentTx,
            approvalTx
        ])

        algoPaymentTx.group = gid
        chadPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        algoPaymentTxSigned = algoPaymentTx.sign(buyerKey.privKey)

        chadPaymentTxLogSig = algo_txn.LogicSig(self.escrowBytes)
        chadPaymentTxSigned = algo_txn.LogicSigTransaction(chadPaymentTx, chadPaymentTxLogSig)

        approvalTxSigned = approvalTx.sign(self.admin.privKey)

        signedGroup = [
            algoPaymentTxSigned,
            chadPaymentTxSigned,
            approvalTxSigned
        ]

        print(f"\nSending swap ({algoAmount/1e6} algo for {chadAmount/1e6} CHAD)")
        txID = self.client.send_transactions(signedGroup)
        NetworkInteraction.wait_for_confirmation(self.client, txID)

        return txID

    def swapChadForAlgo(self, chadAmount: int, chadsPerAlgo: int, buyerKey: KeyPair) -> str:
        # Convert amounts to native units
        chadAmount = int(chadAmount * 1e6)
        algoAmount = int(chadAmount / chadsPerAlgo)

        # First transaction is transfer of chad to contract
        chadPaymentTx = ASATransactionRepository.asa_transfer(
            client=self.client,
            sender_address=buyerKey.pubKey,
            receiver_address=self.escrowAddress,
            amount=chadAmount,
            asa_id=self.chadID,
            revocation_target=None,
            sender_private_key=None,
            sign_transaction=False
        )

        # Second transaction is payment of algoAmount to buyer
        algoPaymentTx = PaymentTransactionRepository.payment(
            client=self.client,
            sender_address=self.escrowAddress,
            receiver_address=buyerKey.pubKey,
            amount=algoAmount,
            sender_private_key=None,
            sign_transaction=False
        )

        # Third transaction is 0 algo tx from admin approving exchange rate
        approvalTx = PaymentTransactionRepository.payment(
            client=self.client,
            sender_address=self.admin.pubKey,
            receiver_address=self.escrowAddress,
            amount=0,
            sender_private_key=None,
            sign_transaction=False
        )

        # Atomic transfer
        gid = algo_txn.calculate_group_id([
            chadPaymentTx,
            algoPaymentTx,
            approvalTx
        ])

        chadPaymentTx.group = gid
        algoPaymentTx.group = gid
        approvalTx.group = gid

        # Sign transcations
        chadPaymentTxSigned = chadPaymentTx.sign(buyerKey.privKey)

        algoPaymentTxLogSig = algo_txn.LogicSig(self.escrowBytes)
        algoPaymentTxSigned = algo_txn.LogicSigTransaction(algoPaymentTx, algoPaymentTxLogSig)

        approvalTxSigned = approvalTx.sign(self.admin.privKey)

        signedGroup = [
            chadPaymentTxSigned,
            algoPaymentTxSigned,
            approvalTxSigned
        ]

        print(f"\nSending swap ({chadAmount / 1e6} CHAD for {algoAmount / 1e6} Algo)")
        txID = self.client.send_transactions(signedGroup)
        NetworkInteraction.wait_for_confirmation(self.client, txID)

        return txID

def createExchangeService(secrets: str) -> ChadExchangeService:
    """
    Create a chad exchange service object from config files

    inputs:
        secrets: Path to chadserver secrets directory
    """

    # Create algod daemon
    with open(os.path.join(secrets, 'algod.yaml')) as algodCfgFile:
        algodCfg = yaml.safe_load(algodCfgFile)
    url = algodCfg['url']
    token = algodCfg['token']
    client = algod.AlgodClient(algod_token=token, algod_address=url)

    # Access KMD client
    with open(os.path.join(secrets, 'kmd.yaml')) as kmdCfgFile:
        kmdCfg = yaml.safe_load(kmdCfgFile)
    url = kmdCfg['url']
    token = kmdCfg['token']
    kcl = kmd.KMDClient(kmd_address=url, kmd_token=token)

    # Get admin keypair
    wallets = kcl.list_wallets()
    chadWallet = None
    for wallet in wallets:
        if wallet['name'] == 'chadadmin':
            chadWallet = wallet
            break

    if not chadWallet:
        raise KeyError("chadadmin wallet not managed by local KMD instance. Does it exist?")

    handle = kcl.init_wallet_handle(chadWallet['id'], kmdCfg['walletPassword'])

    pubKeys = kcl.list_keys(handle)
    if len(pubKeys) != 1:
        raise ValueError(f"Expected one address in admin wallet (got {len(pubKeys)})")

    admin = KeyPair(pubKeys[0], kcl.export_key(handle, kmdCfg['walletPassword'], pubKeys[0]))

    # Get chadcoin ASA details
    with open(os.path.join(secrets, 'chadToken.yaml')) as chadCfgFile:
        chadCfg = yaml.safe_load(chadCfgFile)
    asaID = chadCfg['assetID']

    # Get exchange config
    with open(os.path.join(secrets, 'config.yaml')) as exchangeCfgFile:
        exchangeCfg = yaml.safe_load(exchangeCfgFile)
    minChadTxThresh = exchangeCfg['minChadTxThresh']

    return ChadExchangeService(client=client, admin=admin, minChadTxThresh=minChadTxThresh, chadID=asaID)