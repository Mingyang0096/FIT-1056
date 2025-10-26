# gui/roster_pages.py
import streamlit as st
import datetime
from app.i18n import STR

def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return STR.get(lang, STR["en"]).get(key, key)

def role_display(role: str) -> str:
    mapping = {"Admin": t("role_admin"), "Auditor": t("role_auditor"),
               "Nurse": t("role_nurse"), "Doctor": t("role_doctor"), "Patient": t("role_patient")}
    return mapping.get(role, role)

def observations_page(svc, user):
    st.header(t("observations"))
    role = user["role"]

    # 顶部输入病人ID
    pid = st.text_input(t("patient_id"), key="obs_pid")

    if role in ("Admin","Nurse","Doctor"):
        c1, c2 = st.columns(2)

        # 就诊：创建或使用（回车提交）
        with c1:
            with st.form("obs_visit_form", clear_on_submit=False):
                vid = st.text_input(t("visit_id"), value=st.session_state.get("cur_vid",""), key="obs_vid")
                do_visit = st.form_submit_button(t("create_or_use_visit"))
            if do_visit:
                if not pid:
                    st.error(t("patient_id_required"))
                else:
                    try:
                        v = vid.strip()
                        if not v:
                            vid = svc.add_visit(pid, None, username=user["username"])
                            st.session_state["cur_vid"] = vid
                            st.success(("Created visit " + vid) if st.session_state.get("lang","en")=="en" else ("已创建就诊 "+vid))
                        else:
                            st.session_state["cur_vid"] = v
                            st.success(("Using visit " + v) if st.session_state.get("lang","en")=="en" else ("使用就诊 "+v))
                    except Exception as e:
                        st.error(str(e))

        # 创建观察（回车提交）
        with c2:
            with st.form("obs_create_form", clear_on_submit=True):
                vid = st.text_input(t("visit_id"), value=st.session_state.get("cur_vid",""), key="obs_vid2")
                pain = st.number_input(t("pain"), 0, 10, 0, key="pain")
                appetite = st.selectbox(t("appetite"), ["Good","Average","Poor"], key="appetite")
                note = st.text_input(t("note"), key="note")
                do_create = st.form_submit_button(t("create"))
            if do_create:
                try:
                    if not pid: raise ValueError("patient id required")
                    if not vid: raise ValueError("visit id required")
                    oid = svc.add_observation(
                        user["username"], pid, vid,
                        int(pain), appetite, note
                    )
                    st.success(("Added observation " + oid) if st.session_state.get("lang","en")=="en" else ("已新增观察 " + oid))
                except Exception as e:
                    st.error(str(e))
    else:
        st.info(t("read_only"))

    # 最近记录（编辑表单内回车保存）——默认近90天（FR6）
    st.subheader(t("recent_within_90"))
    for o in svc.list_recent_observations(90, username=user["username"]):
        st.write(o)
        if role in ("Admin","Nurse","Doctor"):
            with st.expander(t("edit_or_delete")):
                with st.form(f"obs_edit_form_{o['id']}", clear_on_submit=False):
                    newpain = st.number_input(t("pain"), 0, 10, o["pain"], key="p_"+o["id"])
                    newapp  = st.selectbox(t("appetite"), ["Good","Average","Poor"],
                                           index=["Good","Average","Poor"].index(o["appetite"]),
                                           key="a_"+o["id"])
                    newnote = st.text_input(t("note"), value=o["note"], key="n_"+o["id"])
                    do_save = st.form_submit_button(t("save_changes"))
                if do_save:
                    try:
                        svc.edit_observation(o["id"], pain=int(newpain), appetite=newapp, note=newnote)
                        st.success(t("saved"))
                    except Exception as e:
                        st.error(str(e))

                with st.form(f"obs_del_form_{o['id']}", clear_on_submit=False):
                    do_del = st.form_submit_button(t("soft_delete"))
                if do_del:
                    svc.soft_delete_observation(o["id"])
                    st.warning(t("soft_delete"))

    # 历史开关（FR6）
    if st.checkbox(t("show_older_history"), key="obs_show_older"):
        for o in svc.list_history_observations(90, username=user["username"]):
            st.write(o)

def stories_page(svc, user):
    st.header(t("stories"))
    role = user["role"]
    if role in ("Admin","Nurse","Doctor"):
        with st.form("story_form", clear_on_submit=True):
            pid = st.text_input(t("patient_id_story"), key="story_pid")
            vid = st.text_input(t("visit_id"), key="story_vid")
            text = st.text_area(t("story_text"), key="story_text")
            do_create = st.form_submit_button(t("create"))
        if do_create:
            try:
                sid = svc.add_story(user["username"], pid, vid, text)
                st.success(("Added story " + sid) if st.session_state.get("lang","en")=="en" else ("已新增叙事 "+sid))
            except Exception as e:
                st.error(str(e))
    else:
        st.info(t("read_only"))

