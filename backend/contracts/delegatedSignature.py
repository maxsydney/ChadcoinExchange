from pyteal import *
import hashlib

class DelegatedSignature:
    """
    Delegated signature transaction for floating exchange payments
    """

    @staticmethod
    def algoSig(exchangeAddr: str, noMoreThan: int, buyAmt: int, chadID: int):
        """
        Returns a TEAL delegated signature approval program for spending up to noMoreThan
        Algos in exhange for buyAmt Chads
        """
        actions = Cond(
            [DelegatedSignature.isAlgoTx(chadID), DelegatedSignature.validateAlgoTx(exchangeAddr, noMoreThan, buyAmt)]
        )

        return compileTeal(actions, Mode.Signature, version=5)

    @staticmethod
    def chadSig(exchangeAddr: str, noMoreThan: int, buyAmt: int, chadID: int):
        """
        Returns a TEAL delegated signature approval program for spending up to noMoreThan
        Chads in exhange for buyAmt Algos
        """
        actions = Cond(
            [DelegatedSignature.isChadTx(chadID), DelegatedSignature.validateChadTx(exchangeAddr, noMoreThan, buyAmt)]
        )

        return compileTeal(actions, Mode.Signature, version=5)

    @staticmethod
    def isAlgoTx(chadID: int):
        """
        Returns true if the transaction is an algo transfer
        """

        return And(
            Global.group_size() == Int(3),                      # Atomic group
            Gtxn[0].type_enum() == TxnType.Payment,             # First tx is payment
            Gtxn[1].type_enum() == TxnType.AssetTransfer,       # Second tx is asset transfer
            Gtxn[1].xfer_asset() == Int(chadID),                # Asset is ChadCoin
        )

    @staticmethod
    def isChadTx(chadID: int):
        """
        Returns true if the transaction is a ChadCoin transfer
        """
        return And(
            Global.group_size() == Int(3),                      # Atomic group
            Gtxn[0].type_enum() == TxnType.AssetTransfer,       # First tx is asset transfer
            Gtxn[0].xfer_asset() == Int(chadID),                # Asset is ChadCoin
            Gtxn[1].type_enum() == TxnType.Payment,             # Second tx is payment
        )

    @staticmethod
    def validateAlgoTx(exchangeAddr: str, noMoreThan: int, buyAmt: int):
        """
        Transaction is validated if
        - Tx0 Receiver is chadcoin exchange address
        - Tx0 Algo amount is no more than limit
        - Tx1 asset receiver is Tx0 sender
        - Tx1 Chad amount is buyAmt
        - Lease is set
        - Expiry is set
        - Generic security criteria is met 
        """
        return And(
            Gtxn[0].receiver() == Addr(exchangeAddr),               # Payment is to admin addr
            Gtxn[0].fee() <= Int(1000),                             # Fee is sensible
            Gtxn[0].amount() <= Int(noMoreThan),                    # Amount is less than limit
            Gtxn[0].close_remainder_to() == Global.zero_address(),  # Prevent close remainder to
            Gtxn[0].rekey_to() == Global.zero_address(),            # Prevent rekey
            Gtxn[0].lease() == Bytes(hashlib.sha256("ChadCoin".encode()).digest()),                   # Lease is set
            Gtxn[1].asset_receiver() == Gtxn[0].sender(),           # Tx1 asset receiver is Tx0 sender
            Gtxn[1].asset_amount() == Int(buyAmt),                  # Tx1 Chad amount is buyAmt
            Gtxn[1].fee() <= Int(1000),                             # Fee is sensible
        )

    @staticmethod
    def validateChadTx(exchangeAddr: str, noMoreThan: int, buyAmt: int):
        """
        Transaction is validated if
        - Receiver is chadcoin exchange address
        - Chad amount is no more than limit
        - Generic security criteria is met 
        """
        return And(
            Txn.asset_receiver() == Addr(exchangeAddr),         # Payment is to admin addr
            Txn.fee() <= Int(1000),                             # Fee is sensible
            Txn.asset_amount() <= Int(noMoreThan),              # Amount is less than limit
            Txn.asset_close_to() == Global.zero_address(),      # Prevent close asset to
            Txn.rekey_to() == Global.zero_address()             # Prevent rekey
        )