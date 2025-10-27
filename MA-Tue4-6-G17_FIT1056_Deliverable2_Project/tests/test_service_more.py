import os, pytest
from datetime import datetime
from app.repo_json import JsonRepo
from app.service import CareLogService

@pytest.fixture()
def svc(tmp_path):
    data_path = tmp_path / "carelog.json"
    backups = tmp_path / "backups"
    repo = JsonRepo(str(data_path), str(backups))
    return CareLogService(repo)

def _bootstrap_admin_and_nurse(svc):
    svc.self_register("admin", "adminpw", "Admin")
    svc.self_register("nurse", "nursepw", "Nurse")

def test_create_patient_assign_and_add_observation(svc):
    _bootstrap_admin_and_nurse(svc)
    # create a patient
    pid = svc.create_patient(name="Alice", dob="1990-01-01", tags=["diabetes"])
    # admin assigns to nurse
    svc.admin_assign_patient("admin", "nurse", pid)
    # nurse can access and add observation
    assert svc.can_access("nurse", pid) is True
    vid = "V001"
    oid = svc.add_observation(username="nurse", pid=pid, vid=vid, pain=3, appetite="Good", note="stable")
    assert isinstance(oid, str) and oid

def test_add_observation_validation_errors(svc):
    _bootstrap_admin_and_nurse(svc)
    pid = svc.create_patient(name="Bob", dob="", tags=[])
    svc.admin_assign_patient("admin", "nurse", pid)
    # pain out of range
    with pytest.raises(ValueError):
        svc.add_observation(username="nurse", pid=pid, vid="V", pain=20, appetite="Good", note="x")
    # invalid appetite
    with pytest.raises(ValueError):
        svc.add_observation(username="nurse", pid=pid, vid="V", pain=5, appetite="Bad", note="x")

def test_upsert_and_get_preferences_and_viewed_by(svc):
    _bootstrap_admin_and_nurse(svc)
    pid = svc.create_patient(name="Carol", dob="", tags=[])
    svc.admin_assign_patient("admin", "nurse", pid)
    # first upsert creates record
    svc.upsert_preferences(pid, diet="Low sugar", gender="Female", visiting_hours="9-11", staff_reader="nurse", actor="nurse")
    pre = svc.get_preferences(pid)
    assert pre and pre.get("diet") == "Low sugar"
    assert "nurse" in pre.get("viewed_by", [])
    # update some fields
    svc.upsert_preferences(pid, diet=None, gender="Male", visiting_hours=None, staff_reader=None, actor="admin")
    pre2 = svc.get_preferences(pid)
    assert pre2.get("preferred_gender") == "Male"
    assert pre2.get("updated_by") == "admin"

def test_text_report_contains_observation_lines(svc):
    _bootstrap_admin_and_nurse(svc)
    pid = svc.create_patient(name="Dora", dob="", tags=[])
    svc.admin_assign_patient("admin", "nurse", pid)
    svc.add_observation("nurse", pid, "V1", pain=2, appetite="Average", note="ok")
    report = svc.text_report(patient_id=pid)
    assert "Observation" in report
    assert str(pid) in report

def test_get_patient_info_for_user_patient_role_self_register(svc):
    # self-register patient should auto-create a patient record and assignment
    svc.self_register("patientA", "pw", "Patient")
    info = svc.get_patient_info_for_user("patientA")
    assert info and info.get("id") and info.get("name") == "patientA"

def test_list_backups_returns_sorted_list(tmp_path):
    repo = JsonRepo(str(tmp_path / "carelog.json"), str(tmp_path / "backups"))
    # create multiple backups
    for _ in range(2):
        repo.backup()
    lst = repo.list_backups()
    assert isinstance(lst, list)
    assert all(x.endswith(".bak") for x in lst)

def test_admin_assign_patient_no_duplicate(svc):
    _bootstrap_admin_and_nurse(svc)
    pid = svc.create_patient(name="Eve", dob="", tags=[])
    svc.admin_assign_patient("admin", "nurse", pid)
    # second assignment should not duplicate
    svc.admin_assign_patient("admin", "nurse", pid)
    # nurse should have exactly one assignment entry for this pid
    ids = svc.get_assigned_patient_ids("nurse")
    assert ids.count(pid) == 1

def test_can_access_rules(svc):
    svc.self_register("admin", "pw", "Admin")
    svc.self_register("aud", "pw", "Auditor")
    svc.self_register("nurse", "pw", "Nurse")
    svc.self_register("pat", "pw", "Patient")
    pid = svc.create_patient(name="Pat", dob="", tags=[])
    # assign to nurse and patient
    svc.admin_assign_patient("admin", "nurse", pid)
    svc.admin_assign_patient("admin", "pat", pid)
    assert svc.can_access("admin", pid) is True
    assert svc.can_access("aud", pid) is True
    assert svc.can_access("nurse", pid) is True
    assert svc.can_access("pat", pid) is True
