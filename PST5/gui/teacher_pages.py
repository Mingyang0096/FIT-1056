import streamlit as st

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def _safe_list_teachers(manager):
    try:
        return manager.list_teachers()
    except AttributeError:
        out = []
        for t in getattr(manager, "teachers", []):
            if isinstance(t, dict):
                out.append({"id": t.get("id"), "name": t.get("name", ""), "speciality": t.get("speciality", "")})
            else:
                out.append({"id": getattr(t, "id", None), "name": getattr(t, "name", ""), "speciality": getattr(t, "speciality", "")})
        return out

def show_teacher_page(manager):
    st.header("Teacher Management")

    with st.form("add_teacher"):
        tname = st.text_input("Teacher Name")
        spec  = st.text_input("Speciality")
        if st.form_submit_button("Add Teacher"):
            if tname.strip() and spec.strip():
                try:
                    manager.add_teacher(tname.strip(), spec.strip())
                    st.success("Teacher added")
                    _rerun()
                except Exception as e:
                    st.error(f"Add failed: {e}")
            else:
                st.error("Name and speciality cannot be empty")

    st.markdown("---")
    st.subheader("All Teachers")

    for t in _safe_list_teachers(manager):
        cols = st.columns([1, 3, 2])  # ID | Name | Speciality/Action
        cols[0].write(t["id"])
        cols[1].write(t["name"])
        cols[2].write(t["speciality"])

        if cols[2].button(f"RemoveT-{t['id']}", key=f"rmT_{t['id']}"):
            ok = False
            try:
                ok = manager.remove_teacher(t["id"])
            except Exception as e:
                st.error(f"Removal failed: {e}")
            else:
                if ok:
                    st.success("Removed successfully")
                    _rerun()
                else:
                    st.error("Removal failed")
