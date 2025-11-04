# gui/roster_pages.py
import streamlit as st
import datetime
import io, csv, re, json
import os
from pathlib import Path
from app.i18n import STR

def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return STR.get(lang, STR["en"]).get(key, key)

def make_export_bytes(rows, fmt: str):
    """
    rows: List[Dict[str, Any]] （若是 DataFrame，先 rows = df.to_dict('records')）
    fmt:  'CSV' | 'TXT'
    return: (bytes, mime, ext)
    """
    if not rows:
        return b"", "text/plain", "txt"

    headers = list(rows[0].keys())

    if fmt == "CSV":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        # Use utf-8-sig (with BOM) for Excel compatibility
        data = buf.getvalue().encode("utf-8-sig")
        return data, "text/csv", "csv"

    if fmt == "TXT":
        lines = []
        for r in rows:
            lines.append("; ".join(f"{k}={r.get(k,'')}" for k in headers))
        data = ("\n".join(lines)).encode("utf-8")
        return data, "text/plain", "txt"

    # Fallback: unknown formats revert to CSV
    return make_export_bytes(rows, "CSV")

def export_report_bytes(report_text: str, fmt: str):
    """
    report_text: 已经渲染在页面上的报告全文（字符串）
    fmt: 'TXT' | 'CSV'
    return: (bytes, mime, ext)
    """
    if not report_text:
        return b"", "text/plain", "txt"

    if fmt == "TXT":
        return report_text.encode("utf-8"), "text/plain", "txt"

    # CSV: split each row into time + content (leave time empty if no timestamp)
    rows = []
    for line in report_text.splitlines():
        m = re.match(r"^\s*\[([^\]]+)\]\s*(.*)$", line.rstrip("\n"))
        if m:
            rows.append({"time": m.group(1), "content": m.group(2)})
        else:
            rows.append({"time": "", "content": line.rstrip("\n")})

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["time", "content"])
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig"), "text/csv", "csv"

# ====== audit export utils ======
AUDIT_CSV_FIELDS = [
    "ts", "actor", "action",
    "type", "id", "patient_id", "visit_id",
    "username", "role", "extra"   # username/role/extra taken from meta
]

def _flatten_audit_row(ev: dict) -> dict:
    """把一条审计事件拍平成 CSV 行（缺失字段留空）"""
    meta = ev.get("meta") or {}
    row = {
        "ts": ev.get("ts", ""),
        "actor": ev.get("actor", ""),
        "action": ev.get("action", ""),
        "type": ev.get("type", ""),
        "id": ev.get("id", ""),
        "patient_id": ev.get("patient_id", "") or ev.get("pid", ""),
        "visit_id": ev.get("visit_id", "") or ev.get("vid", ""),
        "username": meta.get("username", ""),
        "role": meta.get("role", ""),
        # Merge remaining metadata into one column for table viewing
        "extra": json.dumps({k: v for k, v in meta.items() if k not in ("username", "role")}, ensure_ascii=False)
    }
    return row

def export_audit_bytes(entries: list[dict], fmt: str):
    """
    entries: 审计事件列表（list[dict]）
    fmt: 'TXT' | 'CSV'
    return: (bytes, mime, ext)
    """
    if not entries:
        return b"", "text/plain", "txt"

    if fmt == "TXT":
        # One item per line to ease reading and auditing
        lines = [json.dumps(e, ensure_ascii=False) for e in entries]
        data = ("\n".join(lines)).encode("utf-8")
        return data, "text/plain", "txt"

    # CSV: flatten into common fields
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=AUDIT_CSV_FIELDS)
    writer.writeheader()
    for ev in entries:
        writer.writerow(_flatten_audit_row(ev))
    data = buf.getvalue().encode("utf-8-sig")  # Excel-friendly
    return data, "text/csv", "csv"
# ====== end utils ======

def role_display(role: str) -> str:
    mapping = {"Admin": t("role_admin"), "Auditor": t("role_auditor"),
               "Nurse": t("role_nurse"), "Doctor": t("role_doctor"), "Patient": t("role_patient")}
    return mapping.get(role, role)

