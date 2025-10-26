# CareLog

I built CareLog as a teaching-oriented example for managing clinical notes. It uses a simple layered design: a JSON-backed repository, a service layer with business rules, and a lightweight GUI. The code aims to be readable first, then extensible.

## Goals

- Demonstrate a small but complete end-to-end app: persistence, business logic, and UI.
- Keep the data model explicit and transparent (JSON on disk).
- Make core actions auditable and reversible (audit log and backup/restore).
- Be easy to run on Windows, macOS, and Linux with only the standard library.

## Features

- User management and authentication (Admin, Nurse, Doctor, Auditor, Patient).
- Patient records with preferences and soft delete.
- Access control via assignments (who can read/write which patient).
- Visits, stories (free-text notes), and observations (structured fields).
- Handover notes and a simple text report generator.
- Audit trail with search and monthly view.
- Backups with timestamped files and full restore.
- Basic internationalization with English and Chinese strings.

## Project layout

```
CareLog_structured/
  main.py
  app/
    __init__.py
    service.py        # business logic (CareLogService)
    repo_json.py      # JSON repository (JsonRepo)
    utils.py          # helpers (timestamps, range checks)
    i18n.py           # translations (en, zh)
  gui/
    main_dashboard.py
    roster_pages.py
    student_pages.py
  tests/              # optional: pytest tests (if you added them)
```

## Technology

- Python 3.10+ (standard library only)
- Storage: JSON files on disk
- GUI: lightweight Python UI code
- Tests: pytest (optional but recommended)

## Data model (JSON on disk)

A single JSON file stores all application data. A typical shape looks like this (simplified):

```json
{
  "users": [
    { "username": "alice", "salt": "...", "hash": "...", "role": "Admin", "disabled": false }
  ],
  "patients": [
    {
      "id": "P1",
      "name": "Bob",
      "dob": "1990-01-01",
      "tags": ["diabetes"],
      "deleted": false,
      "preferences": {
        "diet": "",
        "preferred_gender": "",
        "visiting_hours": ""
      }
    }
  ],
  "assignments": [
    { "patient_id": "P1", "username": "nina" }
  ],
  "visits": [
    { "id": "V1", "patient_id": "P1", "start": "2025-01-01", "note": "Routine check", "created_by": "nina" }
  ],
  "stories": [
    { "id": "S1", "patient_id": "P1", "visit_id": "V1", "text": "Doing well.", "deleted": false }
  ],
  "observations": [
    { "id": "O1", "patient_id": "P1", "visit_id": "V1", "pain": 3, "appetite": "Good", "note": "BP 120/80", "deleted": false }
  ],
  "handover": [
    { "patient_id": "P1", "text": "Night shift handover..." }
  ],
  "audit": [
    { "at": "2025-10-26T11:52:59+08:00", "actor": "alice", "action": "create_user", "details": {"username": "nina"} }
  ],
  "next_ids": { "patient": 1, "visit": 1, "story": 1, "observation": 1 }
}
```

Backups are plain copies of the JSON data file created with a timestamped name like:

```
data.json.20251026-115259.bak
```

## Service layer API (quick reference)

All core operations live in `CareLog_structured/app/service.py` as `CareLogService`. Common method signatures:

### Authentication and users
- `self_register(username: str, password: str, role: str) -> dict`
- `authenticate(username: str, password: str) -> dict`
- `admin_create_user(actor: str, username: str, password: str, role: str)`
- `admin_disable_user(actor: str, username: str)`
- `list_users(roles: Optional[List[str]] = None, only_enabled: bool = True) -> List[dict]`

### Patients and access
- `create_patient(name: str, dob: Optional[str], tags: Optional[List[str]]) -> str`
- `edit_patient(pid: str, ...)`
- `soft_delete_patient(pid: str)`
- `assign_patient(username: str, patient_id: str)`
- `admin_assign_patient(actor: str, username: str, patient_id: str)`
- `can_access(username: str, patient_id: str) -> bool`
- `get_assigned_patient_ids(username: str) -> List[str]`
- `upsert_preferences(pid: str, prefs: dict)`

