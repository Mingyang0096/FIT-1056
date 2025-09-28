import streamlit as st

def show_course_page(manager):
    st.header("Course Management")

    # Add course form
    # Function: allow admin to create a new course with name, instrument, and teacher ID.
    # Why: provides a structured way to add courses into the system.
    with st.form("add_course"):
        cname = st.text_input("Course Name")
        instr = st.text_input("Instrument")
        tid = st.number_input("Teacher ID", min_value=0, step=1)
        if st.form_submit_button("Add Course"):
            if cname.strip() and instr.strip():
                manager.add_course(cname, instr, tid)
                st.success("Course added")
            else:
                # Validation
                # Function: prevent empty values for course name or instrument.
                # Why: ensures data integrity and avoids incomplete course records.
                st.error("Course name and instrument cannot be empty")

    st.markdown("---")
    st.subheader("All Courses")

    # List all courses
    # Function: display all registered courses in a table-like layout.
    # Why: gives admin an overview and allows removal of specific courses.
    for c in manager.list_courses():
        cols = st.columns([1,3,2,2])  # layout: ID, Name, Instrument, Teacher/Action
        cols[0].write(c["id"])
        cols[1].write(c["name"])
        cols[2].write(c["instrument"])
        cols[3].write(f"Teacher {c['teacher_id']}")

        # Remove button for each course
        # Function: delete course by ID.
        # Why: admin may need to remove incorrect or outdated course records.
        # Note: unique key per course ensures no widget conflicts.
        if cols[3].button(f"RemoveC-{c['id']}", key=f"rmC_{c['id']}"):
            if manager.remove_course(c['id']):
                st.success("Removed successfully")
                st.experimental_rerun()  # refresh to update the list
            else:
                st.error("Removal failed")