def observations_page(svc, user):
    st.header(t("observations"))
    role = user["role"]

    # Step 1: choose patient
    st.subheader(t("step1_select_patient"))
    all_patients = svc.get_all_patients()
    patient_options = {f"{p['id']} - {p.get('name', 'N/A')}": p['id'] for p in all_patients}
    patient_options_list = [""] + list(patient_options.keys())

    selected_patient = st.selectbox(
        t("select_patient"),
        patient_options_list,
        key="obs_patient_select",
        help=t("select_patient_help")
    )
    pid = patient_options.get(selected_patient, "") if selected_patient else ""

    # Show the selected patient information
    if pid:
        st.success(f"{t('selected_patient')}: {selected_patient}")
    else:
        st.info(t("please_select_patient_first"))
        return

    can_edit = role in ("Admin","Nurse","Doctor")

    if can_edit:
        st.divider()

        # Step 2: create a new observation
        st.subheader(t("step2_add_observation"))

        with st.form("obs_create_form", clear_on_submit=True):
            st.markdown(f"**{t('patient')}: {selected_patient}**")

            col1, col2 = st.columns(2)
            with col1:
                pain = st.slider(t("pain_level"), 0, 10, 0, key="pain", help=t("pain_help"))
            with col2:
                appetite = st.selectbox(
                    t("appetite_level"),
                    ["Good", "Average", "Poor"],
                    key="appetite",
                    format_func=lambda x: t(f"appetite_{x.lower()}")
                )

            note = st.text_area(t("clinical_notes"), key="note", height=100, help=t("note_help"))

            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                do_create = st.form_submit_button(t("save_observation"), type="primary", use_container_width=True)

        if do_create:
            try:
                # Automatically create visit record
                vid = svc.add_visit(pid, None, username=user["username"])

                # Create observation record
                oid = svc.add_observation(
                    user["username"], pid, vid,
                    int(pain), appetite, note
                )
                st.success(f"{t('observation_saved')}: {oid}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.divider()
    else:
        st.info(t("read_only"))
        st.divider()

    # Step 3: review history
    st.subheader(t("step3_view_history"))

    # History filter options
    status_options = [
        ("active", t("filter_deleted_active")),
        ("deleted", t("filter_deleted_deleted")),
        ("all", t("filter_deleted_all")),
    ]
    status_choice = st.selectbox(
        t("filter_deleted_label"),
        options=[opt[0] for opt in status_options],
        format_func=lambda value: dict(status_options)[value],
        key="obs_status_filter",
    )
    status_map = {"active": False, "deleted": True, "all": None}
    deleted_filter = status_map.get(status_choice, False)

    show_all = st.checkbox(
        t("show_all_history"),
        key="obs_show_all",
        help=t("show_all_history_help"),
        value=st.session_state.get("obs_show_all", False),
    )

    # Fetch observation records
    recent = svc.list_recent_observations(90, username=user["username"], patient_id=pid, deleted=deleted_filter)
    history = svc.list_history_observations(90, username=user["username"], patient_id=pid, deleted=deleted_filter)

    if show_all:
        # Merge and sort when user explicitly requests the complete history
        observations = (recent + history)
        observations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        st.caption(t("showing_all_history"))
    else:
        # Show only records within the recent window
        observations = recent
        if history:
            st.caption(t("older_records_hidden"))
    if not observations:
        st.info(t("no_observations_found"))
        return

    st.caption(f"{t('total_records')}: {len(observations)}")

    # Render observation records as cards
    for idx, o in enumerate(observations):
        with st.container():
            is_deleted = o.get("deleted", False)

            # Create a card-style border
            col_header1, col_header2, col_header3 = st.columns([2, 2, 1])

            with col_header1:
                st.markdown(f"**{t('observation_id')}: `{o['id']}`**")
            with col_header2:
                st.markdown(f"**{t('date')}: {o.get('created_at', 'N/A')[:16]}**")
            with col_header3:
                st.markdown(f"**{t('created_by')}: {o.get('created_by', 'N/A')}**")

            # Display observation data
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(t("pain_level"), f"{o['pain']}/10")
            with col2:
                # Fix nested string quotes
                st.metric(t("appetite_level"), t(f"appetite_{o['appetite'].lower()}"))
            with col3:
                st.metric(t("visit_id"), o.get('visit_id', 'N/A'))

            if o.get('note'):
                st.text_area(t("clinical_notes"), value=o['note'], height=80, disabled=True, key=f"note_display_{o['id']}")

            if is_deleted:
                st.info(t("soft_deleted_flag"))
            elif can_edit:
                # Edit and delete actions
                with st.expander(t('edit_or_delete')):
                    with st.form(f"obs_edit_form_{o['id']}", clear_on_submit=False):
                        st.markdown(f"**{t('editing_record')}: {o['id']}**")

                        edit_col1, edit_col2 = st.columns(2)
                        with edit_col1:
                            newpain = st.slider(t("pain_level"), 0, 10, o["pain"], key="p_"+o["id"])
                        with edit_col2:
                            newapp = st.selectbox(
                                t("appetite_level"),
                                ["Good", "Average", "Poor"],
                                index=["Good", "Average", "Poor"].index(o["appetite"]),
                                key="a_"+o["id"],
                                format_func=lambda x: t(f"appetite_{x.lower()}")
                            )

                        newnote = st.text_area(t("clinical_notes"), value=o["note"], key="n_"+o["id"], height=100)

                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            do_save = st.form_submit_button(t("save_changes"), type="primary", use_container_width=True)
                        with btn_col2:
                            do_del = st.form_submit_button(t("delete_record"), use_container_width=True)

                    if do_save:
                        try:
                            svc.edit_observation(o["id"], pain=int(newpain), appetite=newapp, note=newnote)
                            st.success(t('saved'))
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                    if do_del:
                        svc.soft_delete_observation(o["id"])
                        st.warning(t('record_deleted'))
                        st.rerun()
            else:
                st.info(t("read_only"))

            st.divider()

def stories_page(svc, user):
    st.header(t("stories"))
    role = user["role"]

    # Step 1: choose patient
    st.subheader(t("step1_select_patient"))
    all_patients = svc.get_all_patients()
    patient_options = {f"{p['id']} - {p.get('name', 'N/A')}": p['id'] for p in all_patients}
    patient_options_list = [""] + list(patient_options.keys())

    selected_patient = st.selectbox(
        t("select_patient"),
        patient_options_list,
        key="story_patient_select",
        help=t("select_patient_help")
    )
    pid = patient_options.get(selected_patient, "") if selected_patient else ""

    if pid:
        st.success(f"{t('selected_patient')}: {selected_patient}")
    else:
        st.info(t("please_select_patient_first"))
        return

    can_edit = role in ("Admin","Nurse","Doctor")

    if can_edit:
        st.divider()

        # Step 2: add a new narrative
        st.subheader(t("step2_add_story"))

        with st.form("story_form", clear_on_submit=True):
            st.markdown(f"**{t('patient')}: {selected_patient}**")
            text = st.text_area(t("story_text"), key="story_text", height=200, help=t("story_help"))

            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                do_create = st.form_submit_button(t("save_story"), type="primary", use_container_width=True)

        if do_create:
            try:
                # Automatically create visit record
                vid = svc.add_visit(pid, None, username=user["username"])
                # Create narrative record
                sid = svc.add_story(user["username"], pid, vid, text)
                st.success(f"{t('story_saved')}: {sid}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.divider()
    else:
        st.info(t("read_only"))
        st.divider()

    # Step 3: review history
    st.subheader(t("step3_view_history"))

    status_options = [
        ("active", t("filter_deleted_active")),
        ("deleted", t("filter_deleted_deleted")),
        ("all", t("filter_deleted_all")),
    ]
    status_choice = st.selectbox(
        t("filter_deleted_label"),
        options=[opt[0] for opt in status_options],
        format_func=lambda value: dict(status_options)[value],
        key="story_status_filter",
    )
    status_map = {"active": False, "deleted": True, "all": None}
    deleted_filter = status_map.get(status_choice, False)

    show_all = st.checkbox(
        t("show_all_history"),
        key="story_show_all",
        help=t("show_all_history_help"),
        value=st.session_state.get("story_show_all", False),
    )

    # Fetch narrative records
    recent = svc.list_recent_stories(90, username=user["username"], patient_id=pid, deleted=deleted_filter)
    history = svc.list_history_stories(90, username=user["username"], patient_id=pid, deleted=deleted_filter)

    if show_all:
        stories = recent + history
        stories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        st.caption(t("showing_all_history"))
    else:
        stories = recent
        if history:
            st.caption(t("older_records_hidden"))
    if not stories:
        st.info(t("no_stories_found"))
        return

    st.caption(f"{t('total_records')}: {len(stories)}")

    # Render narrative records as cards
    for s in stories:
        with st.container():
            is_deleted = s.get("deleted", False)

            col_header1, col_header2, col_header3 = st.columns([2, 2, 1])

            with col_header1:
                st.markdown(f"**{t('story_id')}: `{s['id']}`**")
            with col_header2:
                st.markdown(f"**{t('date')}: {s.get('created_at', 'N/A')[:16]}**")
            with col_header3:
                st.markdown(f"**{t('created_by')}: {s.get('created_by', 'N/A')}**")

            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric(t("patient_id"), s.get('patient_id', 'N/A'))
            with col2:
                st.metric(t("visit_id"), s.get('visit_id', 'N/A'))

            st.text_area(t("story_text"), value=s.get('text', ''), height=120, disabled=True, key=f"story_display_{s['id']}")

            if is_deleted:
                st.info(t("soft_deleted_flag"))
            elif can_edit:
                # Edit and delete actions
                with st.expander(t('edit_or_delete')):
                    with st.form(f"story_edit_form_{s['id']}", clear_on_submit=False):
                        st.markdown(f"**{t('editing_record')}: {s['id']}**")
                        newtext = st.text_area(t("story_text"), value=s['text'], key="t_"+s["id"], height=200)

                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            do_save = st.form_submit_button(t("save_changes"), type="primary", use_container_width=True)
                        with btn_col2:
                            do_del = st.form_submit_button(t("delete_record"), use_container_width=True)

                    if do_save:
                        try:
                            svc.edit_story(s["id"], text=newtext)
                            st.success(t('saved'))
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                    if do_del:
                        svc.soft_delete_story(user["username"], s["id"])
                        st.warning(t('record_deleted'))
                        st.rerun()
            else:
                st.info(t("read_only"))

            st.divider()

def handover_page(svc, user):
    st.header(t("handover"))
    role = user["role"]

    # Step 1: choose patient
    st.subheader(t("step1_select_patient"))
    all_patients = svc.get_all_patients()
    patient_options = {f"{p['id']} - {p.get('name', 'N/A')}": p['id'] for p in all_patients}
    patient_options_list = [""] + list(patient_options.keys())

    selected_patient = st.selectbox(
        t("select_patient"),
        patient_options_list,
        key="handover_patient_select",
        help=t("select_patient_for_handover")
    )
    pid = patient_options.get(selected_patient, "") if selected_patient else ""

    if pid:
        st.success(f"{t('selected_patient')}: {selected_patient}")
    else:
        st.info(t("please_select_patient_first"))
        return

    if role not in ("Admin","Nurse","Doctor"):
        st.info(t("read_only"))
        return

    st.divider()

    # Step 2: edit handover record
    st.subheader(t("step2_handover_notes"))

    current = svc.get_handover(pid)
    default_text = (current or {}).get("text", "")

    # Show last updated details
    if current:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("handover_id"), current.get("id", "N/A"))
        with col2:
            ts_show = current.get("updated_at") or current.get("created_at")
            st.metric(t("last_updated"), ts_show[:16] if ts_show else "N/A")
        with col3:
            st.metric(t("updated_by"), current.get("created_by", "N/A"))

    with st.form("handover_form", clear_on_submit=False):
        st.markdown(f"**{t('patient')}: {selected_patient}**")
        text_area = st.text_area(
            t("handover_note"),
            value=default_text,
            height=300,
            key="handover_text",
            help=t("handover_help")
        )

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            do_save = st.form_submit_button(t("save_handover"), type="primary", use_container_width=True)

    if do_save:
        try:
            hid = svc.create_or_update_handover(user["username"], pid, text_area)
            st.session_state["handover_flash_success"] = f"{t('handover_saved')}: {hid}"
            st.session_state.pop("handover_flash_error", None)
        except Exception as e:
            st.session_state["handover_flash_error"] = str(e)
            st.session_state.pop("handover_flash_success", None)
        st.rerun()

    flash_success = st.session_state.pop("handover_flash_success", None)
    if flash_success:
        st.success(flash_success)
    flash_error = st.session_state.pop("handover_flash_error", None)
    if flash_error:
        st.error(flash_error)

def search_page(svc, user):
    st.header(t("search"))

    # Configure search criteria
    st.subheader(t("search_criteria"))

    # History options
    show_hist = st.checkbox(t("show_all_history"), value=False, key="search_hist_toggle", help=t("show_all_history_help"))
    default_start = (datetime.date.today() - datetime.timedelta(days=90))
    default_end = datetime.date.today()

    with st.form("search_form", clear_on_submit=False):
        # Keyword search
        kw = st.text_input(t("keyword"), key="search_kw", help=t("search_keyword_help"))

        # Date range (no limit when “show all history” is checked)
        c1, c2 = st.columns(2)
        d_start = c1.date_input(t("start_date"), value=None if show_hist else default_start, key="search_start_date")
        d_end = c2.date_input(t("end_date"), value=None if show_hist else default_end, key="search_end_date")

        # Five searchable types (plural)
        type_opts = ["observations", "stories", "visits", "preferences", "handover"]
        picked = st.multiselect(t("search_types"), type_opts, default=type_opts, key="search_type_opts")

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            do_search = st.form_submit_button(t("search_button"), type="primary", use_container_width=True)

    results = []
    if do_search:
        start_str = None if (show_hist or not d_start) else d_start.isoformat()
        end_str = None if (show_hist or not d_end) else d_end.isoformat()
        # Use the new unified search interface
        results = svc.search_entries(keyword=kw, start=start_str, end=end_str, types=set(picked))

        # Cache results in session for export
        st.session_state["search_entries_results"] = results

    st.divider()

    # Search results
    st.subheader(t("search_results"))

    results = st.session_state.get("search_entries_results", results)

    if not results:
        st.info(t("no_search_results"))
        return

    # Result summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric(t("total_results"), len(results))
    with col2:
        hint = t("mode_history") if show_hist else t("mode_recent_90")
        st.caption(hint)

    # Render results (shared across the five types)
    for r in results:
        ts = r.get("ts")
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts)
        st.write(f"[{r['type']}] {r.get('patient_id') or '-'} · {ts_str} · {(r.get('text') or '')[:120]}")

    # Export functionality
    st.divider()
    st.subheader(t("export"))

    export_fmt = st.selectbox(t("export_format"), ["TXT", "CSV"], index=0)

    if results:
        data, mime, ext = make_export_bytes(results, export_fmt)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label=f"{t('download')}（.{ext}）",
            data=data,
            file_name=f"search_export_{ts}.{ext}",
            mime=mime,
            use_container_width=True
        )
    else:
        st.info(t("no_search_results_to_export"))

