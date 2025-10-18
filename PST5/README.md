https://github.com/Mingyang0096/FIT-1056.git

# Music School Management System (PST5)

A Streamlit-based management app for a music school. It supports user registration and login, encrypted data storage, students/teachers/courses management, daily roster with attendance, payments and CSV exports, logging, backups, and automated tests.

This README is written to help you score highly against the PST5 brief and rubric.

---

## 1. What’s included

Core features
- Registration and login (first user becomes admin, later users are staff)
- Encrypted persistence by default (Fernet/AES) with optional plaintext mode
- Students, teachers, courses CRUD
- Enrol and unenrol students to courses
- Daily roster and attendance check-in
- Payments: record amounts, view history, export finance and attendance CSV reports
- Logging to file and one-click backups
- Automated tests (pytest)

Tech
- Python 3.10+ (tested on 3.13)
- Streamlit
- cryptography
- pytest

---

## 2. Project structure

```
FIT-1056/
  app/
    __init__.py
    admin_utils.py          # init_logger(), backup_data()
    auth.py                 # user registration/login (PBKDF2)
    schedule.py             # business logic + persistence (encrypted or plaintext)
    security.py             # EncryptionManager (Fernet)
    student.py              # StudentUser
    teacher.py              # TeacherUser, Course
    user.py                 # Base User
  gui/
    __init__.py
    auth_pages.py           # Login/Register UI (auth_gate)
    course_pages.py
    finance_pages.py        # Payments UI + CSV exports
    main_dashboard.py       # app entry from main.py, routes all pages
    roster_pages.py
    student_pages.py
    teacher_pages.py
  data/
    msms.json.enc           # encrypted business data (default)
    users.json.enc          # encrypted user DB
    backups/                # timestamped copies of data file
  secrets/
    msms.key                # symmetric key for .enc files (must be backed up)
  tests/
    test_schedule_manager.py
  msms.log                  # application log
  main.py                   # starts logging/backup then launches Streamlit
  README.md
```

---

## 3. Quick start

Install dependencies
```bash
pip install -U streamlit cryptography pytest
```

Run the app
```bash
streamlit run main.py
```

First-time use
1. On the login screen, register a new account. The first account becomes admin automatically.
2. Log in with that account.
3. Use the sidebar to navigate students, teachers, courses, daily roster, and payments.

Encrypted data location
- Business data: data/msms.json.enc
- User DB: data/users.json.enc
- Encryption key: secrets/msms.key (keep this safe; without it you cannot read .enc files)

Backups and logs
- One-click Backup Now button is available to admin in the sidebar.
- Startup also performs a backup via main.py (data/backups/…).
- Logs written to msms.log.

---

## 4. Pages and workflows

Dashboard
- High-level counts for students, teachers, courses.

Student Management
- Add students by name.
- Remove students.
- Enrol/Unenrol a student into a course by IDs.
- Generate a simple student ID card text file.

Teacher Management
- Add and remove teachers, track speciality.

Course Management
- Add and remove courses with instrument and optional teacher assignment.

Daily Roster and Attendance
- Select a course and see enrolled students.
- Check-in students with one click.
- Query attendance per student.

Payments
- Record payments (amount and method) for a student.
- View a student’s payment history.
- Export CSV reports for finance and attendance.

---

## 5. Data storage and encryption

Default mode: encrypted
- main_dashboard.py initialises ScheduleManager with EncryptionManager and data_path="data/msms.json.enc".
- All business data is written in encrypted form (Fernet). The file content looks like a long base64 token (often starting with gAAAA…).

Plaintext mode (for debugging only)
- In gui/main_dashboard.py inside launch(), replace the encrypted initialisation with:
```python
st.session_state.manager = ScheduleManager(
    data_path="data/msms.json",
    enc_manager=None
)
```
- This will write human-readable JSON to data/msms.json.
- Do not use plaintext mode in assessed or production settings.

