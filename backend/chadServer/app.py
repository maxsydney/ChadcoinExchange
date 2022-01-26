from flask import Flask, render_template, request, jsonify
from backend.services.chadExchangeService import ChadExchangeService
from backend.services.keyPair import KeyPair
from backend.services.priceAPI.coingeckoPriceAPI import CoingeckoPriceAPI
from backend.services.networkInteraction import NetworkInteraction
from backend.contracts.delegatedSignature import DelegatedSignature
from algosdk.future import transaction
from algosdk import encoding
import base64
import json
import yaml
import backend.chadServer.models as models
import os

app = Flask(__name__)

# Check CHAD_EXCHANGE environment variable exists
if "CHAD_EXCHANGE" not in os.environ:
    raise KeyError("Please set CHAD_EXCHANGE enviroment variable")

secrets = os.path.join(os.environ['CHAD_EXCHANGE'], 'backend', 'chadServer', '.secret')

# Get chadcoin config
with open(os.path.join(secrets, "chadToken.yaml"), 'r') as stream:
    try:
        chadConfig=yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# Get KMD config
with open(os.path.join(secrets, "kmd.yaml"), 'r') as stream:
    try:
        kmdConfig=yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# Get algod client
client = NetworkInteraction.createAlgodClient(secrets)

# Get KMD client
kcl = NetworkInteraction.createKMDClient(secrets)

# Get admin pubkey
wallets = kcl.list_wallets()
chadWallet = None
for wallet in wallets:
    if wallet['name'] == 'chadadmin':
        chadWallet = wallet

if not chadWallet:
    raise ValueError("Chadcoin admin wallet could not be found")
handle = kcl.init_wallet_handle(wallet["id"], kmdConfig['walletPassword'])

# TODO: This is unsafe. Do not use in production
adminKeypair = KeyPair(kcl.list_keys(handle)[0], kcl.export_key(handle, kmdConfig['walletPassword'], kcl.list_keys(handle)[0]))

# Create the exchange service
exchange = ChadExchangeService(client=client, admin=adminKeypair, minChadTxThresh=100, chadID=chadConfig['assetID'])

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
 
    # Create delegated signature transaction
    tealContract = DelegatedSignature.algoSig(exchange.escrowAddress, req.algoNoMoreThan, req.chadAmount, chadConfig['assetID'])
    program = base64.decodebytes(client.compile(tealContract)['result'].encode())
    delSig = transaction.LogicSig(program)

    # Return encoded transaction for user to sign
    txEncoded = encoding.msgpack_encode(delSig)

    response = jsonify({"tx": txEncoded})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0')