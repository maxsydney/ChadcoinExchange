import pytest
import os
import yaml
from backend.test.testHelpers import Sandbox, Account, Client, Transaction
from algosdk import wallet

from backend.services.chadExchangeService import createExchangeService, ChadExchangeService

class TestCreateChadExchangeServicde:
    """
    Unit tests for the chad exchange service factory method
    """
    def setup_method(self, method):
        """
        Initialize tests with sandbox running and get test accounts
        """
        Sandbox.command("up", "release")
        Sandbox.command("reset")

        # Create sandbox algod client and create a chadcoin token
        self.client = Client.getClient()
        self.admin, self.user1, self.user2 = Account.getTestAccounts()
        self.chadID = Transaction.createChadToken(client=self.client, owner=self.admin)

        # Write the chadID to test config file
        self.secrets = os.path.join(os.environ['CHAD_EXCHANGE'], 'backend', 'test', 'services', 'testSecrets')
        chadCfg = os.path.join(self.secrets, 'chadToken.yaml')
        with open(chadCfg, 'w') as file:
            yaml.dump({'assetID': self.chadID}, file)

    def teardown_method(self, method):
        Sandbox.command("down")

    def test_successfulCreation(self):
        """
        Check that exchange is successfully created from test config
        """
        # Add chadadmin wallet to wallets managed by KMD
        kcl = Account.getKcl()
        chadWallet = wallet.Wallet('chadadmin', '', kcl)
        chadWallet.generate_key()

        exchange = createExchangeService(self.secrets)

        assert exchange.admin.pubKey == chadWallet.list_keys()[0]
        assert exchange.chadID == self.chadID

        with open(os.path.join(self.secrets, 'config.yaml')) as configFile:
            assert exchange.minChadtxThresh == yaml.safe_load(configFile)['minChadTxThresh']
    
    def test_noChadadminWalletAvailable(self):
        """
        Check that exchange creation fails if the chadadmin wallet is not managed by local
        KMD instance
        """

        # Check logic fails
        with pytest.raises(KeyError):
            createExchangeService(self.secrets)

    def test_noAccountInChadAdminWallet(self):
        """
        Check that exchange creation fails if the local chadadmin wallet does not contain any
        accounts
        """
        # Add chadadmin wallet to wallets managed by KMD
        kcl = Account.getKcl()
        chadWallet = wallet.Wallet('chadadmin', '', kcl)

        # Check logic fails
        with pytest.raises(ValueError):
            createExchangeService(self.secrets)

    def test_severalAccountsInChadAdminWallet(self):
        """
        Check that exchange creation fails if the local chadadmin wallet contains several
        accounts
        """

        # Add chadadmin wallet to wallets managed by KMD
        kcl = Account.getKcl()
        chadWallet = wallet.Wallet('chadadmin', '', kcl)
        chadWallet.generate_key()
        chadWallet.generate_key()   # Create second account managed in wallet

        # Check logic fails
        with pytest.raises(ValueError):
            createExchangeService(self.secrets)
