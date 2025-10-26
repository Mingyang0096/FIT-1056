
import os, tempfile, pytest
from pathlib import Path
from app.repo_json import JsonRepo
from app.service import CareLogService

def make_service(tmp_path):
    data_path = tmp_path / "data.json"
    backups = tmp_path / "backups"
    repo = JsonRepo(str(data_path), str(backups))
    return CareLogService(repo)

def test_self_register_and_authenticate(tmp_path):
    svc = make_service(tmp_path)
    svc.self_register("admin","pw","Admin")
    info = svc.authenticate("admin","pw")
    assert info["username"] == "admin"
    assert info["role"] == "Admin"

def test_admin_create_user_and_list_users(tmp_path):
    svc = make_service(tmp_path)
    svc.self_register("admin","pw","Admin")
    svc.admin_create_user("admin","nina","pw","Nurse")
    svc.admin_create_user("admin","doc","pw","Doctor")
    users = svc.list_users()
    usernames = {u["username"] for u in users}
    assert {"admin","nina","doc"}.issubset(usernames)

def test_patient_flow_visit_and_story(tmp_path):
    svc = make_service(tmp_path)
    svc.self_register("admin","pw","Admin")
    svc.self_register("nina","pw","Nurse")
    svc.self_register("doc","pw","Doctor")

    pid = svc.create_patient(name="Bob", dob="1990-01-01", tags=["diabetes"])
    # admin assigns staff
    svc.admin_assign_patient("admin","nina", pid)
    svc.admin_assign_patient("admin","doc", pid)

    assert svc.can_access("nina", pid)
    assert svc.can_access("doc", pid)

    # visit + story paths that are callable with current signatures
    vid = svc.add_visit(pid, start="2025-01-01", username="nina")
    sid = svc.add_story("nina", pid, vid, "Patient feels fine")
    assert isinstance(vid, str) and vid
    assert isinstance(sid, str) and sid


def test_add_observation_known_issue(tmp_path):
    svc = make_service(tmp_path)
    svc.self_register("admin","pw","Admin")
    svc.self_register("nina","pw","Nurse")
    pid = svc.create_patient(name="Bob", dob="1990-01-01", tags=[])
    svc.admin_assign_patient("admin","nina", pid)
    vid = svc.add_visit(pid, start=None, username="nina")
    # Expect this to work logically, but current code raises TypeError due to check_range call
    svc.add_observation("nina", pid, vid, pain=3, appetite="Good", note="ok")

def test_backup_and_restore_via_service(tmp_path):
    svc = make_service(tmp_path)
    svc.self_register("admin","pw","Admin")
    pid = svc.create_patient(name="Bob", dob=None, tags=[])
    path = svc.backup_now("admin")
    assert os.path.exists(path)
    backups = svc.list_backups()
    assert any(os.path.basename(b)==os.path.basename(path) for b in backups)
    # mutate state
    pid2 = svc.create_patient(name="Alice", dob=None, tags=[])
    # restore prior backup (removes pid2)
    svc.restore_from_backup("admin", os.path.basename(path))
    # reload state and assert only pid exists
    assert any(p["name"]=="Bob" for p in svc.data.get("patients", []))
    assert not any(p.get("name")=="Alice" for p in svc.data.get("patients", []))