def handover_page(svc, user):
    st.header(t("handover"))
    role = user["role"]

    with st.form("handover_form", clear_on_submit=False):
        pid = st.text_input(t("patient_id_handover"), key="handover_pid")
        current = svc.get_handover(pid) if pid else None
        default_text = (current or {}).get("text","")
        text_area = st.text_area(t("handover_note") if role in ("Admin","Nurse","Doctor")
                                 else t("handover_note")+" ("+t("read_only")+")",
                                 value=default_text, height=200,
                                 disabled=False if role in ("Admin","Nurse","Doctor") else True,
                                 key="handover_text")
        do_save = st.form_submit_button(t("save_handover")) if role in ("Admin","Nurse","Doctor") else False
    if role in ("Admin","Nurse","Doctor") and do_save:
        try:
            hid = svc.create_or_update_handover(user["username"], pid, st.session_state.get("handover_text",""))
            st.success(("Saved handover " + hid) if st.session_state.get("lang","en")=="en" else ("已保存交接班 "+hid))
        except Exception as e:
            st.error(str(e))
    if 'current' in locals() and current:
        st.info(f'{t("last_updated_by")}: {current.get("updated_at","")} / {current.get("created_by","")}')

def search_page(svc, user):
    st.header(t("search"))

    # 历史切换与默认近90天（FR6）
    show_hist = st.checkbox(t("show_history_all"), value=False, key="search_hist_toggle")
    default_start = (datetime.date.today() - datetime.timedelta(days=90))
    default_end = datetime.date.today()

    # 创建者下拉（FR5）
    users = svc.list_users(roles=None, only_enabled=True)
    user_options = [""] + [u["username"] for u in users]

    # 搜索表单（回车提交）
    with st.form("search_form", clear_on_submit=False):
        kw = st.text_input(t("keyword"), key="search_kw")
        creator = st.selectbox(t("created_by_optional"), user_options, index=0, key="search_creator_sel")
        c1, c2 = st.columns(2)
        d_start = c1.date_input(t("start_date"), value=None if show_hist else default_start, key="search_start_date")
        d_end   = c2.date_input(t("end_date"),   value=None if show_hist else default_end,   key="search_end_date")

        # 类型多选（FR5）
        all_types = ["observation","story","handover","preference","visit"]
        if user["role"] in ("Admin","Auditor"):
            all_types.append("audit")
        types = st.multiselect(t("record_types"), all_types, ["observation","story"], key="search_types")

        do_search = st.form_submit_button(t("search_button"))

    if do_search:
        start_str = d_start.isoformat() if d_start else None
        end_str = d_end.isoformat() if d_end else None
        rows = svc.search_logs(kw, (creator or None), start_str, end_str, types or None, username=user["username"])
        st.session_state["search_rows"] = rows
        st.session_state["search_hist_is_on"] = show_hist

    rows = st.session_state.get("search_rows", [])
    # 模式提示（FR6）
    hint = t("mode_history") if st.session_state.get("search_hist_is_on") else t("mode_recent_90")
    st.caption(hint)

    st.write(f"{len(rows)} {t('results_count')}")
    for r in rows[:200]:
        if "highlight" in r and r["highlight"]:
            who = r.get("created_by", r.get("actor",""))
            when = r.get("created_at", r.get("ts",""))
            st.markdown(f'**{r["type"].title()}** | `{who}` | `{when}`  \n{r["highlight"]}')
        else:
            st.write(r)

    # 导出（所见即所得，FR5/FR6 都适用）
    if rows:
        with st.form("search_export_form", clear_on_submit=False):
            do_export = st.form_submit_button(t("export_csv"))
        if do_export:
            csv_text = svc.export_csv(rows)
            st.download_button(t("download_csv"), data=csv_text, file_name="search_results.csv", key="search_download")

def report_page(svc, user):
    st.header(t("report"))
    role = user["role"]
    import datetime as _dt
    if role == "Patient":
        my_pids = svc.get_assigned_patient_ids(user["username"])
        if not my_pids:
            st.warning(t("no_patient_record_linked")); return
        with st.form("report_my_form", clear_on_submit=False):
            pid = st.selectbox(t("your_patient_record"), my_pids, index=0, key="report_patient_pick")
            do_gen = st.form_submit_button(t("generate"))
        if do_gen:
            # 患者视角：默认用近90天可在搜索页查看，患者报告仍按原逻辑
            st.code(svc.text_report(patient_id=pid))
    else:
        mode = st.radio(t("report_mode"), [t("by_patient"), t("by_date")], key="report_mode")
        if mode == t("by_patient"):
            # 历史开关（FR6）：默认近90天
            show_hist = st.checkbox(t("show_history_all"), value=False, key="report_hist_toggle")
            with st.form("report_by_pid_form", clear_on_submit=False):
                pid = st.text_input(t("patient_id"), key="report_pid")
                do_gen1 = st.form_submit_button(t("generate"))
            if do_gen1:
                if show_hist:
                    st.code(svc.text_report(patient_id=pid))
                else:
                    _to = _dt.date.today().isoformat()
                    _from = (_dt.date.today() - _dt.timedelta(days=90)).isoformat()
                    st.code(svc.text_report(patient_id=pid, date_from=_from, date_to=_to))
        else:
            with st.form("report_by_date_form", clear_on_submit=False):
                d = st.date_input(t("by_date"), value=_dt.date.today(), key="report_date")
                do_gen2 = st.form_submit_button(t("generate"))
            if do_gen2:
                dt_iso = _dt.datetime.combine(d, _dt.time(0,0)).astimezone().isoformat()
                st.code(svc.text_report(date_iso=dt_iso))