### Visits and notes
- `add_visit(pid: str, start: Optional[str] = None, username: Optional[str] = None) -> str`
- `add_story(username: str, pid: str, vid: str, text: str) -> str`
- `edit_story(sid: str, text: str)`
- `add_observation(username: str, pid: str, vid: str, pain: int, appetite: str, note: str) -> str`
- `edit_observation(oid: str, ...)`
- `soft_delete_story(sid: str)`
- `soft_delete_observation(oid: str)`
- `list_recent_observations(limit: int = 20) -> List[dict]`
- `list_history_observations(pid: str, limit: int = 100) -> List[dict]`
- `create_or_update_handover(pid: str, text: str)`
- `text_report(pid: str) -> str`

### Audit and search
- `monthly_audit_view(year: int, month: int) -> List[dict]`
- `search_logs(query: str) -> List[dict]`
- `search_patients(query: str) -> List[dict]`

### Backup and restore
- `backup_now(actor: str) -> str`
- `list_backups() -> List[str]`
- `restore_from_backup(actor: str, backup_filename: str)`
- `checksum() -> str`

The repository class `JsonRepo` (in `app/repo_json.py`) handles file paths, load/save, backup, restore, and checksum.

## Running the app

### Prerequisites
- Python 3.10 or newer
- No external dependencies required

### Option 1: run the app entry point
From the project root:
```bash
cd CareLog_structured
python main.py
```
`main.py` initializes the repository and service and launches the app. Data will be created under a local data folder. Backups are created under a local backups folder.

### Option 2: programmatic use (no GUI)
```python
from app.repo_json import JsonRepo
from app.service import CareLogService

repo = JsonRepo(data_path="data/data.json", backups_dir="backups")
svc = CareLogService(repo)

svc.self_register("admin", "pw", "Admin")
svc.admin_create_user("admin", "nina", "pw", "Nurse")

pid = svc.create_patient(name="Bob", dob="1990-01-01", tags=["diabetes"])
svc.admin_assign_patient("admin", "nina", pid)

vid = svc.add_visit(pid, start="2025-01-01", username="nina")
sid = svc.add_story("nina", pid, vid, "Patient is doing well.")
oid = svc.add_observation("nina", pid, vid, pain=3, appetite="Good", note="BP 120/80")

report = svc.text_report(pid)
print(report)
```

### Configuration
- To change where data and backups live, pass different paths when creating `JsonRepo`.
- The repository will create directories as needed.

## Internationalization
- `app/i18n.py` contains string dictionaries for English and Chinese.
- To add languages, extend the file with new keys.

## Backups and restore
- `backup_now` writes a complete copy of the JSON data file to `backups/` with a timestamp in the filename.
- `list_backups` returns full paths to available backups.
- `restore_from_backup` accepts a backup path and replaces the live data file, then reloads it into memory.
- `checksum` returns a SHA-256 of the current data file to detect changes.

## Testing
If you use the provided pytest tests:
```bash
python -m pip install -U pytest
pytest -q
```
Typical suites cover:
- `utils.py` for ISO timestamps and range checks.
- `repo_json.py` for load/save, backups, restore, and checksum.
- `service.py` for registration, auth, patient flow, visit/story/observation, backup through the service.

If you previously saw one expected failure around `add_observation` and `check_range`, apply one of the fixes and remove the xfail in tests.

## Access control model
- Admin can create and disable users and assign staff to patients.
- Nurse and Doctor can access patients assigned to them.
- Patient can be self-assigned to their own record.
- Auditor is read-only for audit views and reporting.
- Service methods enforce access checks, and audit entries are recorded on write operations.

## Known limitations
- JSON file storage is not designed for concurrent writes or multi-user servers.
- Field-level authorization is not implemented; access is per patient record.
- Input validation is intentionally minimal for teaching.
- GUI is a simple demonstration and not production-hardened.

## Development notes
- Start by reading `app/service.py` to understand the domain operations and invariants.
- `app/repo_json.py` is the only code that touches the filesystem; swapping in a real database should primarily require changing the repository.
- `gui/` wires the service into a basic UI; keep UI thin and push rules into the service.

## Roadmap ideas
- Replace JSON with SQLite or another DB while keeping the service API stable.
- Enrich validation and error reporting.
- Add role-based capabilities per method rather than only by patient ownership.
- Expand the observation model and reporting, add export to CSV or PDF.
- Improve the GUI and accessibility.

## License and authorship
This codebase is authored for teaching purposes. You are free to read, run, and extend it in coursework settings. For other uses, adapt as needed and keep the attribution in place.
