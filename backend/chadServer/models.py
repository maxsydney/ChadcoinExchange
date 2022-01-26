from marshmallow import Schema, fields, post_load
from dataclasses import dataclass
from typing import List

@dataclass
class BuyChadRequest:
    """
    Request to construct a buy chad transaction
    """
    addr: str
    chadAmount: int
    algoNoMoreThan: int

class BuyChadRequestSchema(Schema):
    addr = fields.String()
    chadAmount = fields.Integer()
    algoNoMoreThan = fields.Integer()

    @post_load
    def createBuyChadRequest(self, data, **kwargs) -> BuyChadRequest:
        return BuyChadRequest(**data)

@dataclass
class BuyChadResponse:
    """
    Response to a BuyChadRequest. Returns an encoded logicSig object representing the delegated
    signature contract for the user to sign
    """
    txs: str

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
    txs: List[str]

class SubmitBuyChadTxSchema(Schema):
    txs = fields.List(fields.String())

    @post_load
    def createSubmitChadTx(self, data, **kwargs) -> SubmitBuyChadTx:
        return SubmitBuyChadTx(**data)

@dataclass
class PriceReturn:
    """
    Algo price in NZD
    """
    
    price: float
    success: bool

class PriceReturnSchema(Schema):
    price = fields.Float()
    success = fields.Boolean()

    @post_load
    def createPriceReturn(self, data, **kwargs) -> PriceReturn:
        return PriceReturn(**data)