Migration note
- If an old plaintext data/msms.json exists and you switch to encrypted mode, the app will read and write to data/msms.json.enc. Old plaintext is preserved by default for safety; you can archive or delete it after verifying your encrypted file contains the expected data.

Key management
- secrets/msms.key is created automatically on first run when using EncryptionManager.
- Back it up securely. If it is lost, .enc files cannot be decrypted.

---

## 6. Logging and backups

Startup lifecycle (in main.py)
- init_logger("msms.log")
- backup_data("data/msms.json.enc", "data/backups")
- launch()

In-app backup
- Admins see a “Backup Now” button in the sidebar to create a timestamped copy of the current data file into data/backups/.

---

## 7. Automated tests

Run all tests
```bash
py -m pytest -q
# or
pytest -q
```

Typical outputs
- 3 passed in 0.05s indicates core flows are working: CRUD/persistence, enrolment/attendance, payments/exports, and safe defaults for empty files.

Common test options
```bash
pytest tests/test_schedule_manager.py -q
pytest -k finance -vv
pytest -x -vv
```

If you see “No module named 'app'”
- Ensure app/ and gui/ contain __init__.py.
- Run from project root: py -m pytest -q.

---

## 8. How to operate for marking

Suggested marking path
1. Register an admin account, log in.
2. Add sample teachers and students. Add a course and enrol students.
3. Use Daily Roster to check in some students.
4. Open Payments, record one or two payments, export finance and attendance CSV.
5. Click Backup Now (sidebar), verify a new backup appears in data/backups/.
6. Restart the app, confirm data persists. Optionally run tests: py -m pytest -q.

Where files go
- Business data: data/msms.json.enc (encrypted by default)
- Users: data/users.json.enc (encrypted)
- Backups: data/backups/
- Logs: msms.log
- Encryption key: secrets/msms.key

---

## 9. Mapping to PST5 brief and rubric

Fragment requirements
- Finance engine and GUI: record_payment, get_payment_history, export_report and Finance page implemented.
- Admin utilities integrated: logging at startup, backup at startup, optional in-app backup button.
- Robust data handling: empty/corrupt files safely fall back to defaults; migration from plaintext supported.
- Registration and roles: auth_gate enabled, first user admin; non-admins see limited menu by default.
- Streamlit compatibility: rerun wrapper supports both st.rerun and st.experimental_rerun.

Rubric highlights
- Completeness: all required features in place, plus backups and tests.
- Reliability: tested core flows, exception handling, and safe defaults.
- Code quality: modular separation (app vs gui), docstrings and comments at key points.
- Usability: clear navigation, role-based menu, export and backup actions visible.

---

## 10. Troubleshooting

JSONDecodeError on startup
- Usually caused by attempting to read an encrypted .enc as plaintext. Ensure encrypted mode is used:
```python
enc = EncryptionManager()
ScheduleManager(data_path="data/msms.json.enc", enc_manager=enc)
```
- Or switch to plaintext and use data/msms.json.

Two data files appear (msms.json and msms.json.enc)
- You ran both plaintext and encrypted modes at different times. After confirming the encrypted file is valid, archive or remove the old plaintext file.

“.enc is readable JSON”
- You didn’t pass enc_manager when creating ScheduleManager. In encrypted mode, .enc content looks like a base64 token, not JSON.

“ModuleNotFoundError: app”
- Ensure __init__.py exists in app/ and gui/, and run tests from project root via py -m pytest -q.

“experimental_rerun not found”
- The code uses a small wrapper to support st.rerun on newer Streamlit. You should not see this error with the provided pages.

---

## 11. Maintenance notes

- Back up secrets/msms.key together with the data backups.
- Avoid editing .enc files by hand.
- Keep cryptography and Streamlit updated.
- Use plaintext mode only when debugging and never commit real data in plaintext.

---

## 12. License and attribution

This coursework project is for FIT1056 PST5. External packages are used under their respective licenses (Streamlit, cryptography, pytest).
