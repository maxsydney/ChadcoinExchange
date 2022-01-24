import { Component, OnInit } from '@angular/core';
import { interval } from 'rxjs';
import WalletConnect from "@walletconnect/client";
import QRCodeModal from "algorand-walletconnect-qrcode-modal";
import algosdk from 'algosdk';
import { HttpClient } from '@angular/common/http';
import { FormControl } from '@angular/forms';
import { BuyChadRequest, PriceReturn } from './Models/models'

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})

export class AppComponent implements OnInit {
  title = 'frontend';
  connector: WalletConnect;
  connected = false;
  account: any;
  algoBalance: number = 0;
  chadBalance: number = 0;

  buyChadAmt = new FormControl(0.0);
  algoPerChad = 0;

  // TODO: Move this to server side
  server = "https://mainnet-algorand.api.purestake.io/ps2";
  port = "";
  token = {
    "x-api-key": "Xq0wmBHRay4ou13yYq30e55HYVGWfmBB3qlpBkgT"
  };

  client = new algosdk.Indexer(this.token, this.server, this.port);

  constructor(private http: HttpClient) {
    this.http = http;
  }

  ngOnInit() {
    // Get the current algo price in NZD every 30 seconds
    const obs$ = interval(1000);
    obs$.subscribe((res) => {
      this.getAlgoPrice();
    })
  }

  connectWallet() {
    this.connector = new WalletConnect({
      bridge: "https://bridge.walletconnect.org", // Required
      qrcodeModal: QRCodeModal,
    });

    QRCodeModal.open(this.connector.uri, () => { });

    // Check if connection is already established
    if (!this.connector.connected) {
      console.log("Conn already established")
      this.connector.createSession();
    }

    // Subscribe to connection events
    this.connector.on("connect", (error, payload) => {
      if (error) {
        throw error;
      }

      // Get user account information
      this.account = payload.params[0].accounts[0];
      console.log(this.account);
      this.connected = this.connector.connected;
      this.getAccInfo(this.account);
      QRCodeModal.close();
    });

    this.connector.on("session_update", (error, payload) => {
      if (error) {
        throw error;
      }

      console.log("Update")
      // TODO: What do we need to do here
    });
  }

  disconnectWallet(): void {
    this.connector.killSession();
    this.connected = false;
  }

  printShortAddress(addr: string) {
    return addr.slice(0, 10) + '...';
  }

  async getAccInfo(addr: string) {
    // Get acc info
    let info = (await this.client.lookupAccountByID(addr).do());

    // Get Algo balance
    this.algoBalance = info['amount'] * 1e-6;

    // Get Chad balance
    for (var asset of info["assets"]) {
      if (asset["asset-id"] == 355961778) {
        this.chadBalance = asset["amount"] * 1e-6;
      }
    }
    console.log(`Detected ${this.algoBalance} Algo`);
    console.log(`Detected ${this.chadBalance} Chads`);
  }

  buyChadInitiate() {
    // User must be connected with valid wallet
    if (this.connected == false) {
      console.log("Connect wallet first");
      return;
    }

    // Request transaction group for the purchase of chadcoin from
    // the chadcoin server
    let req = new BuyChadRequest(this.account, this.buyChadAmt.value);

    this.http.post('http://127.0.0.1:5000/createBuyChadTx', req.serialize()).subscribe(response => console.log(response));
  }

  //
  // Get the current algo price in NZD from the chad server
  //
  getAlgoPrice() {
    console.log("Getting algo price");
    this.http.get<string>('http://127.0.0.1:5000/getPrice').subscribe(res => {
      // TODO: Use PriceData interface here to parse directly
      this.algoPerChad = JSON.parse(res)["price"] / 100;
    });
  }
}
