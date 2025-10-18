import base64, hashlib, hmac, secrets, time
from typing import Optional
from app.security import EncryptionManager

class UserAuth:
    """Simple username/password auth with PBKDF2 hashing and encrypted user DB."""

    def __init__(self, userdb_path: str = "data/users.json.enc", enc_manager: Optional[EncryptionManager] = None):
        self.userdb_path = userdb_path
        self.enc = enc_manager or EncryptionManager()

    # ---- password hashing (stdlib, no extra deps) ----
    @staticmethod
    def _hash_password(password: str, salt: bytes = None, iterations: int = 200_000):
        salt = salt or secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return {
            "salt": base64.b64encode(salt).decode(),
            "hash": base64.b64encode(dk).decode(),
            "iterations": iterations
        }

    @staticmethod
    def _verify_password(password: str, salt_b64: str, hash_b64: str, iterations: int) -> bool:
        salt = base64.b64decode(salt_b64.encode())
        expect = base64.b64decode(hash_b64.encode())
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expect)

    def _load_db(self):
        db = self.enc.read_json(self.userdb_path, default={"users": []})
        return db if isinstance(db, dict) and "users" in db else {"users": []}

    def _save_db(self, db):
        self.enc.write_json(self.userdb_path, db)

    def has_any_user(self) -> bool:
        return len(self._load_db()["users"]) > 0

    def register_user(self, username: str, password: str, role: str = None):
        username = (username or "").strip()
        if not username or not password:
            raise ValueError("Username and password are required.")
        db = self._load_db()
        if any(u["username"].lower() == username.lower() for u in db["users"]):
            raise ValueError("Username already exists.")
        role = role or ("admin" if not db["users"] else "staff")
        hp = self._hash_password(password)
        user = {
            "username": username,
            "role": role,
            "password": hp,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        db["users"].append(user)
        self._save_db(db)
        return {"username": username, "role": role}

    def authenticate_user(self, username: str, password: str):
        db = self._load_db()
        u = next((x for x in db["users"] if x["username"].lower() == (username or "").strip().lower()), None)
        if not u: return None
        p = u["password"]
        ok = self._verify_password(password, p["salt"], p["hash"], p["iterations"])
        return {"username": u["username"], "role": u["role"]} if ok else None
