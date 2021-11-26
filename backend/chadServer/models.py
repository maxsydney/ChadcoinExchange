from marshmallow import Schema, fields, post_load
from dataclasses import dataclass
from typing import List

@dataclass
class BuyChadRequest:
    """
    Request to construct a buy chad transaction
    """
    addr: str
    algoAmount: int

class BuyChadRequestSchema(Schema):
    addr = fields.String()
    algoAmount = fields.Integer()

    @post_load
    def createBuyChadRequest(self, data, **kwargs) -> BuyChadRequest:
        return BuyChadRequest(**data)

@dataclass
class BuyChadResponse:
    """
    Response to a BuyChadRequest. Returns a list of transactions that form an
    atomic group. The first two transactions are signed by the chad server. The
    third transaction is to be signed by the user
    """
    txs: List[str]

class BuyChadResponseSchema(Schema):
    txs = fields.List(fields.String())

    @post_load
    def createBuyChadResponse(self, data, **kwargs) -> BuyChadResponse:
        return BuyChadResponse(**data)

@dataclass
class SubmitBuyChadTx:
    """
    Signed atomic group forming a buy chad transaction
    """
    txs: List(str)

class SubmitBuyChadTxSchema(Schema):
    txs = fields.List(fields.String())

    @post_load
    def createSubmitChadTx(self, data, **kwargs) -> SubmitBuyChadTx:
        return SubmitBuyChadTx(**data)