def report_page(svc, user):
    # Top section: ensure a stable session_state
    if "report_text" not in st.session_state:
        st.session_state["report_text"] = ""
    
    st.header(t("report"))
    role = user["role"]
    import datetime as _dt

    if role == "Patient":
        # Patient view: review personal reports
        st.subheader(t("your_patient_report"))

        my_pids = svc.get_assigned_patient_ids(user["username"])
        if not my_pids:
            st.warning(t("no_patient_record_linked"))
            return

        with st.form("report_my_form", clear_on_submit=False):
            pid = st.selectbox(t("your_patient_record"), my_pids, index=0, key="report_patient_pick")
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                do_gen = st.form_submit_button(t("generate"), type="primary", use_container_width=True)

        if do_gen:
            report_text = svc.text_report(patient_id=pid)
            st.session_state["report_text"] = report_text
            st.divider()
            
    else:
        # Clinician view: choose report mode
        st.subheader(t("select_report_mode"))

        mode = st.radio(
            t("report_mode"),
            [t("by_patient"), t("by_date")],
            key="report_mode",
            horizontal=True,
            help=t("report_mode_help")
        )

        st.divider()

        if mode == t("by_patient"):
            # Generate reports by patient
            st.subheader(t("generate_patient_report"))

            # History options
            show_hist = st.checkbox(t("show_all_history"), value=False, key="report_hist_toggle", help=t("show_all_history_help"))

            # Fetch all patient entries
            all_patients = svc.get_all_patients()
            patient_options = {f"{p['id']} - {p.get('name', 'N/A')}": p['id'] for p in all_patients}
            patient_options_list = [""] + list(patient_options.keys())

            with st.form("report_by_pid_form", clear_on_submit=False):
                selected_patient = st.selectbox(
                    t("select_patient"),
                    patient_options_list,
                    key="report_patient_select",
                    help=t("select_patient_for_report")
                )
                pid = patient_options.get(selected_patient, "") if selected_patient else ""

                col_btn1, col_btn2 = st.columns([1, 4])
                with col_btn1:
                    do_gen1 = st.form_submit_button(t("generate"), type="primary", use_container_width=True)

            if do_gen1:
                if not pid:
                    st.error(t("please_select_patient_first"))
                else:
                    if show_hist:
                        st.caption(t("showing_all_history"))
                        report_text = svc.text_report(patient_id=pid)
                    else:
                        st.caption(t("showing_recent_90_days"))
                        _to = _dt.date.today().isoformat()
                        _from = (_dt.date.today() - _dt.timedelta(days=90)).isoformat()
                        report_text = svc.text_report(patient_id=pid, date_from=_from, date_to=_to)
                    st.session_state["report_text"] = report_text
                    st.divider()
        else:
            # Generate reports by date
            st.subheader(t("generate_date_report"))

            with st.form("report_by_date_form", clear_on_submit=False):
                d = st.date_input(
                    t("select_date"),
                    value=_dt.date.today(),
                    key="report_date",
                    help=t("select_date_for_report")
                )

                col_btn1, col_btn2 = st.columns([1, 4])
                with col_btn1:
                    do_gen2 = st.form_submit_button(t("generate"), type="primary", use_container_width=True)

            if do_gen2:
                st.caption(f"{t('report_for_date')}: {d}")
                dt_iso = _dt.datetime.combine(d, _dt.time(0,0)).astimezone().isoformat()
                report_text = svc.text_report(date_iso=dt_iso)
                st.session_state["report_text"] = report_text
                st.divider()
    
    # Pull text from session consistently
    report_text = st.session_state.get("report_text", "")

    st.subheader(t("report_content"))
    if report_text.strip():
        st.code(report_text)

        st.divider()
        st.subheader(t("export_report"))

        # -- Export formats (TXT/CSV only) --
        export_fmt = st.selectbox(t("export_format"), ["TXT", "CSV"], index=0, key="report_export_fmt")

        # Generate binary content
        data, mime, ext = export_report_bytes(report_text, export_fmt)

        # Use a stable key; avoid time-stamp-based keys
        st.download_button(
            label=f"{t('download_report')} (.{ext})",
            data=data,
            file_name=f"report_export.{ext}",  # Add a date to the filename to avoid overwriting, but keep the key fixed
            mime=mime,
            use_container_width=True,
            key="report_download_btn"
        )
    else:
        st.info(t("no_report_to_export"))

