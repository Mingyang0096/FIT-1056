# tests/test_schedule_manager.py
import os
import csv
import json
import tempfile
from app.schedule import ScheduleManager

def make_manager(tmpdir):
    # 明文模式，指向一个临时路径，避免影响真实数据
    data_path = os.path.join(tmpdir, "msms.json")
    return ScheduleManager(data_path=data_path, enc_manager=None)

def test_add_and_persist_student_teacher_course():
    with tempfile.TemporaryDirectory() as td:
        m = make_manager(td)
        m.add_student("Alice")
        m.add_teacher("Bob", "Piano")
        m.add_course("Piano 101", "Piano", 1)

        # 基本断言
        assert len(m.students) == 1
        assert len(m.teachers) == 1
        assert len(m.courses)  == 1

        # 重建 manager 验证持久化
        data_path = m.data_path
        m2 = ScheduleManager(data_path=data_path, enc_manager=None)
        assert len(m2.students) == 1
        assert len(m2.teachers) == 1
        assert len(m2.courses)  == 1
        assert m2.students[0].name == "Alice"
        assert m2.teachers[0].name == "Bob"
        assert m2.courses[0].name  == "Piano 101"

def test_enrol_attendance_payment_and_reports():
    with tempfile.TemporaryDirectory() as td:
        m = make_manager(td)
        m.add_student("Charlie")
        m.add_teacher("Dora", "Guitar")
        m.add_course("Guitar 101", "Guitar", 1)

        # 选课
        assert m.enrol_student_in_course(1, 1) is True
        # 出勤
        assert m.check_in(1, 1) is True
        att = m.get_attendance_by_student(1)
        assert isinstance(att, list) and len(att) == 1

        # 支付
        m.record_payment(1, 120.0, "Cash")
        hist = m.get_payment_history(1)
        assert len(hist) == 1 and hist[0]["amount"] == 120.0

        # 导出报表（CSV）
        fin_csv = os.path.join(td, "finance.csv")
        att_csv = os.path.join(td, "attendance.csv")
        m.export_report("finance", fin_csv)
        m.export_report("attendance", att_csv)

        # 简单校验 CSV 头与行数
        with open(fin_csv, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            assert rows and set(rows[0].keys()) == {"student_id", "amount", "method", "timestamp"}

        with open(att_csv, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            assert rows and set(rows[0].keys()) == {"student_id", "course_id", "timestamp"}

def test_safe_defaults_when_file_missing_or_empty():
    with tempfile.TemporaryDirectory() as td:
        # 构造一个空文件，验证不会崩溃
        path = os.path.join(td, "msms.json")
        open(path, "w", encoding="utf-8").close()
        m = ScheduleManager(data_path=path, enc_manager=None)
        assert m.list_students() == []
        assert m.list_teachers() == []
        assert m.list_courses()  == []
