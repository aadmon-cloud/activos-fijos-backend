from dataclasses import dataclass


@dataclass
class LoginGoogleDTO:
    credencial: str
    nonce: str
