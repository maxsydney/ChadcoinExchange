from pyteal import *

class DelegatedSignature:
    """
    Delegated signature transaction for floating exchange payments
    """

    @staticmethod
    def algoSig(exchangeAddr: str, noMoreThan: int):
        """
        Returns a TEAL delegated signature approval program for spending up to noMoreThan
        Algos
        """
        actions = Cond(
            [DelegatedSignature.isAlgoTx(), DelegatedSignature.validateAlgoTx(exchangeAddr, noMoreThan)]
        )

        return compileTeal(actions, Mode.Signature, version=5)

    @staticmethod
    def chadSig(exchangeAddr: str, noMoreThan: int, chadID: int):
        """
        Returns a TEAL delegated signature approval program for spending up to noMoreThan
        Chads 
        """
        actions = Cond(
            [DelegatedSignature.isChadTx(chadID), DelegatedSignature.validateChadTx(exchangeAddr, noMoreThan)]
        )

        return compileTeal(actions, Mode.Signature, version=5)

    @staticmethod
    def isAlgoTx():
        """
        Returns true if the transaction is an algo transfer
        """

        return And(
            Global.group_size() == Int(1),                      # Single Tx
            Txn.type_enum() == TxnType.Payment,                 # Type is algo tx
        )

    @staticmethod
    def isChadTx(chadID: int):
        """
        Returns true if the transaction is a ChadCoin transfer
        """
        return And(
            Global.group_size() == Int(1),                  # Single Tx
            Txn.type_enum() == TxnType.AssetTransfer,       # Type is asset tx
            Txn.xfer_asset() == Int(chadID),                # Asset is ChadCoin
        )

    @staticmethod
    def validateAlgoTx(exchangeAddr: str, noMoreThan: int):
        """
        Transaction is validated if
        - Receiver is chadcoin exchange address
        - Algo amount is no more than limit
        - Generic security criteria is met 
        """
        return And(
            Txn.receiver() == Addr(exchangeAddr),               # Payment is to admin addr
            Txn.fee() <= Int(1000),                             # Fee is sensible
            Txn.amount() <= Int(noMoreThan),                    # Amount is less than limit
            Txn.close_remainder_to() == Global.zero_address(),  # Prevent close remainder to
            Txn.rekey_to() == Global.zero_address()             # Prevent rekey
        )

    @staticmethod
    def validateChadTx(exchangeAddr: str, noMoreThan: int):
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