def auditor_page(svc):
    st.header(t("auditor"))
    
    # Initialize session state to store audit data
    if "audit_entries" not in st.session_state:
        st.session_state["audit_entries"] = []
    
    with st.form("aud_form", clear_on_submit=False):
        ym = st.text_input(t("ym_label"), value=datetime.date.today().strftime("%Y-%m"), key="aud_ym")
        do_aud = st.form_submit_button("OK")
    if do_aud:
        try:
            y, m = ym.split("-")
            rows = svc.monthly_audit_view(int(y), int(m))
            # Store in session state to keep data available for export
            st.session_state["audit_entries"] = rows
            st.write(f"{len(rows)} {t('entries')}")
            st.json(rows)
        except Exception as e:
            st.error(str(e))
    
    # Export section (i18n)
    st.divider()
    st.subheader(t("export_month_audit"))
    
    export_fmt = st.selectbox(t("export_format"), ["TXT", "CSV"], index=0, key="audit_export_fmt")
    
    current_entries = st.session_state.get("audit_entries", [])
    if current_entries:
        data, mime, ext = export_audit_bytes(current_entries, export_fmt)
        st.download_button(
            label=f"{t('download_audit')} (.{ext})",
            data=data,
            file_name=f"audit_{ym}.{ext}",
            mime=mime,
            use_container_width=True,
            key="audit_download_btn"
        )
    else:
        st.info(t("no_audit_to_export"))

