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
        # 为了兼容 Excel，使用 utf-8-sig（带 BOM）
        data = buf.getvalue().encode("utf-8-sig")
        return data, "text/csv", "csv"

    if fmt == "TXT":
        lines = []
        for r in rows:
            lines.append("; ".join(f"{k}={r.get(k,'')}" for k in headers))
        data = ("\n".join(lines)).encode("utf-8")
        return data, "text/plain", "txt"

    # 兜底：未知格式回退 CSV
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

    # CSV：每行拆成 time + content（若无时间戳则 time 为空）
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
    "username", "role", "extra"   # username/role/extra 从 meta 中提取
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
        # 其余元数据合并成一列，便于在表格里查看
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
        # 一行一条，便于阅读/审计归档
        lines = [json.dumps(e, ensure_ascii=False) for e in entries]
        data = ("\n".join(lines)).encode("utf-8")
        return data, "text/plain", "txt"

    # CSV：拍平为常用字段
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=AUDIT_CSV_FIELDS)
    writer.writeheader()
    for ev in entries:
        writer.writerow(_flatten_audit_row(ev))
    data = buf.getvalue().encode("utf-8-sig")  # Excel 友好
    return data, "text/csv", "csv"
# ====== end utils ======

def role_display(role: str) -> str:
    mapping = {"Admin": t("role_admin"), "Auditor": t("role_auditor"),
               "Nurse": t("role_nurse"), "Doctor": t("role_doctor"), "Patient": t("role_patient")}
    return mapping.get(role, role)

def observations_page(svc, user):
    st.header(t("observations"))
    role = user["role"]

    # 步骤1：选择病人
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

    # 显示选中的病人信息
    if pid:
        st.success(f"{t('selected_patient')}: {selected_patient}")
    else:
        st.info(t("please_select_patient_first"))
        return

    if role not in ("Admin","Nurse","Doctor"):
        st.info(t("read_only"))
        return

    st.divider()

    # 步骤2：创建新观察记录
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
            # 自动创建就诊记录
            vid = svc.add_visit(pid, None, username=user["username"])

            # 创建观察记录
            oid = svc.add_observation(
                user["username"], pid, vid,
                int(pain), appetite, note
            )
            st.success(f"{t('observation_saved')}: {oid}")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.divider()

    # 步骤3：查看历史记录
    st.subheader(t("step3_view_history"))

    # 历史记录筛选选项
    show_all = st.checkbox(t("show_all_history"), key="obs_show_all", help=t("show_all_history_help"))

    # 获取观察记录
    if show_all:
        # 显示所有记录：90天内的 + 90天之前的
        recent = svc.list_recent_observations(90, username=user["username"])
        history = svc.list_history_observations(90, username=user["username"])
        observations = recent + history
        # 按日期排序
        observations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    else:
        # 只显示90天内的记录
        observations = svc.list_recent_observations(90, username=user["username"])

    if not observations:
        st.info(t("no_observations_found"))
        return

    st.caption(f"{t('total_records')}: {len(observations)}")

    # 以卡片形式显示观察记录
    for idx, o in enumerate(observations):
        with st.container():
            # 创建卡片样式的边框
            col_header1, col_header2, col_header3 = st.columns([2, 2, 1])

            with col_header1:
                st.markdown(f"**{t('observation_id')}: `{o['id']}`**")
            with col_header2:
                st.markdown(f"**{t('date')}: {o.get('created_at', 'N/A')[:16]}**")
            with col_header3:
                st.markdown(f"**{t('created_by')}: {o.get('created_by', 'N/A')}**")

            # 显示观察数据
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(t("pain_level"), f"{o['pain']}/10")
            with col2:
                st.metric(t("appetite_level"), t(f'appetite_{o['appetite'].lower()}'))
            with col3:
                st.metric(t("visit_id"), o.get('visit_id', 'N/A'))

            if o.get('note'):
                st.text_area(t("clinical_notes"), value=o['note'], height=80, disabled=True, key=f"note_display_{o['id']}")

            # 编辑和删除操作
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

            st.divider()

