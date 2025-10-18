import streamlit as st

def _safe_list_courses(manager):
    try:
        return manager.list_courses()
    except AttributeError:
        out = []
        for c in getattr(manager, "courses", []):
            if isinstance(c, dict):
                out.append({"id": c.get("id"), "name": c.get("name", "")})
            else:
                out.append({"id": getattr(c, "id", None), "name": getattr(c, "name", "")})
        return out

def show_roster_page(manager):
    st.header("Daily Roster & Attendance")

    courses = _safe_list_courses(manager)
    if not courses:
        st.info("No courses available. Add courses first.")
        return

    course_ids = [c["id"] for c in courses]
    def _fmt(cid):
        c = manager.find_course_by_id(cid)
        return f"{cid} - {c.name if c else 'Unknown'}"

    cid = st.selectbox("Select course", course_ids, format_func=_fmt, key="roster_select_course")

    if st.button("Show enrolled students", key="roster_show_students"):
        cobj = manager.find_course_by_id(cid)
        if not cobj:
            st.error("Selected course not found")
        else:
            students = [manager.find_student_by_id(sid) for sid in getattr(cobj, "enrolled_student_ids", [])]
            if not students:
                st.info("No students enrolled in this course")
            for s in students:
                if not s: 
                    continue
                st.write(f"{s.id}: {s.name}")
                if st.button("Check-in", key=f"roster_chk_{s.id}_{cid}"):
                    if manager.check_in(s.id, cid):
                        st.success("Checked in")
                    else:
                        st.error("Check-in failed")

    st.markdown("---")

    q_sid = st.number_input("Student ID (report)", min_value=0, step=1, key="attendance_q_sid")

    if st.button("Show student attendance", key="btn_show_attendance"):
        recs = manager.get_attendance_by_student(q_sid)
        if recs:
            for r in recs:
                st.write(r)
        else:
            st.info("No records")
