import streamlit as st

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def _safe_list_students(manager):
    try:
        return manager.list_students()
    except AttributeError:
        out = []
        for s in getattr(manager, "students", []):
            if isinstance(s, dict):
                sid = s.get("id") or s.get("user_id")
                name = s.get("name", "")
                enrolled = s.get("enrolled_course_ids", []) or []
            else:
                sid = getattr(s, "id", getattr(s, "user_id", None))
                name = getattr(s, "name", "")
                enrolled = getattr(s, "enrolled_course_ids", []) or []
            out.append({"id": sid, "name": name, "courses": len(enrolled)})
        return out

def _save_card_fallback(student, folder, enrolled_display):
    """Fallback when student object has no save_card (rare)."""
    import os
    from datetime import datetime
    os.makedirs(folder, exist_ok=True)
    sid = student.get("id") or student.get("user_id")
    name = student.get("name", "")
    path = os.path.join(folder, f"student_{sid}_card.txt")
    lines = [
        "MSMS Student ID Card",
        f"ID: {sid}",
        f"Name: {name}",
        "Courses: " + (", ".join(enrolled_display) if enrolled_display else "-"),
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path

def show_student_management_page(manager):
    st.header("Student Management")

    # register
    with st.form(key="student_register_form"):
        name = st.text_input("Student Name", key="student_register_name")
        course = st.number_input("Initial Course ID (optional)", min_value=0, step=1, key="student_register_course")
        submitted = st.form_submit_button("Register", key="student_register_submit")
        if submitted:
            if not name.strip():
                st.error("Name cannot be empty")
            else:
                initial = [int(course)] if course and int(course) > 0 else []
                manager.add_student(name.strip(), initial)
                st.success(f"Registered: {name.strip()}")
                _rerun()

    st.markdown("---")

    st.subheader("All Students")
    students = _safe_list_students(manager)
    if students:
        for s in students:
            sid = s["id"]
            cols = st.columns([1, 3, 2, 2])  # ID | Name | Courses | Action
            cols[0].write(sid)
            cols[1].write(s["name"])
            cols[2].write(f"{s['courses']} course(s)")
            if cols[3].button("Remove", key=f"student_remove_{sid}"):
                ok = False
                try:
                    ok = manager.remove_student(sid)
                except Exception as e:
                    st.error(f"Removal failed: {e}")
                else:
                    if ok:
                        st.success("Removed successfully")
                        _rerun()
                    else:
                        st.error("Removal failed")

    st.markdown("---")

    st.subheader("Student Actions")
    sid = st.number_input("Student ID", min_value=0, step=1, key="student_action_sid")
    cid = st.number_input("Course ID",  min_value=0, step=1, key="student_action_cid")

    if st.button("Enroll student", key="student_btn_enrol"):
        if manager.enrol_student_in_course(sid, cid):
            st.success("Enrolment successful")
            _rerun()
        else:
            st.error("Enrolment failed")

    if st.button("Unenroll student", key="student_btn_unenrol"):
        if manager.unenrol_student_from_course(sid, cid):
            st.success("Unenrolment successful")
            _rerun()
        else:
            st.error("Unenrolment failed")

    if st.button("Save ID Card", key="student_btn_save_card"):
        student = manager.find_student_by_id(sid)
        if not student:
            st.error("Invalid Student ID")
        else:
            enrolled_ids = []
            if isinstance(student, dict):
                enrolled_ids = student.get("enrolled_course_ids", []) or []
            else:
                enrolled_ids = getattr(student, "enrolled_course_ids", []) or []
            names = []
            for cc in enrolled_ids:
                c = manager.find_course_by_id(cc)
                if c:
                    names.append(getattr(c, "name", "") if not isinstance(c, dict) else c.get("name", ""))

            try:
                if hasattr(student, "save_card"):
                    path = student.save_card("cards", enrolled_display=names)
                else:
                    path = _save_card_fallback(student if isinstance(student, dict) else student.__dict__, "cards", names)
                st.success(f"Card saved to {path}")
            except Exception as e:
                st.error(f"Save failed: {e}")
