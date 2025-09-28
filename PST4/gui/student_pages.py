import streamlit as st

def show_student_management_page(manager):
    st.header("Student Management")

    # Registration form (unique keys prefixed with student_)
    # Function: allow admin to register a new student, optionally with an initial course.
    # Why: provides a structured way to add students; unique keys prevent widget conflicts.
    with st.form(key="student_register_form"):
        name = st.text_input("Student Name", key="student_register_name")
        course = st.number_input("Initial Course ID (optional)", min_value=0, step=1, key="student_register_course")
        submitted = st.form_submit_button("Register", key="student_register_submit")
        if submitted:
            if not name.strip():
                st.error("Name cannot be empty")
            else:
                # Only add initial course if > 0
                # Function: avoid invalid course IDs.
                # Why: ensures only valid course IDs are stored.
                initial = [int(course)] if course and int(course) > 0 else []
                manager.add_student(name, initial)
                st.success(f"Registered: {name}")
                st.experimental_rerun()  # refresh to show updated list

    st.markdown("---")

    # List all students with unique button keys per row
    # Function: display all registered students in a table-like format.
    # Why: gives admin an overview and allows removal of specific students.
    st.subheader("All Students")
    students = manager.list_students()
    if students:
        for s in students:
            sid = s["id"]
            cols = st.columns([1,3,2,2])  # layout: ID, Name, Courses, Action
            cols[0].write(sid)
            cols[1].write(s["name"])
            cols[2].write(f"{s['courses']} course(s)")
            # Remove button for each student
            # Function: delete student by ID.
            # Why: admin may need to remove incorrect or outdated records.
            if cols[3].button("Remove", key=f"student_remove_{sid}"):
                if manager.remove_student(sid):
                    st.success("Removed successfully")
                    st.experimental_rerun()
                else:
                    st.error("Removal failed")

    st.markdown("---")

    # Individual actions — use unique keys for each widget
    # Function: allow admin to perform actions on a specific student (enrol, unenrol, save card).
    # Why: provides fine-grained control over student-course relationships.
    st.subheader("Student Actions")
    sid = st.number_input("Student ID", min_value=0, step=1, key="student_action_sid")
    cid = st.number_input("Course ID", min_value=0, step=1, key="student_action_cid")

    # Enrol student in a course
    # Function: add student to a course by ID.
    # Why: supports dynamic course assignment after registration.
    if st.button("Enroll student", key="student_btn_enrol"):
        if manager.enrol_student_in_course(sid, cid):
            st.success("Enrolment successful")
            st.experimental_rerun()
        else:
            st.error("Enrolment failed")

    # Unenrol student from a course
    # Function: remove student from a course by ID.
    # Why: allows corrections if a student was enrolled in the wrong course.
    if st.button("Unenroll student", key="student_btn_unenrol"):
        if manager.unenrol_student_from_course(sid, cid):
            st.success("Unenrolment successful")
            st.experimental_rerun()
        else:
            st.error("Unenrolment failed")

    # Save student ID card
    # Function: generate and save a student ID card with enrolled courses.
    # Why: provides a tangible record for the student, useful for verification.
    if st.button("Save ID Card", key="student_btn_save_card"):
        student = manager.find_student_by_id(sid)
        if not student:
            st.error("Invalid Student ID")
        else:
            # Collect course names for display on the card
            names = [manager.find_course_by_id(cc).name for cc in student.enrolled_course_ids if manager.find_course_by_id(cc)]
            try:
                path = student.save_card("cards", enrolled_display=names)
                st.success(f"Card saved to {path}")
            except Exception as e:
                st.error(f"Save failed: {e}")
