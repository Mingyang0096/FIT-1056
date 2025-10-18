import os, json
from cryptography.fernet import Fernet, InvalidToken

class EncryptionManager:
    """File-level encryption helper using Fernet (AES128 + HMAC)."""

    def __init__(self, key_path: str = "secrets/msms.key"):
        self.key_path = key_path
        self.key = self._ensure_key()

    def _ensure_key(self) -> bytes:
        os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return f.read().strip()
        key = Fernet.generate_key()
        with open(self.key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass
        return key

    @property
    def _fernet(self) -> Fernet:
        return Fernet(self.key)

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        return self._fernet.decrypt(token)

    # -------- JSON helpers --------
    def read_json(self, path: str, default=None):
        default = {} if default is None else default
        if not os.path.exists(path):
            return default
        with open(path, "rb") as f:
            raw = f.read()
        # try encrypted
        try:
            dec = self.decrypt(raw)
            return json.loads(dec.decode("utf-8"))
        except InvalidToken:
            # fallback: plaintext (for first-run migration)
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                return default

    def write_json(self, path: str, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = json.dumps(obj, ensure_ascii=False, indent=4).encode("utf-8")
        enc = self.encrypt(payload)
        with open(path, "wb") as f:
            f.write(enc)
