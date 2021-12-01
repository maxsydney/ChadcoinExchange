import { Component } from '@angular/core';
import WalletConnect from "@walletconnect/client";
import WalletConnectQRCodeModal from "algorand-walletconnect-qrcode-modal";
import algosdk from 'algosdk';
import { HttpClient } from '@angular/common/http';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
}) 

export class AppComponent {
  title = 'frontend';
  connector: WalletConnect;
  connected = false;
  account: any;
  algoBalance: number = 0;
  chadBalance: number = 0;

  buyChadAlgoAmt = new FormControl(0.0);
  algo2Chad = 10;

  server = "https://mainnet-algorand.api.purestake.io/ps2";
  port = "";
  token = {
    "x-api-key": "Xq0wmBHRay4ou13yYq30e55HYVGWfmBB3qlpBkgT"
  };

  client = new algosdk.Indexer(this.token, this.server, this.port);

  constructor(private http: HttpClient) {
    this.http = http;
  }

  connectWallet() {
    this.connector= new WalletConnect({
      bridge: "https://bridge.walletconnect.org", // Required
      qrcodeModal: WalletConnectQRCodeModal,
    });

    // Check if connection is already established
    if (!this.connector.connected) {
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
      WalletConnectQRCodeModal.close();
    });

    this.connector.on("session_update", (error, payload) => {
      if (error) {
        throw error;
      }

      console.log("Update")
      // TODO: What do we need to do here
    });

    WalletConnectQRCodeModal.open(this.connector.uri, {});
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
    // Request transaction group for the purchase of chadcoin from
    // the chadcoin server
    
  }
}
