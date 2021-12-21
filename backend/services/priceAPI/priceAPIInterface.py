from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PriceReturn:
    
    price: float
    success: bool


class PriceAPIInterface(ABC):
    """
    Interface for an object that requests the algo price from a remote API
    """

    @abstractmethod
    def requestAlgoPrice(self) -> PriceReturn:
        """
        Request the price of algo in NZD
        """
        pass