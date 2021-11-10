from dataclasses import dataclass
from algosdk import mnemonic

@dataclass
class KeyPair:
    """
    Container holding a public/private keypair
    """

    pubKey: str
    privKey: str

    def mnemonic(self) -> str:
        return mnemonic.from_private_key(self.privKey)

