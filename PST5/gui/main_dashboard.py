
import streamlit as st
from app.schedule import ScheduleManager
from app.security import EncryptionManager
from gui.auth_pages import auth_gate

from app.admin_utils import backup_data

from gui.student_pages import show_student_management_page
from gui.teacher_pages import show_teacher_page
from gui.course_pages import show_course_page
from gui.roster_pages import show_roster_page
from gui.finance_pages import show_finance_page

def _rerun():
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()

def launch():
    st.set_page_config(page_title="MSMS Dashboard", layout="wide")

    if not auth_gate():
        return


    if "manager" not in st.session_state:
        enc = EncryptionManager() 
        st.session_state.manager = ScheduleManager(
            data_path="data/msms.json.enc",
            enc_manager=enc
        )
    manager = st.session_state.manager

    st.sidebar.title("MSMS Navigation")
    user = st.session_state.get("auth_user", {"username": "unknown", "role": "unknown"})
    st.sidebar.write(f"👤 {user['username']} ({user['role']})")


    if user.get("role") == "admin":
        if st.sidebar.button("Backup Now"):
            try:
                path = getattr(manager, "data_path", "data/msms.json.enc")
                ok = backup_data(path, "data/backups")
                st.sidebar.success("Backup success." if ok else "Backup failed.")
            except Exception as e:
                st.sidebar.error(f"Backup error: {e}")

    if st.sidebar.button("Log out"):
        st.session_state.pop("auth_user", None)
        st.session_state.pop("manager", None)
        _rerun()

    if user.get("role") == "admin":
        page = st.sidebar.radio(
            "Go to",
            ["Dashboard", "Student Management", "Teacher Management", "Course Management", "Daily Roster", "Payments"]
        )
    else:
        page = st.sidebar.radio("Go to", ["Daily Roster"])


    if page == "Dashboard":
        st.subheader("📊 System Overview")
        st.write(f"Students: {len(getattr(manager, 'students', []) or [])}")
        st.write(f"Teachers: {len(getattr(manager, 'teachers', []) or [])}")
        st.write(f"Courses: {len(getattr(manager, 'courses',  []) or [])}")

    elif page == "Student Management":
        show_student_management_page(manager)

    elif page == "Teacher Management":
        show_teacher_page(manager)

    elif page == "Course Management":
        show_course_page(manager)

    elif page == "Daily Roster":
        show_roster_page(manager)

    elif page == "Payments":
        show_finance_page(manager)
