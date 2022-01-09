from flask import Flask, render_template, request, jsonify
from backend.services.chadExchangeService import ChadExchangeService
from backend.services.priceAPI.coingeckoPriceAPI import CoingeckoPriceAPI
import json
import backend.chadServer.models as models
import os

app = Flask(__name__)

# Check CHAD_EXCHANGE environment variable exists
if "CHAD_EXCHANGE" not in os.environ:
    raise KeyError("Please set CHAD_EXCHANGE enviroment variable")

secrets = os.path.join(os.environ['CHAD_EXCHANGE'], 'backend', 'chadServer', '.secret')

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
    
    # Get the current algo per chad rate
    api = CoingeckoPriceAPI()
    price = api.requestAlgoPrice()
    print(price.success)
    print(price.price)
 
    # Create txs

    # Create atomic group

    # Return atomic group for user to sign

    response = jsonify({"test": 42})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0')