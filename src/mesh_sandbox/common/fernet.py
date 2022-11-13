import json
from typing import cast

from cryptography.fernet import Fernet


class FernetHelper:
    def __init__(self):
        self._encoder = Fernet(Fernet.generate_key())

    def encode_dict(self, data: dict, encoding: str = "utf-8") -> str:
        return cast(str, self._encoder.encrypt(json.dumps(data).encode(encoding=encoding)).decode())

    def decode_dict(self, data: str, encoding: str = "utf-8") -> dict:
        json_str = self._encoder.decrypt(data.encode(encoding=encoding)).decode()
        return cast(dict, json.loads(json_str))
