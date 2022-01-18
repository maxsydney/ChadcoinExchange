from pyteal import *

class ChadExchangeASC1:
    """
    Chad escrow account that holds all the CHAD and Algo available for
    swap. There are 4 possible transactions that this contract will
    approve

    - Opt contract into CHAD ASA
    - Swap CHAD and Algo
    - Withdraw Algo
    - Withdraw CHAD
    """

    def __init__(self, adminAddr: str, chadID: int, minChadTxThresh: int):
        self.adminAddr = adminAddr
        self.chadID = chadID
        self.minChadTxThresh = minChadTxThresh

    def program(self):
        actions = Cond(
            [self.isOptIn(), self.handleOptIn()],
            [self.isWithdrawAlgo(), self.handleWithdrawAlgo()],
            [self.isWithdrawChad(), self.handleWithdrawChad()],
            [self.isSwapAlgoForChad(), self.handleSwapAlgoForChad()],
            [self.isSwapChadForAlgo(), self.handleSwapChadForAlgo()],
            [Int(1), Int(0)]    # Fail if none of the criteria are met
        )

        return actions

    def isOptIn(self):
        """
        Returns true if the transaction is opting the contract into
        CHAD ASA
        """
        # TODO: Prevent repeated opt-in transactions to drain algo via fees

        return And(
            Global.group_size() == Int(1),                  # Single Tx
            Txn.type_enum() == TxnType.AssetTransfer,       # Type is asset tx
            Txn.sender() == Txn.asset_receiver(),           # Sender is receiver
        )

    def isSwapAlgoForChad(self):
        """
        Expect atomically grouped transaction made up of
        1. Payment of algo from user to contract
        2. Transfer of Chad from contract to user
        3. Approval 0 algo tx from admin approving exchange rate
        """

        return (If(Global.group_size() == Int(3)).Then(
            And(
                Gtxn[0].type_enum() == TxnType.Payment,            # First tx is payment
                Gtxn[1].type_enum() == TxnType.AssetTransfer       # Second tx is asset transfer
            )
        ).Else(
            Return(Int(0))
        ))
        
    def isSwapChadForAlgo(self):
        """
        Expect atomically grouped transaction made up of
        1. Transfer of Chad from user to conract
        2. Payment of algo from contract to user
        3. Approval 0 algo tx from admin approving exchange rate
        """
        return If(Global.group_size() == Int(3)).Then(
            And(
                Gtxn[0].type_enum() == TxnType.AssetTransfer,       # First tx is asset transfer
                Gtxn[1].type_enum() == TxnType.Payment,             # Second tx is payment
            )
        ).Else(
            Return(Int(0))
        )

    def isWithdrawAlgo(self):
        """
        Returns true if the transaction is an algo transfer from
        contract to admin address
        """

        return And(
            Global.group_size() == Int(1),                      # Single Tx
            Txn.type_enum() == TxnType.Payment,                 # Type is algo tx
        )

    def isWithdrawChad(self):
        """
        Returns true if the transaction is a CHAD transfer from
        contract to admin address
        """
        return And(
            Global.group_size() == Int(1),                  # Single Tx
            Txn.type_enum() == TxnType.AssetTransfer,       # Type is asset tx
            Txn.sender() != Txn.asset_receiver(),           # Sender is not receiver
        )

    def handleOptIn(self):
        """
        Approve opt-in transaction
        """

        return And(
            Txn.xfer_asset() == Int(self.chadID),                # Correct ASA ID
            Txn.asset_amount() == Int(0),                   # 0 asset tx
            Txn.fee() <= Int(1000),                         # Fee is sensible
            Txn.asset_sender() == Global.zero_address(),    # No clawback address
            Txn.asset_close_to() == Global.zero_address(),  # Prevent close-to
            Txn.rekey_to() == Global.zero_address()         # Prevent rekey
        )

    def handleSwapAlgoForChad(self):
        """
        Approve swap algo for chad transaction
        """

        return And(
            Gtxn[0].fee() <= Int(1000),                           # Appropriate fee
            Gtxn[0].receiver() == Gtxn[1].sender(),             # Check valid swap
            Gtxn[1].asset_receiver() == Gtxn[0].sender(),       # Sending asset to correct account
            Gtxn[1].xfer_asset() == Int(self.chadID),                # Correct asset
            Gtxn[1].fee() <= Int(1000),                         # Appropriate fee
            Gtxn[1].asset_sender() == Global.zero_address(),    # No clawback address
            Gtxn[1].asset_close_to() == Global.zero_address(),  # Prevent close-to
            Gtxn[1].rekey_to() == Global.zero_address(),        # Prevent rekey
            Gtxn[1].asset_amount() >= Int(self.minChadTxThresh), # Above min swap size 
            Gtxn[2].type_enum() == TxnType.Payment,             # Third transaction is payment
            Gtxn[2].sender() == Addr(self.adminAddr),                 # Third transaction from admin
            Gtxn[2].amount() == Int(0),                         # Amount is 0
            Gtxn[2].fee() <= Int(1000)                          # Fee is sensible
        )

    def handleSwapChadForAlgo(self):

        return And(
            Gtxn[0].fee() <= Int(1000),                           # Appropriate fee
            Gtxn[0].xfer_asset() == Int(self.chadID),                # Correct asset
            Gtxn[0].asset_amount() >= Int(self.minChadTxThresh), # Above min swap size 
            Gtxn[0].asset_sender() == Global.zero_address(),    # No clawback address
            Gtxn[0].asset_close_to() == Global.zero_address(),  # Prevent close-to
            Gtxn[0].rekey_to() == Global.zero_address(),        # Prevent rekey
            Gtxn[1].receiver() == Gtxn[0].sender(),             # Sending algo to correct account
            Gtxn[1].fee() <= Int(1000),                         # Appropriate fee
            Gtxn[1].close_remainder_to() == Global.zero_address(),   # Prevent close remainder to
            Gtxn[1].rekey_to() == Global.zero_address(),             # Prevent rekey
            Gtxn[2].type_enum() == TxnType.Payment,             # Third transaction is payment
            Gtxn[2].sender() == Addr(self.adminAddr),                 # Third transaction from admin
            Gtxn[2].amount() == Int(0),                         # Amount is 0
            Gtxn[2].fee() <= Int(1000)                          # Fee is sensible
        )

    def handleWithdrawAlgo(self):
        """
        Approve withdraw algo transaction
        """

        return And(
            Txn.receiver() == Addr(self.adminAddr),                   # Payment is to admin addr
            Txn.fee() <= Int(1000),                             # Fee is sensible
            Txn.close_remainder_to() == Global.zero_address(),   # Prevent close remainder to
            Txn.rekey_to() == Global.zero_address()             # Prevent rekey
        )

    def handleWithdrawChad(self):
        """
        Approve withdraw chad transaction
        """
        return And(
            Txn.asset_receiver() == Addr(self.adminAddr),         # Payment is to admin addr
            Txn.xfer_asset() == Int(self.chadID),                # Correct ASA ID
            Txn.fee() <= Int(1000),                         # Fee is sensible
            Txn.asset_sender() == Global.zero_address(),    # No clawback address
            Txn.asset_close_to() == Global.zero_address(),  # Prevent close-to
            Txn.rekey_to() == Global.zero_address()         # Prevent rekey
        )