import streamlit as st

def show_roster_page(manager):
    st.header("Daily Roster & Attendance")

    # Get all courses from manager
    # Function: retrieve the list of available courses.
    # Why: attendance is course-based, so we must first know which courses exist.
    courses = manager.list_courses()
    if not courses:
        st.info("No courses available. Add courses first.")
        return

    # Build a selectbox for choosing a course
    # Function: allow user to pick one course by ID.
    # Why: attendance operations are tied to a specific course.
    # Note: each widget must have a unique key to avoid conflicts.
    course_ids = [c["id"] for c in courses]
    cid = st.selectbox(
        "Select course",
        course_ids,
        format_func=lambda x: f"{x} - {manager.find_course_by_id(x).name if manager.find_course_by_id(x) else 'Unknown'}",
        key="roster_select_course"
    )

    # Button to show enrolled students
    # Function: once a course is selected, display all students enrolled in it.
    # Why: teachers/admins need to see who is in the class before marking attendance.
    if st.button("Show enrolled students", key="roster_show_students"):
        cobj = manager.find_course_by_id(cid)
        if not cobj:
            st.error("Selected course not found")
        else:
            # Collect student objects by their IDs
            # Function: map enrolled student IDs to actual student records.
            # Why: we need student names/IDs to display and check them in.
            students = [manager.find_student_by_id(sid) for sid in cobj.enrolled_student_ids]
            if not students:
                st.info("No students enrolled in this course")
            for s in students:
                if not s:
                    continue
                st.write(f"{s.id}: {s.name}")
                # Add a check-in button for each student
                # Function: mark attendance for this student in this course.
                # Why: attendance is recorded individually, so each student needs a separate button.
                # Note: key must be unique per student+course to avoid widget clashes.
                if st.button("Check-in", key=f"roster_chk_{s.id}_{cid}"):
                    if manager.check_in(s.id, cid):
                        st.success("Checked in")
                    else:
                        st.error("Check-in failed")

    # Divider for attendance query section
    st.markdown("---")

    # Input for querying attendance by student ID
    # Function: allow user to enter a student ID to see their attendance history.
    # Why: useful for students or admins to review attendance records.
    # Note: widget key ensures uniqueness across the app.
    q_sid = st.number_input("Student ID (report)", min_value=0, step=1, key="attendance_q_sid")

    # Button to trigger attendance query
    # Function: fetch and display attendance records for the given student ID.
    # Why: provides transparency and record-keeping for attendance.
    if st.button("Show student attendance", key="btn_show_attendance"):
        recs = manager.get_attendance_by_student(q_sid)
        if recs:
            for r in recs:
                st.write(r)
        else:
            st.info("No records")

