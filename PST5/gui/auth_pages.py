import streamlit as st
from app.auth import UserAuth

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def auth_gate() -> bool:
    """Render login/register until authenticated. Returns True if already authed."""
    if st.session_state.get("auth_user"):
        return True

    st.title("🔐 Sign in to MSMS")

    auth = UserAuth()
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            ok = st.form_submit_button("Login")
            if ok:
                user = auth.authenticate_user(u, p)
                if user:
                    st.session_state["auth_user"] = user
                    st.success(f"Welcome, {user['username']} ({user['role']})")
                    _rerun()
                else:
                    st.error("Invalid username or password.")

    with tab_register:
        st.caption("First account becomes **admin** automatically; subsequent accounts are **staff**.")
        with st.form("register_form"):
            u2 = st.text_input("New username")
            p1 = st.text_input("Password", type="password")
            p2 = st.text_input("Confirm password", type="password")
            reg = st.form_submit_button("Create account")
            if reg:
                if p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        created = auth.register_user(u2, p1)
                        st.success(f"User {created['username']} created ({created['role']}). Please login.")
                    except Exception as e:
                        st.error(str(e))

    st.stop()
