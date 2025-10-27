# gui/main_dashboard.py
import streamlit as st
st.set_page_config(initial_sidebar_state="expanded") # <-- 确保侧边栏默认展开

from app.i18n import STR
from app.service import CareLogService
from app.repo_json import JsonRepo
from gui.student_pages import patients_page, preferences_page
from gui.roster_pages import (
    observations_page, stories_page, handover_page,
    search_page, report_page, auditor_page,
    backup_page, admin_panel,
)

DATA_PATH = "data/carelog.json"
BACKUPS_DIR = "backups"

@st.cache_resource
def get_service():
    repo = JsonRepo(DATA_PATH, BACKUPS_DIR)
    return CareLogService(repo)

def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return STR.get(lang, STR["en"]).get(key, key)

def role_display(role: str) -> str:
    mapping = {"Admin": t("role_admin"), "Auditor": t("role_auditor"),
               "Nurse": t("role_nurse"), "Doctor": t("role_doctor"), "Patient": t("role_patient")}
    return mapping.get(role, role)

def inject_a11y_css():
    if st.session_state.get("large_text", False):
        st.markdown("""
            <style>
              html, body, [class*="css"]  { font-size: 18px !important; line-height: 1.6 !important; }
            </style>
        """, unsafe_allow_html=True)

def hide_streamlit_chrome():
    st.markdown("""
    <style>
      /* 隐藏旧版菜单与页脚（不会影响侧边栏开关） */
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}

      /* 保留工具栏本身，单独隐藏 Deploy/状态等英文控件 */
      [data-testid="stToolbar"] {visibility: visible; height: 0px;} /* 占位，避免界面跳动 */
      /* 部分版本的 Deploy/状态控件（多加几手保险选择器） */
      [data-testid="stToolbar"] a,                    /* 可能的 Deploy 链接 */
      header [data-testid="baseButton-headerNoPadding"],  /* 顶部右侧按钮容器 */
      header [data-testid="stStatusWidget"] { 
        display: none !important;
      }

      /* ——关键：保证侧边栏折叠按钮一直可见—— */
      [data-testid="stSidebarCollapseButton"] {
        display: block !important;
        opacity: 1 !important;
        visibility: visible !important;
      }
    </style>
    """, unsafe_allow_html=True)


def login_view(svc: CareLogService):
    # 确保默认语言；为语言选择器使用单独的 key，避免和 session_state["lang"] 冲突
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    st.session_state.setdefault("lang_select", st.session_state["lang"])

    st.title(t("app_title"))

    # —— 顶部语言行：标签 | 下拉 | 按钮（对齐）——
    c_label, c_select, c_btn = st.columns([0.8, 2.5, 0.8])
    with c_label:
        st.markdown(f"**{t('language')}**")
    with c_select:
        st.selectbox(
            "", ["en", "zh"],
            index=["en", "zh"].index(st.session_state.get("lang_select", st.session_state["lang"])),
            key="lang_select",
            label_visibility="collapsed"
        )
    with c_btn:
        if st.button(t("apply"), key="apply_lang", use_container_width=True):
            st.session_state["lang"] = st.session_state.get("lang_select", "en")
            st.rerun()

    # 登录 / 注册 切换
    mode = st.radio("", [t("sign_in"), t("create_account")], horizontal=True, index=0)

    if mode == t("sign_in"):
        # —— 登录表单：按 Enter 即提交 ——
        with st.form("signin_form", clear_on_submit=False):
            u = st.text_input(t("username"), key="signin_username")
            p = st.text_input(t("password"), type="password", key="signin_password")
            submit_login = st.form_submit_button(t("sign_in"))
        if submit_login:
            user = svc.authenticate(u, p)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error(t("sign_in_failed"))

    else:
        # —— 注册表单：按 Enter 即提交 ——
        display_to_role = {
            t("role_admin"): "Admin",
            t("role_auditor"): "Auditor",
            t("role_nurse"): "Nurse",
            t("role_doctor"): "Doctor",
            t("role_patient"): "Patient",
        }
        with st.form("signup_form", clear_on_submit=False):
            ru  = st.text_input(t("username"), key="signup_username")
            rp  = st.text_input(t("password"), type="password", key="signup_password")
            rp2 = st.text_input(t("confirm_password"), type="password", key="signup_password2")
            role_pick = st.selectbox(t("account_type"), list(display_to_role.keys()), key="signup_role")
            submit_signup = st.form_submit_button(t("create_account"))
        if submit_signup:
            try:
                if rp != rp2:
                    st.error("Passwords do not match." if st.session_state.get("lang","en")=="en" else "两次密码不一致。")
                else:
                    created = svc.self_register(ru, rp, display_to_role[role_pick])
                    st.success(t("account_created_signing_in"))
                    st.session_state["user"] = created
                    st.rerun()
            except Exception as e:
                st.error(str(e))

