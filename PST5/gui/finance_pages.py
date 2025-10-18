import streamlit as st
import pandas as pd

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def show_finance_page(manager):
    """Finance UI: record payments, view history, export CSV reports."""
    st.header("Finance & Payments")

    # --- Section 1: Record a Payment ---
    st.subheader("Record New Payment")
    with st.form("payment_form"):
        student_list = {s.name: s.id for s in manager.students}
        if not student_list:
            st.info("No students found. Please create students first.")
        selected_name = st.selectbox("Select Student", list(student_list.keys()) or ["(no students)"])
        amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        method = st.text_input("Method (e.g., Cash, Card, Transfer)")
        submitted = st.form_submit_button("Record Payment")
        if submitted:
            if selected_name in student_list:
                sid = student_list[selected_name]
                try:
                    manager.record_payment(sid, amount, method or "Unknown")
                    st.success(f"Payment of {amount:.2f} for {selected_name} recorded.")
                    _rerun()
                except Exception as e:
                    st.error(str(e))
            else:
                st.error("Invalid student selection.")

    st.divider()

    # --- Section 2: View Payment History ---
    st.subheader("View Student Payment History")
    student_list = {s.name: s.id for s in manager.students}
    if student_list:
        hist_name = st.selectbox("Student", list(student_list.keys()), key="hist_student")
        sid = student_list[hist_name]
        history = manager.get_payment_history(sid)
        if history:
            df = pd.DataFrame(history)
            st.dataframe(df)
        else:
            st.info("This student has no payment history.")
    else:
        st.info("No students found.")

    st.divider()

    # --- Section 3: Export Reports ---
    st.subheader("Export Reports (CSV)")
    col1, col2 = st.columns(2)
    with col1:
        out_fin = st.text_input("Finance CSV path", value="finance_report.csv", key="out_fin")
        if st.button("Export Finance Report"):
            try:
                manager.export_report("finance", out_fin)
                st.success(f"Exported to {out_fin}")
            except Exception as e:
                st.error(str(e))
    with col2:
        out_att = st.text_input("Attendance CSV path", value="attendance_report.csv", key="out_att")
        if st.button("Export Attendance Report"):
            try:
                manager.export_report("attendance", out_att)
                st.success(f"Exported to {out_att}")
            except Exception as e:
                st.error(str(e))
