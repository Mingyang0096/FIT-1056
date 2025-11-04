# gui/student_pages.py
import streamlit as st
from app.i18n import STR

def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return STR.get(lang, STR["en"]).get(key, key)

def role_display(role: str) -> str:
    mapping = {"Admin": t("role_admin"), "Auditor": t("role_auditor"),
               "Nurse": t("role_nurse"), "Doctor": t("role_doctor"), "Patient": t("role_patient")}
    return mapping.get(role, role)

def mask_name(name: str) -> str:
    if not name: return ""
    return name[0] + "*" * (len(name) - 1)

def patients_page(svc, user):
    st.header(t("patients"))
    role = user["role"]

    # Fetch all patient entries
    all_patients = svc.get_all_patients()
    patient_options = {f"{p['id']} - {p.get('name', 'N/A')}": p for p in all_patients}
    patient_options_list = [t("all_patients")] + list(patient_options.keys())

    # Use a dropdown instead of a search text box
    selected = st.selectbox(t("select_patient_to_view"), patient_options_list, key="pat_select")

    # Show patients based on the selection
    if selected == t("all_patients"):
        rows = all_patients
    elif selected in patient_options:
        rows = [patient_options[selected]]
    else:
        rows = []

    st.session_state["pat_rows"] = rows
    rows = st.session_state.get("pat_rows", [])
    for p in rows[:200]:
        name_disp = p.get("name","")
        if st.session_state.get("lang","en")=="zh" and role not in ("Admin","Auditor"):
            # Privacy masking
            name_disp = mask_name(name_disp)
        dob_disp = p.get("dob","") or "-"
        tags_disp = ", ".join(p.get("tags",[])) or "-"
        with st.container():
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 2])
            c1.markdown(f"**{t('patient_id')}: {p['id']}**")
            c2.markdown(f"**{t('name')}: {name_disp}**")
            c3.markdown(f"{t('dob')}: {dob_disp}")
            c4.markdown(f"{t('tags')}: {tags_disp}")

            with st.expander("操作" if st.session_state.get("lang","en")=="zh" else "Actions"):
                if role in ("Admin","Nurse","Doctor"):
                    # Edit (press Enter to submit)
                    with st.form(f"pat_edit_form_{p['id']}", clear_on_submit=False):
                        newname = st.text_input(f'{t("edit_name")} {p["id"]}', value=p.get("name",""), key="nm_"+p["id"])
                        newdob  = st.text_input(f'{t("edit_dob")} {p["id"]}',  value=p.get("dob",""), key="db_"+p["id"])
                        newtags = st.text_input(f'{t("edit_tags")} {p["id"]}', value=",".join(p.get("tags",[])), key="tg_"+p["id"])
                        do_save = st.form_submit_button(t("save_changes"))
                    if do_save:
                        try:
                            svc.edit_patient(p["id"], name=newname, dob=newdob, tags=[x.strip() for x in newtags.split(",") if x.strip()])
                            st.success(t("saved"))
                        except Exception as e:
                            st.error(str(e))
                    # Self-assign (press Enter to submit)
                    with st.form(f"pat_assign_self_{p['id']}", clear_on_submit=False):
                        do_assign = st.form_submit_button(t("assign_to_me"))
                    if do_assign:
                        try:
                            svc.assign_patient(st.session_state["user"]["username"], p["id"])
                            st.success(t("assigned"))
                        except Exception as e:
                            st.error(str(e))
                elif role == "Admin":
                    with st.form(f"admin_assign_form_{p['id']}", clear_on_submit=False):
                        uname = st.text_input(t("username"), key="ass_"+p["id"])
                        do_assign2 = st.form_submit_button(t("assign"))
                    if do_assign2:
                        try:
                            svc.admin_assign_patient(st.session_state["user"]["username"], uname, p["id"])
                            st.success(t("assigned"))
                        except Exception as e:
                            st.error(str(e))
        st.divider()

def preferences_page(svc, user):
    st.header(t("preferences"))

    # Language and accessibility (press Enter to submit)
    with st.form("prefs_lang_form", clear_on_submit=False):
        st.write(t("language_accessibility"))
        lang  = st.selectbox(t("language"), ["en","zh"],
                             index=["en","zh"].index(st.session_state.get("lang","en")),
                             key="pref_lang_select")
        large = st.checkbox(t("use_large_text"), value=st.session_state.get("large_text", False), key="pref_large_text")
        do_apply = st.form_submit_button(t("apply"))
    if do_apply:
        st.session_state["lang"] = st.session_state.get("pref_lang_select","en")
        st.session_state["large_text"] = st.session_state.get("pref_large_text", False)
        st.success(t("saved"))

    # Patient preferences (press Enter to submit)
    with st.form("prefs_patient_form", clear_on_submit=False):
        pid = st.text_input(t("patient_id"), key="pref_pid")
        diet = st.text_input(t("diet"), key="pref_diet")
        gender = st.text_input(t("preferred_gender"), key="pref_gender")
        vhrs = st.text_input(t("visiting_hours"), key="pref_vhrs")
        do_save_pref = st.form_submit_button(t("save_patient_preference"))
    if do_save_pref:
        try:
            svc.upsert_preferences(pid, diet, gender, vhrs, staff_reader=user["username"], actor=user["username"])
            st.success(t("saved"))
        except Exception as e:
            st.error(str(e))
    pre = svc.get_preferences(pid) if 'pid' in locals() and pid else None
    if pre:
        st.write(pre)
