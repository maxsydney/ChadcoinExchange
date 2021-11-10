import os
import subprocess
import pty
import time

from backend.services.keyPair import KeyPair
from backend.services.transactionService import get_default_suggested_params
from algosdk import kmd
from algosdk.v2client import algod
from algosdk.future import transaction as algo_txn
from algosdk.v2client import indexer
from algosdk.error import IndexerHTTPError

class Sandbox:
    """
    Test helpers for the sandbox local network
    """

    sandboxExecutable = os.path.join(os.environ.get("SANDBOX"), "sandbox")

    @staticmethod
    def command(*args):
        """Call and return sandbox command composed from provided arguments."""
        return subprocess.run(
            [Sandbox.sandboxExecutable, *args], stdin=pty.openpty()[1], capture_output=True
        )

class Account:
    """
    Test helpers for managing accounts
    """

    @staticmethod
    def getTestAccounts():
        """
        Return accounts for unit testing
        """
        kcl = kmd.KMDClient(
            kmd_address="http://localhost:4002", 
            kmd_token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

        wallet = kcl.list_wallets()[0]
        handle = kcl.init_wallet_handle(wallet["id"], "")
        return list(KeyPair(pubKey, kcl.export_key(handle, "", pubKey)) for pubKey in kcl.list_keys(handle))

class Client:
    """
    Test helpers for algod client
    """

    @staticmethod
    def getClient():
        """
        Returns an algod client
        """
        client = algod.AlgodClient(
            algod_token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 
            algod_address="http://localhost:4001"
        )

        return client

class Transaction:
    """
    Test helpers for transactions
    """

    @staticmethod
    def waitForConfirmation(client: algod.AlgodClient, txid: int) -> str:
        """
        Utility function to wait until the transaction is
        confirmed before proceeding.
        """
        lastRound = client.status().get('last-round')
        txinfo = client.pending_transaction_info(txid)
        while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
            print("Waiting for confirmation")
            lastRound += 1
            client.status_after_block(lastRound)
            txinfo = client.pending_transaction_info(txid)
        print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
        return txinfo

    @staticmethod
    def sendAlgo(client: algod.AlgodClient, senderAddr: str, receiverAddr: str, signingKey: str, amount: int,
                 fee: int, closeRemainderTo=None, note=None, lease=None, rekeyTo=None) -> str:

        tx = algo_txn.PaymentTxn(
            sender=senderAddr,
            sp=client.suggested_params(),
            receiver=receiverAddr,
            amt=amount,
            close_remainder_to=closeRemainderTo,
            note=note,
            lease=lease,
            rekey_to=rekeyTo
        )

        txSigned = tx.sign(private_key=signingKey)
        txid = client.send_transaction(txSigned)
        Transaction.waitForConfirmation(client, txid)
        return txid

    @staticmethod
    def createChadToken(client: algod.AlgodClient, owner: KeyPair) -> int:
        """
        Create a chadcoin ASA that belongs to owner
        """
        params = client.suggested_params()

        tx = algo_txn.AssetConfigTxn(
            sender=owner.pubKey,
            sp=params,
            total=Convert.chad2uChad(1200000),
            default_frozen=False,
            unit_name="CHAD",
            asset_name="Chadcoin",
            manager=owner.pubKey,
            reserve=None,
            freeze=None,
            clawback=None,
            url=None,
            decimals=6,
            note=None,
            strict_empty_address_check=False
        )

        txSigned = tx.sign(private_key=owner.privKey)
        txid = client.send_transaction(txSigned)
        Transaction.waitForConfirmation(client, txid)
        ptx = client.pending_transaction_info(txid)
        asset_id = ptx["asset-index"]

        return asset_id

    @staticmethod
    def sendAsset(client: algod.AlgodClient, senderAddr: str, receiverAddr: str, signingKey: str, amount: int, asaID: int,
                 closeAssetsTo=None, revocationTarget=None, note=None,
                 lease=None, rekeyTo=None):

        sp = get_default_suggested_params(client=client)

        tx = algo_txn.AssetTransferTxn(
            sender=senderAddr,
            receiver=receiverAddr,
            amt=amount,
            index=asaID,
            close_assets_to=closeAssetsTo,
            revocation_target=revocationTarget,
            note=note,
            lease=lease,
            rekey_to=rekeyTo,
            sp=sp
        )

        txSigned = tx.sign(signingKey)
        txid = client.send_transaction(txSigned)
        Transaction.waitForConfirmation(client, txid)
        return txid
class Convert:
    """
    Conversion utilities
    """
    @staticmethod
    def uChad2Chad(uChads: int) -> float:
        """
        Convert microChads to Chads
        """
        return uChads / 1e6

    @staticmethod
    def chad2uChad(chads: float) -> int:
        """
        Convert Chads to microChads
        """
        return int(chads * 1e6)

    @staticmethod
    def uAlgo2Algo(uAlgo: int) -> float:
        """
        Convert microAlgo to Algo
        """
        return uAlgo / 1e6

    @staticmethod
    def algo2uAlgo(algo: float) -> int:
        """
        Convert Algo to microAlgo
        """
        return int(algo * 1e6)

class Indexer:
    """
    Private net indexer for unit tests
    """

    indexerAddress = "http://localhost:8980"
    indexerToken = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    timeout = 10
    client = indexer.IndexerClient(indexerToken, indexerAddress)

    @staticmethod
    def transactionInfo(txID: int) -> dict:
        """
        Return transaction information for txID
        """
        timeout = 0
        while timeout < Indexer.timeout:
            try:
                transaction = Indexer.client.transaction(txID)
                break
            except IndexerHTTPError:
                time.sleep(1)
                timeout += 1
        else:
            raise TimeoutError(
                "Timeout reached waiting for transaction to be available in indexer"
            )

        return transaction

    @staticmethod
    def accountInfo(address: str) -> dict:
        """
        Return information about account with address
        """
        timeout = 0
        while timeout < Indexer.timeout:
            try:
                accountInfo = Indexer.client.account_info(address)
                break
            except IndexerHTTPError:
                time.sleep(1)
                timeout += 1
        else:
            raise TimeoutError(
                "Timeout reached waiting for transaction to be available in indexer"
            )

        return accountInfo
