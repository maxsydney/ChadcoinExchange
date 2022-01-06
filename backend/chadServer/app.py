from flask import Flask, render_template, request, jsonify
from backend.services.chadExchangeService import ChadExchangeService
from backend.services.priceAPI.coingeckoPriceAPI import CoingeckoPriceAPI
import json
import backend.chadServer.models as models

app = Flask(__name__)

# Create the exchange service
# exchange = ChadExchangeService

@app.route("/")
def hello_world():
    return render_template('index.html')

@app.route("/getPrice", methods=["GET"])
def getPrice():
    """
    Returns the current algo price in NZD
    """
    api = CoingeckoPriceAPI()
    priceData = api.requestAlgoPrice()
    print(priceData.price)
    schema = models.PriceReturnSchema()
    res = jsonify(schema.dumps(priceData))
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res

@app.route("/createBuyChadTx", methods=["POST"])
def handleBuyChadTx():
    """
    Create buy chad transaction
    """
    print(request)
    schema = models.BuyChadRequestSchema()
    req = schema.load(json.loads(request.data))
    
    api = CoingeckoPriceAPI()
    price = api.requestAlgoPrice()
    print(price.success)
    print(price.price)

    response = jsonify({"test": 42})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0')