def backup_page(svc, user):
    st.header(t("backup_restore"))
    if user["role"] != "Admin":
        st.warning(t("admin_only")); return

    # --- State initialization (avoid stale state) ---
    st.session_state.pop("backup_ok", None)
    st.session_state.pop("restore_ok", None)
    st.session_state.pop("last_msg", None)

    BACKUP_DIR = Path("backups")

    # ========== Create backup ==========
    st.subheader(t("create_backup"))
    if st.button(t("create_backup_now"), key="btn_backup_now", use_container_width=True):
        try:
            # Call the service-layer backup function
            fname = svc.backup_now(user["username"])
            st.session_state["backup_ok"] = True
            st.session_state["last_msg"] = t("backup_succeeded").format(fname=fname)
        except Exception as e:
            st.error(f"{t('backup_failed')}: {e}")
            st.stop()

    # ========== Restore from backup ==========
    st.subheader(t("restore_from_backup"))
    restore_name = st.text_input(
        t("backup_file_name"), 
        value="", 
        placeholder=t("backup_file_placeholder"),
        key="restore_name"
    )

    if st.button(t("restore_now"), key="btn_restore_now", use_container_width=True):
        name = restore_name.strip()
        if not name:
            st.warning(t("please_enter_backup_filename"))
            st.stop()
        path = BACKUP_DIR / name if not os.path.isabs(name) else Path(name)
        if not path.exists():
            st.error(f"{t('backup_file_not_found')}: {path}")
            st.stop()
        try:
            # Call the service-layer restore function
            svc.restore_from_backup(user["username"], str(path))
            st.session_state["restore_ok"] = True
            st.session_state["last_msg"] = f"{t('restored_from')}：{path.name}"
        except Exception as e:
            st.error(f"{t('restore_failed')}: {e}")
            st.stop()

    # ========== Unified message area ==========
    if st.session_state.get("backup_ok"):
        st.success(st.session_state.get("last_msg", t("backup_succeeded")))
    elif st.session_state.get("restore_ok"):
        st.success(st.session_state.get("last_msg", t("restore_succeeded")))

    # ========== Show existing backups & validation ==========
    st.subheader(t("existing_backups"))
    try:
        files = sorted([p.name for p in BACKUP_DIR.glob("*.bak")])
        st.json(files)
    except Exception:
        st.info(t("no_backup_files_yet"))

    st.subheader(t("checksum_current_data"))
    try:
        st.code(svc.checksum())
    except Exception as e:
        st.error(f"{t('checksum_failed')}: {e}")

def admin_page(svc, user):
    st.header(t("admin"))
    if user["role"] != "Admin":
        st.warning(t("admin_only")); return

    # ---- Create user (submit on Enter) ----
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

    # ---- Enable or disable user (submit on Enter) ----
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

    # ---- Assign patients to users (dropdown + Enter to submit) ----
    st.subheader(t("assign_patient_to_user"))
    st.caption(t("only_staff_roles_listed"))
    eligible = svc.list_users(roles=["Nurse","Doctor","Admin"], only_enabled=True)
    if not eligible:
        st.info(t("no_eligible_users"))
        return
    display = [f'{u["username"]} ({role_display(u["role"])})' for u in eligible]

    # Fetch all patient entries
    all_patients = svc.get_all_patients()
    patient_options = {f"{p['id']} - {p.get('name', 'N/A')}": p['id'] for p in all_patients}
    patient_options_list = [""] + list(patient_options.keys())

    with st.form("admin_assign_form", clear_on_submit=False):
        selected_patient = st.selectbox(t("select_patient"), patient_options_list, key="admin_assign_patient_select")
        pid = patient_options.get(selected_patient, "") if selected_patient else ""
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