def auditor_page(svc):
    st.header(t("auditor"))
    with st.form("aud_form", clear_on_submit=False):
        ym = st.text_input(t("ym_label"), value=datetime.date.today().strftime("%Y-%m"), key="aud_ym")
        do_aud = st.form_submit_button("OK")
    if do_aud:
        try:
            y,m = ym.split("-")
            rows = svc.monthly_audit_view(int(y), int(m))
            st.write(f"{len(rows)} {t('entries')}")
            for r in rows:
                st.write(r)
        except Exception as e:
            st.error(str(e))

def backup_page(svc, user):
    st.header(t("backup_restore"))
    if user["role"] != "Admin":
        st.warning(t("admin_only")); return

    # 备份（回车提交）
    st.subheader(t("create_backup"))
    with st.form("backup_now_form", clear_on_submit=False):
        do_bak = st.form_submit_button(t("create_backup_now"))
    if do_bak:
        path = svc.backup_now(user["username"])
        st.success(("Backup created: " + path) if st.session_state.get("lang","en")=="en" 
                   else ("已创建备份: " + path))

    st.subheader(t("restore_from_backup"))
    with st.form("restore_form", clear_on_submit=False):
        fname = st.text_input(t("backup_file_name"), key="restore_name")
        do_res = st.form_submit_button(t("restore_now"))
    if do_res:
        try:
            svc.restore_from_backup(user["username"], fname)
            st.success(t("saved"))
        except Exception as e:
            st.error(str(e))

    st.subheader(t("existing_backups"))
    st.write(svc.list_backups())

    st.subheader(t("checksum_current_data"))
    st.code(svc.checksum())

def admin_page(svc, user):
    st.header(t("admin"))
    if user["role"] != "Admin":
        st.warning(t("admin_only")); return

    # ---- 创建用户（回车提交）----
    st.subheader(t("create_user"))
    with st.form("admin_create_form", clear_on_submit=False):
        username = st.text_input(t("username"), key="admin_new_username")
        password = st.text_input(t("password"), type="password", key="admin_new_pwd")
        role = st.selectbox(t("role_label"), ["Admin","Auditor","Nurse","Doctor","Patient"], key="admin_new_role")
        do_create = st.form_submit_button(t("create"))
    if do_create:
        try:
            svc.admin_create_user(user["username"], username, password, role)
            st.success(t("user_created"))
        except Exception as e:
            st.error(str(e))

    # ---- 启停用户（回车提交）----
    st.subheader(t("disable_enable_user"))
    with st.form("admin_toggle_user_form", clear_on_submit=False):
        u2 = st.text_input(t("username_to_change"), key="admin_toggle_username")
        dis = st.checkbox(t("disable_this_user"), value=True, key="admin_toggle_disabled")
        do_apply = st.form_submit_button(t("apply_change"))
    if do_apply:
        try:
            svc.admin_disable_user(user["username"], u2, dis)
            st.success(t("saved"))
        except Exception as e:
            st.error(str(e))

    # ---- 分配病人给用户（下拉 + 回车提交）----
    st.subheader(t("assign_patient_to_user"))
    st.caption(t("only_staff_roles_listed"))
    eligible = svc.list_users(roles=["Nurse","Doctor","Admin"], only_enabled=True)
    if not eligible:
        st.info(t("no_eligible_users"))
        return
    display = [f'{u["username"]} ({role_display(u["role"])})' for u in eligible]
    with st.form("admin_assign_form", clear_on_submit=False):
        pid = st.text_input(t("patient_id"), key="admin_assign_pid")
        idx = st.selectbox(t("select_target_user"),
                           options=list(range(len(eligible))),
                           format_func=lambda i: display[i],
                           key="admin_assign_user_sel")
        do_assign = st.form_submit_button(t("assign"))
    if do_assign:
        try:
            uname = eligible[idx]["username"]
            svc.admin_assign_patient(user["username"], uname, pid)
            st.success(t("assigned"))
        except Exception as e:
            st.error(str(e))

# Backward-compatible alias expected by main_dashboard
admin_panel = admin_page