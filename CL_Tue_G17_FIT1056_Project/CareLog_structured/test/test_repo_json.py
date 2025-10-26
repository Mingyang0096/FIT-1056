
import json, os
from pathlib import Path
from app.repo_json import JsonRepo

def make_repo(tmp_path):
    data_path = tmp_path / "data" / "data.json"
    backups = tmp_path / "backups"
    return JsonRepo(str(data_path), str(backups))

def test_load_empty_creates_structure(tmp_path):
    repo = make_repo(tmp_path)
    data = repo.load()
    for key in ["users", "patients", "visits", "audit"]:
        assert key in data
        assert isinstance(data[key], list)

def test_save_and_load_roundtrip(tmp_path):
    repo = make_repo(tmp_path)
    data = repo.load()
    data["users"].append({"username":"u","salt":"s","hash":"h","role":"Admin","disabled":False})
    repo.save(data)
    again = repo.load()
    assert again == data

def test_backup_and_restore(tmp_path):
    repo = make_repo(tmp_path)
    data = repo.load()
    data["patients"].append({"id":"P1","name":"Bob"})
    repo.save(data)

    backup_file = repo.backup()
    assert os.path.exists(backup_file)
    assert os.path.basename(backup_file).endswith(".bak")

    # mutate and then restore
    data2 = repo.load()
    data2["patients"].append({"id":"P2","name":"Alice"})
    repo.save(data2)

    backups = repo.list_backups()
    assert backup_file in backups

    repo.restore(backup_file)  # expects full path
    restored = repo.load()
    assert any(p.get("id")=="P1" for p in restored.get("patients", []))
    assert not any(p.get("id")=="P2" for p in restored.get("patients", []))

def test_checksum_changes_on_save(tmp_path):
    repo = make_repo(tmp_path)
    before = repo.checksum()
    data = repo.load()
    data["audit"].append({"action":"hello"})
    repo.save(data)
    after = repo.checksum()
    assert before != after
