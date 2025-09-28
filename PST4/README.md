MSMS Dashboard — README (English, plain text)

Project overview
MSMS Dashboard is a Streamlit-based demonstration/admin interface for a simple music-school management system. This release simplifies permissions by concentrating most management features under a single admin role; students have read-only access to their own info and attendance queries.

Quick start
1. From the project root run:
   streamlit run main.py
2. Open the URL printed by Streamlit (typically http://localhost:8501).

Default credentials (testing only)
- Administrator:
  Username: admin
  Password: admin

Student login
- Username: student name (case-insensitive)
- Password: student ID (numeric)
- Student records are loaded from ScheduleManager (your project data source).

What this release changed (design notes)
- Permission model: simplified. Most CRUD operations (student/teacher/course management, roster) are available only to the admin role. Students can view their personal info and attendance only.
- Login flow: implemented with st.form + st.form_submit_button so that authentication happens in a single script run and sets session_state keys: logged_in, username, role, student_id.
- Streamlit compatibility: removed direct calls to removed API st.experimental_rerun. Where a UI update must be signalled after a write operation, the app now sets a session_state “dummy” key (e.g., st.session_state[_update]) and returns, which is a cross-version compatible way to let Streamlit re-render on the next interaction or refresh.

Files and responsibilities
- main.py
  - App entry point. Calls gui/main_dashboard.launch().
- gui/main_dashboard.py
  - Login form and main dashboard launcher.
  - Contains USERS dict for the demo admin account.
  - Renders role-specific navigation and routes to page modules.
- gui/student_pages.py
  - Student management UI (register, list, enrol/unenrol, save ID card).
  - Uses session_state["_updated"] to signal list refresh after mutations.
- gui/teacher_pages.py
  - Teacher management UI (add, list, remove).
  - Uses session_state["_updated"] to signal updates.
- gui/course_pages.py
  - Course management UI (add, list, remove).
  - Uses session_state["_updated"] to signal updates.
- gui/roster_pages.py
  - Daily roster and attendance UI (select course, show enrolled students, check-in, attendance query).
- app/schedule.py
  - Domain model and ScheduleManager (data loading/saving). This module supplies manager.students, manager.courses, and related methods used by UI pages.

How login works (behavior)
- The login form validates admin (USERS dict) first.
- If not admin, it iterates manager.students and matches username (case-insensitive) to student.name and password to student.id.
- On successful authentication the app sets session_state keys and continues rendering the dashboard for that role in the same run.

Streamlit compatibility and rerun behavior
- st.experimental_rerun and st.experimental_set_query_params are not used.
- After a write operation (add/remove/enrol/unenrol), UI functions set:
    st.session_state["_updated"] = int(time.time())
  and return. A subsequent user interaction or manual refresh will reload pages and show updated data.
- This pattern avoids using removed/experimental APIs and is broadly compatible across Streamlit versions.

Security (explicit, honest)
- The code does NOT implement secure password storage or transport. Specifically:
  - Passwords are not hashed or salted; the admin account is stored in plain text inside the USERS dict.
  - No TLS is configured by the application code; transport security must be handled at deployment (reverse proxy / platform).
  - No real authentication backend (database/identity provider) is used; student data is read from ScheduleManager’s data source.
  - Authorization is coarse: a role string ("admin" / "student") is used; no fine-grained RBAC, policies, or audit logging is implemented.
- If you plan to use this beyond a local demo, you must:
  - Replace plain text credentials with a secure user store (database), store passwords as hashed+salted values (e.g., bcrypt, Argon2), and never hard-code secrets.
  - Use TLS at the server or reverse-proxy level.
  - Implement proper RBAC and audit logging.
  - Validate and sanitize all inputs and handle exceptions robustly.

Developer notes and suggestions
- To add secure admin accounts, move USERS to a persistent store and compare password hashes instead of plain text.
- For immediate refresh behavior without requiring a second interaction, consider adding a small “Refresh” button that toggles a session_state flag, or implement a centralized helper that attempts to set st.query_params when available, falling back to the session_state toggle. Be aware these methods behave differently across Streamlit versions and hosting environments.
- Ensure every interactive widget has a unique key to avoid widget collisions.
- Search the codebase for any remaining uses of st.experimental_rerun and replace them with the session_state pattern shown above.
- Add unit tests for ScheduleManager methods that mutate data and for authentication logic.

Limitations
- Intended for demonstration and development only.
- No user registration flow beyond admin-managed student addition.
- No password reset, account recovery, or email verification.
- No production-grade logging, monitoring, or backup strategy included.

Contact / next steps
- If you want, I can:
  - Generate patches to replace any remaining st.experimental_rerun calls across files.
  - Replace the plain-text admin credentials with a bcrypt-hashed example and show the minimal code changes needed to verify hashed passwords.
  - Add a short deployment note showing how to run the app behind a TLS-terminating proxy (nginx) for local testing.

License
- No license file included. Add a license that fits your needs before distributing.

End of README.