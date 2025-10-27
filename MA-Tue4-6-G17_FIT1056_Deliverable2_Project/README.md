CareLog
A lightweight patient interaction and story logging tool for small teams. Built with a Streamlit UI, a service layer, and a JSON repository.

Repository Contents
- Streamlit entry point (main.py) and UI pages under gui/
- Core domain and service logic under app/
- JSON persistence utilities and backup/restore in app/repo_json.py
- Simple i18n dictionary for English and Chinese in app/i18n.py
- Pytest tests under tests/
- Runtime folders data/ and backups/

Features (MVP)
- Record observations: pain level, appetite, notes; supports soft delete
- Maintain patient preferences: diet, preferred consultation gender, visiting hours
- Assign patients to staff; access is enforced per assignment
- Search logs by keyword and generate plain text reports
- Role-based auth: Admin, Nurse, Doctor, Patient, Auditor
- Audit logging for critical actions and a monthly audit view
- Timestamped backups and restore with checksum verification
- Bilingual labels (English/Chinese) and a large-text mode

Architecture
- Presentation: Streamlit pages in gui/ and the main entry point in main.py
- Service: CareLogService in app/service.py
- Persistence: JsonRepo in app/repo_json.py with atomic writes and backups
Data layout
- The live JSON file is created under data/ on first write
- Backups are written to backups/ with a timestamped filename
Important service methods (selection)
- Users and auth: self_register, authenticate, admin_create_user, admin_disable_user
- Patients and access: create_patient, admin_assign_patient, get_assigned_patient_ids, can_access
- Observations: add_visit, add_observation, soft_delete_observation, update_observation
- Preferences and reports: upsert_preferences, get_preferences, text_report
- Search and audit: search_logs(kw, creator, start, end, types, username=None), monthly_audit_view(year, month)

Project Layout (short)
CL_Wed_G17_FIT1056_Deliverable2_Project/
  app/
    i18n.py
    repo_json.py
    service.py
    utils.py
  gui/
    main_dashboard.py
    roster_pages.py
    student_pages.py
  data/            (created at runtime)
  backups/         (created at runtime)
  tests/
    test_service_basic.py
    test_service_more.py
  main.py          (Streamlit entry point)

Getting Started
Prerequisites

- Python 3.10+
- pip

Install and run
pip install streamlit

pip install pytest

python -m streamlit run main.py
The app opens in your browser. On first launch, use Self Register to create an account. If you register an Admin, you can manage assignments and backups from the admin area.

Data and Backups
- Runtime JSON is written to data/
- Backups are written to backups/ and can be restored through the admin area or service APIs

Testing
Run all tests
python -m pytest -q
Coverage highlights

- Registration and authentication, including failure cases
- Admin disable and audit entry visibility
- JSON backup, restore
- Patient creation, assignment, and access checks
- Observation creation and validation errors
- Preferences upsert and retrieval
- Text report generation
- Backup listing and duplicate-assignment prevention
- Basic search call without crashing on empty data
Note
- The search API signature is search_logs(kw, creator, start, end, types, username=None). If you previously used keyword or limit as named parameters, pass positional arguments as shown.

Known Limitations
- Single JSON file storage is not intended for concurrent multi-user writes
- UI error handling is basic
- No external database or hospital system integration
- Session state is simple; reloading the browser may reset some UI state
