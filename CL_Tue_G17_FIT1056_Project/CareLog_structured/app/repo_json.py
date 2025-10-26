# app/repo_json.py
import os, json, hashlib, time, shutil
from typing import Dict, Any

class JsonRepo:
    def __init__(self, data_path: str, backups_dir: str):
        self.data_path = data_path
        self.backups_dir = backups_dir
        os.makedirs(os.path.dirname(self.data_path) or ".", exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)

    def _empty(self) -> Dict[str, Any]:
        return {
            "users": [],
            "patients": [],
            "visits": [],
            "observations": [],
            "stories": [],
            "handover_notes": [],
            "preferences": [],
            "assignments": [],
            "audit": [],
            "next_ids": {"patient":1,"visit":1,"observation":1,"story":1,"handover":1}
        }

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.data_path):
            return self._empty()
        with open(self.data_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return self._empty()

    def save(self, data: Dict[str, Any]):
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def backup(self) -> str:
        os.makedirs(self.backups_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        base = os.path.basename(self.data_path) or "carelog.json"
        dst = os.path.join(self.backups_dir, f"{base}.{ts}.bak")
        if os.path.exists(self.data_path):
            shutil.copy2(self.data_path, dst)
        else:
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(self._empty(), f, ensure_ascii=False, indent=2)
        return dst

    def list_backups(self):
        if not os.path.isdir(self.backups_dir):
            return []
        return sorted([os.path.join(self.backups_dir, x) for x in os.listdir(self.backups_dir) if x.endswith(".bak")])

    def restore(self, backup_file: str):
        if not os.path.exists(backup_file):
            raise FileNotFoundError(backup_file)
        shutil.copy2(backup_file, self.data_path)

    def checksum(self) -> str:
        if not os.path.exists(self.data_path):
            return ""
        h = hashlib.sha256()
        with open(self.data_path, "rb") as f:
            while True:
                b = f.read(65536)
                if not b: break
                h.update(b)
        return h.hexdigest()