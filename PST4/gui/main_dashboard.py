import streamlit as st
from app.schedule import ScheduleManager
from gui.student_pages import show_student_management_page
from gui.roster_pages import show_roster_page
from gui.teacher_pages import show_teacher_page
from gui.course_pages import show_course_page

# Built-in admin account (for demonstration only).
# Function: provide a default administrator login.
# Why: makes it possible to test the system even if no student/teacher data exists yet.
USERS = {
    "admin": {"password": "admin", "role": "admin"}
}


def login(manager):
    """
    Function: Render the login form and handle authentication.
    Why: Before accessing the system, both students and admins must log in.
         Using st.form + st.form_submit_button ensures the login is processed
         in one run cycle, without forcing a rerun.
    """
    st.title("🎓 MSMS Dashboard - Login")
    st.write("Below just for test\n1. Username: admin    Password: admin    Role: Manager\n2. Username: Mark    Password: 7    Role: Student")

    with st.form(key="login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password (admin or student ID)", type="password", key="login_password")
        submitted = st.form_submit_button("Login", use_container_width=True, key="login_submit")

    if not submitted:
        return  # Function: do nothing until the form is submitted.
                # Why: prevents premature validation before the user clicks Login.

    # Admin authentication
    # Function: check if the username/password matches the built-in admin.
    # Why: allow administrator to log in with fixed credentials.
    if username in USERS and USERS[username]["password"] == password:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.session_state["role"] = USERS[username]["role"]
        st.success(f"Welcome {username} (admin)")
        return

    # Student authentication
    # Function: match by student name (case-insensitive) and student ID as password.
    # Why: ensures students can log in with their own identity without needing a separate account table.
    matched = None
    for s in manager.students:
        sname = getattr(s, "name", None) if not isinstance(s, dict) else s.get("name")
        sid = getattr(s, "id", None) if not isinstance(s, dict) else (s.get("id") or s.get("user_id"))
        if sname is None or sid is None:
            continue
        if username.strip().lower() == str(sname).strip().lower() and str(password) == str(sid):
            matched = s
            break

    if matched:
        st.session_state["logged_in"] = True
        st.session_state["username"] = getattr(matched, "name", matched.get("name") if isinstance(matched, dict) else None)
        st.session_state["role"] = "student"
        st.session_state["student_id"] = getattr(matched, "id", matched.get("id") if isinstance(matched, dict) else None)
        st.success(f"Welcome {st.session_state['username']} (student)")
        return

    # Function: show error if neither admin nor student credentials match.
    # Why: prevents unauthorized access.
    st.error("Invalid username or password. For students: use name (case-insensitive) and numeric ID as password.")


def logout():
    """
    Function: Clear all login-related session_state keys.
    Why: ensures that after logout, the system forgets the user identity
         and forces a new login next time.
    """
    for key in ["logged_in", "username", "role", "student_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.info("Logged out. Please log in again.")


def main_dashboard(manager):
    """
    Function: Render the main dashboard after login.
    Why: show different menus and pages depending on whether the user is a student or an admin.
    """
    st.sidebar.title("Navigation")
    role = st.session_state.get("role")

    # Role-based menu
    # Function: students only see their info and attendance; admins see full management options.
    # Why: enforce permission separation so students cannot access admin functions.
    if role == "student":
        choice = st.sidebar.radio("Menu", ["Student Info", "Attendance Query"], key="nav_student")
    elif role == "admin":
        choice = st.sidebar.radio(
            "Menu",
            ["Dashboard", "Student Management", "Teacher Management", "Course Management", "Daily Roster"],
            key="nav_admin"
        )
    else:
        st.error("Unknown role")
        return

    # Logout button
    # Function: allow user to log out anytime.
    # Why: important for switching accounts or ending a session securely.
    if st.sidebar.button("Logout", key="btn_logout"):
        logout()
        return  # Stop rendering now; next run will show login page.

    # Page routing
    # Function: load the correct page based on role and menu choice.
    # Why: ensures each role only sees the pages they are allowed to.
    if role == "student":
        if choice == "Student Info":
            st.subheader("📘 Student Info Page")
            sid = st.session_state.get("student_id")
            student = manager.find_student_by_id(sid) if sid else None
            if student:
                sid_val = getattr(student, "id", None) or (student.get("id") if isinstance(student, dict) else None)
                name_val = getattr(student, "name", None) or (student.get("name") if isinstance(student, dict) else None)
                st.write(f"ID: {sid_val}")
                st.write(f"Name: {name_val}")
                st.write("Enrolled courses:")
                enrolled = getattr(student, "enrolled_course_ids", None) or (student.get("enrolled_course_ids", []) if isinstance(student, dict) else [])
                for cid in enrolled:
                    c = manager.find_course_by_id(cid)
                    st.write(f"- {cid}: {c.name if c else 'Unknown'}")
            else:
                st.info("Student data not found.")
        elif choice == "Attendance Query":
            st.subheader("📝 Attendance Query Page")
            sid = st.session_state.get("student_id")
            if sid:
                recs = manager.get_attendance_by_student(sid)
                if recs:
                    for r in recs:
                        st.write(r)
                else:
                    st.info("No attendance records.")
            else:
                st.info("No student logged in.")
    elif role == "admin":
        if choice == "Dashboard":
            st.subheader("📊 System Overview")
            students_count = len(manager.students) if manager.students is not None else 0
            teachers_count = len(getattr(manager, "teachers", []))
            courses_count = len(getattr(manager, "courses", []))
            st.write(f"Students: {students_count}")
            st.write(f"Teachers: {teachers_count}")
            st.write(f"Courses: {courses_count}")
        elif choice == "Student Management":
            show_student_management_page(manager)
        elif choice == "Teacher Management":
            show_teacher_page(manager)
        elif choice == "Course Management":
            show_course_page(manager)
        elif choice == "Daily Roster":
            show_roster_page(manager)


def launch():
    """
    Function: Entry point for the app.
    Why: main.py calls launch(), so this function must handle both login and dashboard rendering.
    """
    st.set_page_config(page_title="MSMS Dashboard", layout="wide")

    # Ensure manager is stored in session_state
    # Function: keep ScheduleManager persistent across reruns.
    # Why: without this, data would reset every time the app reruns.
    if "manager" not in st.session_state:
        st.session_state.manager = ScheduleManager()
    manager = st.session_state.manager

    # Always render login first.
    # Function: if not logged in, show login form.
    # Why: prevents unauthorized access to dashboard.
    if not st.session_state.get("logged_in", False):
        login(manager)
        # If login just succeeded, session_state will contain logged_in=True,
        # so we can continue rendering dashboard in the same run.
        if not st.session_state.get("logged_in", False):
            return  # Still not logged in → stop here and wait for next interaction.

    # Already logged in → render main dashboard.
    main_dashboard(manager)

