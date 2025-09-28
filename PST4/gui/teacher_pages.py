import streamlit as st

def show_teacher_page(manager):
    st.header("Teacher Management")

    # Add teacher form
    # Function: allow admin to register a new teacher with name and speciality.
    # Why: provides a structured way to add teachers into the system.
    with st.form("add_teacher"):
        tname = st.text_input("Teacher Name")
        spec = st.text_input("Speciality")
        if st.form_submit_button("Add Teacher"):
            if tname.strip() and spec.strip():
                manager.add_teacher(tname, spec)
                st.success("Teacher added")
            else:
                # Validation
                # Function: prevent empty values from being submitted.
                # Why: ensures data integrity for teacher records.
                st.error("Name and speciality cannot be empty")

    st.markdown("---")
    st.subheader("All Teachers")

    # List all teachers
    # Function: display all registered teachers in a table-like layout.
    # Why: gives admin an overview and allows removal of specific teachers.
    for t in manager.list_teachers():
        cols = st.columns([1,3,2])  # layout: ID, Name, Speciality/Action
        cols[0].write(t["id"])
        cols[1].write(t["name"])
        cols[2].write(t["speciality"])

        # Remove button for each teacher
        # Function: delete teacher by ID.
        # Why: admin may need to remove incorrect or outdated teacher records.
        if cols[2].button(f"RemoveT-{t['id']}", key=f"rmT_{t['id']}"):
            if manager.remove_teacher(t['id']):
                st.success("Removed successfully")
                st.experimental_rerun()  # refresh to update the list
            else:
                st.error("Removal failed")
