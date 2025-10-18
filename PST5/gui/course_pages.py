import streamlit as st

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def _safe_list_courses(manager):
    """Prefer manager.list_courses(); fallback to build from objects."""
    try:
        return manager.list_courses()
    except AttributeError:
        out = []
        for c in getattr(manager, "courses", []):
            if isinstance(c, dict):
                out.append({
                    "id": c.get("id"),
                    "name": c.get("name", ""),
                    "instrument": c.get("instrument", ""),
                    "teacher_id": c.get("teacher_id"),
                })
            else:
                out.append({
                    "id": getattr(c, "id", None),
                    "name": getattr(c, "name", ""),
                    "instrument": getattr(c, "instrument", ""),
                    "teacher_id": getattr(c, "teacher_id", None),
                })
        return out

def show_course_page(manager):
    st.header("Course Management")

    # Add course
    with st.form("add_course"):
        cname = st.text_input("Course Name")
        instr = st.text_input("Instrument")
        tid   = st.text_input("Teacher ID (optional)")
        if st.form_submit_button("Add Course"):
            if cname.strip() and instr.strip():
                teacher_id = None
                if str(tid).strip():
                    try:
                        teacher_id = int(tid)
                        if teacher_id <= 0:
                            teacher_id = None
                    except ValueError:
                        teacher_id = None
                manager.add_course(cname.strip(), instr.strip(), teacher_id)
                st.success("Course added")
                _rerun()
            else:
                st.error("Course name and instrument cannot be empty")

    st.markdown("---")
    st.subheader("All Courses")

    for c in _safe_list_courses(manager):
        cols = st.columns([1, 3, 2, 2])  # ID | Name | Instrument | Teacher/Action
        cols[0].write(c["id"])
        cols[1].write(c["name"])
        cols[2].write(c["instrument"])
        cols[3].write(f"Teacher {c['teacher_id']}" if c["teacher_id"] is not None else "No teacher")

        if cols[3].button(f"RemoveC-{c['id']}", key=f"rmC_{c['id']}"):
            ok = False
            try:
                ok = manager.remove_course(c["id"])
            except Exception as e:
                st.error(f"Removal failed: {e}")
            else:
                if ok:
                    st.success("Removed successfully")
                    _rerun()
                else:
                    st.error("Removal failed")
