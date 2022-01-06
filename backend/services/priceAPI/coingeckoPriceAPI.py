from backend.services.priceAPI.priceAPIInterface import PriceAPIInterface, PriceReturn
import requests
import time

class CoingeckoPriceAPI(PriceAPIInterface):

    requestPeriod = 10 # [s]
    request = 'https://api.coingecko.com/api/v3/simple/price?ids=algorand&vs_currencies=nzd&include_last_updated_at=true'
    headers = 'accept: application/json'

    def __init__(self):
        self.currPrice = 0
        self.lastUpdated = 0

        # Test that we can reach the API endpoint
        if self.requestAlgoPrice().success == False:
            raise ValueError("CoingeckoAPI was unable to connect")

    def requestAlgoPrice(self) -> PriceReturn:
        """
        Request the price of algo in NZD
        """

        # Check time since last request. If less than requestPeriod, return
        # most recent price
        tnow = time.time()
        if tnow - self.lastUpdated < CoingeckoPriceAPI.requestPeriod:
            return PriceReturn(self.currPrice, True)

        # Otherwise, get a new price
        res = requests.get(CoingeckoPriceAPI.request)

        if res.status_code != requests.codes.OK:
            print(f"Got status code: {res.status_code}")
            return PriceReturn(self.currPrice, False)

        # Decode response
        try:
            resJSON = res.json()["algorand"]
        except:
            print("Failed to decode response")
            return PriceReturn(self.currPrice, False)

        # Set latest update time
        self.lastUpdated = resJSON["last_updated_at"]

        # Return new price
        self.currPrice = resJSON["nzd"]

        return PriceReturn(self.currPrice, True)
