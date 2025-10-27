import os, json, re
import pytest
from app.repo_json import JsonRepo
from app.service import CareLogService
from datetime import datetime

@pytest.fixture()
def svc(tmp_path):
    """
    Fresh service instance backed by a temp JSON repo for each test.
    """
    data_path = tmp_path / "carelog.json"
    backups = tmp_path / "backups"
    repo = JsonRepo(str(data_path), str(backups))
    service = CareLogService(repo)
    return service

def test_self_register_and_authenticate_success(svc):
    """
    Register a Nurse and authenticate successfully.
    """
    svc.self_register("nurse1", "pw123", "Nurse")
    u = svc.authenticate("nurse1", "pw123")
    assert u["username"] == "nurse1"
    # role exists and is one of the supported roles
    assert u.get("role") in ("Nurse", "Doctor", "Admin", "Patient", "Auditor")

def test_authenticate_invalid_credentials(svc):
    """
    Wrong username/password should be rejected.
    """
    with pytest.raises(PermissionError):
        svc.authenticate("no_user", "no_pass")

def test_admin_disable_user_audit_and_auth(svc):
    """
    Admin disables a user:
      - authentication of the disabled user should fail
      - action should appear in current month's audit view
    """
    # Prepare admin and normal user
    svc.self_register("admin", "adminpw", "Admin")
    svc.self_register("userA", "passA", "Nurse")

    # Disable userA
    svc.admin_disable_user("admin", "userA", True)

    # Authentication should now fail for userA
    with pytest.raises(PermissionError):
        svc.authenticate("userA", "passA")

    # And an audit record should be visible this month
    now = datetime.now()
    items = svc.monthly_audit_view(now.year, now.month)
    assert any(
        x.get("type") == "audit" and x.get("action") == "disable_user"
        for x in items
    )

def test_repo_backup_and_restore(tmp_path):
    """
    JsonRepo backup() should create a .bak file and restore() should revert data.
    """
    data_path = tmp_path / "carelog.json"
    backups = tmp_path / "backups"
    repo = JsonRepo(str(data_path), str(backups))

    # Write initial data and capture checksum
    data = {"users": [{"username": "u1"}]}
    repo.save(data)
    cs1 = repo.checksum()

    # Make a backup
    bfile = repo.backup()
    assert os.path.exists(bfile)

    # Change data and checksum should differ
    repo.save({"users": [{"username": "u2"}]})
    cs2 = repo.checksum()
    assert cs1 != cs2

    # Restore from backup, checksum returns to original
    repo.restore(bfile)
    assert repo.checksum() == cs1

def test_search_functions_do_not_crash_on_empty_data(svc):
    """
    search_* APIs should return lists and not crash on empty datasets.
    """
    rows = svc.search_patients("any")
    assert isinstance(rows, list)

    logs = svc.search_logs("x", None, None, None, None, None)
    assert isinstance(logs, list)
