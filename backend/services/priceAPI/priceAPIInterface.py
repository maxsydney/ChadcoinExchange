from abc import ABC, abstractmethod
from dataclasses import dataclass
from backend.chadServer.models import PriceReturn

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