def stories_page(svc, user):
    st.header(t("stories"))
    role = user["role"]

    # 步骤1：选择病人
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

    if role not in ("Admin","Nurse","Doctor"):
        st.info(t("read_only"))
        return

    st.divider()

    # 步骤2：添加新叙事记录
    st.subheader(t("step2_add_story"))

    with st.form("story_form", clear_on_submit=True):
        st.markdown(f"**{t('patient')}: {selected_patient}**")
        text = st.text_area(t("story_text"), key="story_text", height=200, help=t("story_help"))

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            do_create = st.form_submit_button(t("save_story"), type="primary", use_container_width=True)

    if do_create:
        try:
            # 自动创建就诊记录
            vid = svc.add_visit(pid, None, username=user["username"])
            # 创建叙事记录
            sid = svc.add_story(user["username"], pid, vid, text)
            st.success(f"{t('story_saved')}: {sid}")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.divider()

    # 步骤3：查看历史记录
    st.subheader(t("step3_view_history"))

    show_all = st.checkbox(t("show_all_history"), key="story_show_all", help=t("show_all_history_help"))

    # 获取叙事记录
    if show_all:
        recent = svc.list_recent_stories(90, username=user["username"])
        history = svc.list_history_stories(90, username=user["username"])
        stories = recent + history
        stories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    else:
        stories = svc.list_recent_stories(90, username=user["username"])

    if not stories:
        st.info(t("no_stories_found"))
        return

    st.caption(f"{t('total_records')}: {len(stories)}")

    # 以卡片形式显示叙事记录
    for s in stories:
        with st.container():
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

            # 编辑和删除操作
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
                    svc.soft_delete_story(s["id"])
                    st.warning(t('record_deleted'))
                    st.rerun()

            st.divider()

def handover_page(svc, user):
    st.header(t("handover"))
    role = user["role"]

    # 步骤1：选择病人
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

    # 步骤2：编辑交接班记录
    st.subheader(t("step2_handover_notes"))

    current = svc.get_handover(pid)
    default_text = (current or {}).get("text", "")

    # 显示最后更新信息
    if current:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("handover_id"), current.get("id", "N/A"))
        with col2:
            st.metric(t("last_updated"), current.get("updated_at", "N/A")[:16] if current.get("updated_at") else "N/A")
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
            hid = svc.create_or_update_handover(user["username"], pid, st.session_state.get("handover_text", ""))
            st.success(f"{t('handover_saved')}: {hid}")
            st.rerun()
        except Exception as e:
            st.error(str(e))

def search_page(svc, user):
    st.header(t("search"))

    # 搜索条件设置
    st.subheader(t("search_criteria"))

    # 历史记录选项
    show_hist = st.checkbox(t("show_all_history"), value=False, key="search_hist_toggle", help=t("show_all_history_help"))
    default_start = (datetime.date.today() - datetime.timedelta(days=90))
    default_end = datetime.date.today()

    with st.form("search_form", clear_on_submit=False):
        # 关键词搜索
        kw = st.text_input(t("keyword"), key="search_kw", help=t("search_keyword_help"))

        # 创建者筛选
        users = svc.list_users(roles=None, only_enabled=True)
        user_options = [""] + [u["username"] for u in users]
        creator = st.selectbox(t("created_by_optional"), user_options, index=0, key="search_creator_sel")

        # 日期范围
        c1, c2 = st.columns(2)
        d_start = c1.date_input(t("start_date"), value=None if show_hist else default_start, key="search_start_date")
        d_end = c2.date_input(t("end_date"), value=None if show_hist else default_end, key="search_end_date")

        # 记录类型多选
        all_types = ["observation","story","handover","preference","visit"]
        if user["role"] in ("Admin","Auditor"):
            all_types.append("audit")
        types = st.multiselect(
            t("record_types"),
            all_types,
            ["observation","story"],
            key="search_types",
            help=t("record_types_help")
        )

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            do_search = st.form_submit_button(t("search_button"), type="primary", use_container_width=True)

    if do_search:
        start_str = d_start.isoformat() if d_start else None
        end_str = d_end.isoformat() if d_end else None
        rows = svc.search_logs(kw, (creator or None), start_str, end_str, types or None, username=user["username"])
        st.session_state["search_rows"] = rows
        st.session_state["search_hist_is_on"] = show_hist

    st.divider()

    # 搜索结果
    st.subheader(t("search_results"))

    rows = st.session_state.get("search_rows", [])

    if not rows:
        st.info(t("no_search_results"))
        return

    # 显示结果统计
    col1, col2 = st.columns(2)
    with col1:
        st.metric(t("total_results"), len(rows))
    with col2:
        hint = t("mode_history") if st.session_state.get("search_hist_is_on") else t("mode_recent_90")
        st.caption(hint)

    # 以卡片形式显示搜索结果
    for idx, r in enumerate(rows[:200]):
        with st.container():
            col_header1, col_header2, col_header3 = st.columns([2, 2, 1])

            with col_header1:
                st.markdown(f"**{t('record_type')}: {r['type'].title()}**")
            with col_header2:
                who = r.get("created_by", r.get("actor","N/A"))
                st.markdown(f"**{t('created_by')}: {who}**")
            with col_header3:
                when = r.get("created_at", r.get("ts","N/A"))[:16]
                st.markdown(f"**{when}**")

            if "highlight" in r and r["highlight"]:
                st.markdown(r["highlight"])
            else:
                # 显示主要信息
                if r.get("patient_id"):
                    st.text(f"{t('patient_id')}: {r.get('patient_id')}")
                if r.get("text"):
                    st.text_area("", value=r.get("text", ""), height=80, disabled=True, key=f"search_text_{idx}")
                elif r.get("note"):
                    st.text(f"{t('note')}: {r.get('note')}")

            st.divider()

    # 导出功能
    st.divider()
    st.subheader(t("export"))

    export_fmt = st.selectbox(t("export_format"), ["TXT", "CSV"], index=0)

    if rows:
        data, mime, ext = make_export_bytes(rows, export_fmt)
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
    # 顶部：保证有稳定的 session_state
    if "report_text" not in st.session_state:
        st.session_state["report_text"] = ""
    
    st.header(t("report"))
    role = user["role"]
    import datetime as _dt

    if role == "Patient":
        # 患者视角：查看自己的报告
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
        # 医护人员视角：选择报告模式
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
            # 按病人生成报告
            st.subheader(t("generate_patient_report"))

            # 历史记录选项
            show_hist = st.checkbox(t("show_all_history"), value=False, key="report_hist_toggle", help=t("show_all_history_help"))

            # 获取所有病人列表
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
            # 按日期生成报告
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
    
    # 统一从会话取文本
    report_text = st.session_state.get("report_text", "")

    st.subheader(t("report_content"))
    if report_text.strip():
        st.code(report_text)

        st.divider()
        st.subheader("导出报告")

        # —— 导出格式（仅 TXT/CSV）——
        export_fmt = st.selectbox("导出格式", ["TXT", "CSV"], index=0, key="report_export_fmt")

        # 生成二进制内容
        data, mime, ext = export_report_bytes(report_text, export_fmt)

        # 用“固定不变的 key”，不要用时间戳当 key
        st.download_button(
            label=f"下载报告（.{ext}）",
            data=data,
            file_name=f"report_export.{ext}",  # 如需避免覆盖可加日期到文件名，但 key 保持固定
            mime=mime,
            use_container_width=True,
            key="report_download_btn"
        )
    else:
        st.info("暂无报告内容，请先点击上方“生成”。")