def navbar():
    # 从 session 中获取角色，供后续使用
    role = st.session_state['user']['role']
    username = st.session_state['user']['username']

    # 获取服务实例
    svc = get_service()

    # 折叠的"工具"与账号区（默认收起）
    with st.sidebar.expander(t("tools"), expanded=False):
        # 用户名信息
        st.markdown(f"**{t('username')}：**{username}")
        # 角色信息
        st.markdown(f"**{t('role')}：**{role_display(role)}")

        # 如果是病人角色，显示病人ID和姓名
        if role == "Patient":
            patient_info = svc.get_patient_info_for_user(username)
            if patient_info:
                st.markdown(f"**{t('patient_id')}：**{patient_info['id']}")
                st.markdown(f"**{t('patient_name')}：**{patient_info['name']}")
            else:
                st.info(t("no_patient_record_linked"))

        # 退出按钮
        if st.button(t("sign_out"), use_container_width=True, key="btn_logout"):
            # 清理登录状态并重载
            if "user" in st.session_state:
                del st.session_state["user"]
            st.rerun()

        # 工具按钮（两列）
        c1, c2 = st.columns(2)
        if c1.button(t("toolbar_rerun"), use_container_width=True, key="btn_rerun"):
            st.rerun()
        if c2.button(t("toolbar_clear_cache"), use_container_width=True, key="btn_clear"):
            try:
                st.cache_data.clear()
            except Exception:
                pass
            try:
                st.cache_resource.clear()
            except Exception:
                pass
            st.rerun()

    all_keys = {
        "patients": t("patients"),
        "observations": t("observations"),
        "stories": t("stories"),
        "handover": t("handover"),
        "preferences": t("preferences"),
        "search": t("search"),
        "report": t("report"),
        "auditor": t("auditor"),
        "backup_restore": t("backup_restore"),
        "admin_panel": t("admin_panel"),
    }

    visible = []
    if role in ("Admin","Nurse","Doctor"):
        visible += ["patients","observations","stories","handover"]

    # 病人角色显示偏好和报告
    if role == "Patient":
        visible += ["preferences","report"]
    # 其他角色（护士、医生、审计员、管理员）显示搜索和报告，不显示偏好
    else:
        visible += ["search","report"]

    if role in ("Auditor","Admin"):
        visible += ["auditor"]
    if role == "Admin":
        visible += ["backup_restore","admin_panel"]

    page_key = st.sidebar.radio(t("menu"), visible, format_func=lambda k: all_keys[k])
    return page_key

def main():
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    inject_a11y_css()
    hide_streamlit_chrome()       # 调用新的 CSS 函数
    svc = get_service()
    if "user" not in st.session_state:
        login_view(svc)
        return

    page = navbar()
    user = st.session_state["user"]

    # 如果是病人角色，在主界面顶部显示病人信息
    if user["role"] == "Patient":
        patient_info = svc.get_patient_info_for_user(user["username"])
        if patient_info:
            st.info(f"**{t('patient_id')}:** {patient_info['id']} | **{t('patient_name')}:** {patient_info['name']}")
        else:
            st.warning(t("no_patient_record_linked"))

    if page == "patients":
        patients_page(svc, user)
    elif page == "observations":
        observations_page(svc, user)
    elif page == "stories":
        stories_page(svc, user)
    elif page == "handover":
        handover_page(svc, user)
    elif page == "preferences":
        preferences_page(svc, user)
    elif page == "search":
        search_page(svc, user)
    elif page == "report":
        report_page(svc, user)
    elif page == "auditor":
        auditor_page(svc)
    elif page == "backup_restore":
        backup_page(svc, user)
    elif page == "admin_panel":
        admin_panel(svc, user)