def auditor_page(svc):
    st.header(t("auditor"))
    
    # 初始化会话状态存储审计数据
    if "audit_entries" not in st.session_state:
        st.session_state["audit_entries"] = []
    
    with st.form("aud_form", clear_on_submit=False):
        ym = st.text_input(t("ym_label"), value=datetime.date.today().strftime("%Y-%m"), key="aud_ym")
        do_aud = st.form_submit_button("OK")
    if do_aud:
        try:
            y, m = ym.split("-")
            rows = svc.monthly_audit_view(int(y), int(m))
            # 保存到会话状态，确保导出时数据可用
            st.session_state["audit_entries"] = rows
            st.write(f"{len(rows)} {t('entries')}")
            st.json(rows)
        except Exception as e:
            st.error(str(e))
    
    # 导出区域
    st.divider()
    st.subheader("导出当月审计")
    
    export_fmt = st.selectbox("导出格式", ["TXT", "CSV"], index=0, key="audit_export_fmt")
    
    current_entries = st.session_state.get("audit_entries", [])
    if current_entries:
        data, mime, ext = export_audit_bytes(current_entries, export_fmt)
        st.download_button(
            label=f"下载审计（.{ext}）",
            data=data,
            file_name=f"audit_{ym}.{ext}",
            mime=mime,
            use_container_width=True,
            key="audit_download_btn"
        )
    else:
        st.info("暂无可导出的审计数据")

def backup_page(svc, user):
    st.header(t("backup_restore"))
    if user["role"] != "Admin":
        st.warning(t("admin_only")); return

    # --- 状态初始化（避免旧状态残留） ---
    st.session_state.pop("backup_ok", None)
    st.session_state.pop("restore_ok", None)
    st.session_state.pop("last_msg", None)

    BACKUP_DIR = Path("backups")

    # ========== 创建备份 ==========
    st.subheader(t("create_backup"))
    if st.button(t("create_backup_now"), key="btn_backup_now", use_container_width=True):
        try:
            # 调用服务层备份函数
            fname = svc.backup_now(user["username"])
            st.session_state["backup_ok"] = True
            st.session_state["last_msg"] = f"已备份：{fname}" if st.session_state.get("lang","en")=="en" \
                                        else f"已创建备份：{fname}"
        except Exception as e:
            st.error(f"{t('backup_failed')}: {e}")
            st.stop()

    # ========== 从备份恢复 ==========
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
            # 调用服务层恢复函数
            svc.restore_from_backup(user["username"], str(path))
            st.session_state["restore_ok"] = True
            st.session_state["last_msg"] = f"{t('restored_from')}：{path.name}"
        except Exception as e:
            st.error(f"{t('restore_failed')}: {e}")
            st.stop()

    # ========== 统一提示区 ==========
    if st.session_state.get("backup_ok"):
        st.success(st.session_state.get("last_msg", t("backup_succeeded")))
    elif st.session_state.get("restore_ok"):
        st.success(st.session_state.get("last_msg", t("restore_succeeded")))

    # ========== 展示现有备份 & 校验 ==========
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

    # 获取所有病人列表
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