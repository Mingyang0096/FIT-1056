import os, json, datetime, logging, csv
from typing import Optional, List, Dict, Any
from app.student import StudentUser
from app.teacher import TeacherUser, Course
from app.security import EncryptionManager

# --------- 默认空数据 ---------
_DEFAULT = {
    "students": [],
    "teachers": [],
    "courses": [],
    "attendance": [],
    "finance": [],
    "next_student_id": 1,
    "next_teacher_id": 1,
    "next_course_id": 1
}

class ScheduleManager:
    """
    Business layer: students/teachers/courses/attendance/finance with (optional) encrypted persistence.

    公共接口（与现有 UI 兼容）：
      - list_students() / list_teachers() / list_courses()
      - add_student(name), add_teacher(name, speciality), add_course(name, instrument, teacher_id)
      - remove_student/teacher/course
      - enrol_student_in_course(student_id, course_id) / unenrol_student_from_course(student_id, course_id)
      - check_in(student_id, course_id)
      - get_attendance_by_student(student_id) / get_attendance_by_course(course_id)
      - record_payment(student_id, amount, method) / get_payment_history(student_id) / export_report(kind, out_path)
      - find_*_by_id
    """

    def __init__(
        self,
        data_path: str = "data/msms.json",                # ← 默认改为明文路径，避免误读 .enc
        enc_manager: Optional[EncryptionManager] = None   # 传入则启用加密
    ):
        self.data_path = data_path
        self.enc = enc_manager

        self.students: List[StudentUser] = []
        self.teachers: List[TeacherUser] = []
        self.courses:  List[Course] = []
        self.attendance_log: List[Dict[str, Any]] = []
        self.finance_log: List[Dict[str, Any]] = []
        self.next_student_id = self.next_teacher_id = self.next_course_id = 1

        self._load_data()

    # ---------- persistence ----------
    def _read_store(self) -> Dict[str, Any]:
        """
        读取数据文件：
        - enc_manager 存在 → 走加密读（支持首次从旧明文迁移）。
        - enc_manager 不存在 → 走明文读；空文件/损坏/密文误读 → 回退默认结构并写回。
        """
        # 加密模式
        if self.enc:
            data = self.enc.read_json(self.data_path, default=_DEFAULT.copy())

            # 一次性迁移：若 .enc 不存在而旧明文存在，则迁移写入密文
            if (not os.path.exists(self.data_path)):
                # 推断可能的旧明文文件（常用名）
                candidates = ["data/msms.json"]
                for old_plain in candidates:
                    if os.path.exists(old_plain):
                        try:
                            with open(old_plain, "r", encoding="utf-8") as f:
                                plain = json.load(f)
                            # 补齐 finance 字段
                            if "finance" not in plain:
                                plain["finance"] = []
                            self.enc.write_json(self.data_path, plain)
                            logging.info(f"Migrated plaintext {old_plain} -> encrypted {self.data_path}")
                            data = plain
                            break
                        except Exception as e:
                            logging.warning(f"Migration read failed from {old_plain}: {e}")
            # 数据有效性兜底
            if not isinstance(data, dict):
                logging.warning("Encrypted store invalid; falling back to default.")
                return _DEFAULT.copy()
            for k in _DEFAULT.keys():
                data.setdefault(k, _DEFAULT[k])
            return data

        # 明文模式
        if not os.path.exists(self.data_path):
            return _DEFAULT.copy()

        # 读明文：空文件/损坏/密文误读 → 兜底
        try:
            if os.path.getsize(self.data_path) == 0:
                logging.warning(f"Empty store file at {self.data_path}; using defaults.")
                return _DEFAULT.copy()
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logging.warning(f"Failed to read plaintext JSON at {self.data_path}: {e}; using defaults.")
            return _DEFAULT.copy()

        # 数据结构兜底
        if not isinstance(data, dict):
            logging.warning("Plain store invalid; falling back to default.")
            return _DEFAULT.copy()
        for k in _DEFAULT.keys():
            data.setdefault(k, _DEFAULT[k])
        return data

    def _write_store(self, obj: Dict[str, Any]) -> None:
        """根据是否有 enc_manager 决定加密或明文写回。"""
        if self.enc:
            # 加密写
            self.enc.write_json(self.data_path, obj)
            return

        # 明文写
        os.makedirs(os.path.dirname(self.data_path) or ".", exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=4, ensure_ascii=False)

    def _load_data(self) -> None:
        data = self._read_store()

        # 反序列化对象
        try:
            self.students = [StudentUser.from_dict(s) for s in data.get("students", [])]
            self.teachers = [TeacherUser.from_dict(t) for t in data.get("teachers", [])]
            self.courses  = [Course.from_dict(c) for c in data.get("courses", [])]
        except Exception as e:
            logging.error(f"Deserialization error; resetting to defaults: {e}")
            data = _DEFAULT.copy()
            self.students, self.teachers, self.courses = [], [], []

        self.attendance_log = data.get("attendance", [])
        self.finance_log    = data.get("finance", [])
        self.next_student_id = data.get("next_student_id", 1)
        self.next_teacher_id = data.get("next_teacher_id", 1)
        self.next_course_id  = data.get("next_course_id", 1)

        # 如读到的是默认且文件此前存在损坏，顺手写回干净结构，避免以后再报错
        try:
            self._save_data()
        except Exception as e:
            logging.warning(f"Save after load (healing) failed: {e}")

    def _save_data(self) -> None:
        data = {
            "students": [s.to_dict() for s in self.students],
            "teachers": [t.to_dict() for t in self.teachers],
            "courses":  [c.to_dict() for c in self.courses],
            "attendance": list(self.attendance_log),
            "finance":    list(self.finance_log),
            "next_student_id": self.next_student_id,
            "next_teacher_id": self.next_teacher_id,
            "next_course_id": self.next_course_id
        }
        self._write_store(data)

    # ---------- creation / deletion ----------
    def add_student(self, name, enrolled_course_ids=None):
        self.students.append(StudentUser(self.next_student_id, name, enrolled_course_ids or []))
        self.next_student_id += 1
        self._save_data()
        logging.info(f"Student added: name={name}")

    def remove_student(self, student_id):
        student = self.find_student_by_id(student_id)
        if not student:
            return False
        for c in self.courses:
            if student_id in c.enrolled_student_ids:
                c.enrolled_student_ids.remove(student_id)
        self.students = [s for s in self.students if s.id != student_id]
        self._save_data()
        logging.info(f"Student removed: id={student_id}")
        return True

    def add_teacher(self, name, speciality):
        self.teachers.append(TeacherUser(self.next_teacher_id, name, speciality))
        self.next_teacher_id += 1
        self._save_data()
        logging.info(f"Teacher added: name={name}, speciality={speciality}")

    def remove_teacher(self, teacher_id):
        t = self.find_teacher_by_id(teacher_id)
        if not t:
            return False
        for c in self.courses:
            if c.teacher_id == teacher_id:
                c.teacher_id = None
        self.teachers = [x for x in self.teachers if x.id != teacher_id]
        self._save_data()
        logging.info(f"Teacher removed: id={teacher_id}")
        return True

    def add_course(self, name, instrument, teacher_id):
        self.courses.append(Course(self.next_course_id, name, teacher_id, instrument))
        self.next_course_id += 1
        self._save_data()
        logging.info(f"Course added: name={name}, instrument={instrument}, teacher_id={teacher_id}")

    def remove_course(self, course_id):
        c = self.find_course_by_id(course_id)
        if not c:
            return False
        for s in self.students:
            if course_id in s.enrolled_course_ids:
                s.enrolled_course_ids.remove(course_id)
        self.courses = [x for x in self.courses if x.id != course_id]
        self._save_data()
        logging.info(f"Course removed: id={course_id}")
        return True

    # ---------- enrolments ----------
    def enrol_student_in_course(self, student_id, course_id):
        s, c = self.find_student_by_id(student_id), self.find_course_by_id(course_id)
        if not s or not c:
            return False
        if student_id not in c.enrolled_student_ids:
            c.enrolled_student_ids.append(student_id)
        if course_id not in s.enrolled_course_ids:
            s.enrolled_course_ids.append(course_id)
        self._save_data()
        logging.info(f"Enrolment: student_id={student_id} -> course_id={course_id}")
        return True

    def unenrol_student_from_course(self, student_id, course_id):
        s, c = self.find_student_by_id(student_id), self.find_course_by_id(course_id)
        if not s or not c:
            return False
        if student_id in c.enrolled_student_ids:
            c.enrolled_student_ids.remove(student_id)
        if course_id in s.enrolled_course_ids:
            s.enrolled_course_ids.remove(course_id)
        self._save_data()
        logging.info(f"Unenrol: student_id={student_id} -/-> course_id={course_id}")
        return True

    # ---------- attendance ----------
    def check_in(self, student_id, course_id):
        if not self.find_student_by_id(student_id) or not self.find_course_by_id(course_id):
            return False
        self.attendance_log.append({
            "student_id": student_id,
            "course_id": course_id,
            "timestamp": datetime.datetime.now().isoformat()
        })
        self._save_data()
        logging.info(f"Check-in: student_id={student_id}, course_id={course_id}")
        return True

    def get_attendance_by_student(self, student_id):
        return [rec for rec in self.attendance_log if str(rec.get("student_id")) == str(student_id)]

    def get_attendance_by_course(self, course_id):
        return [rec for rec in self.attendance_log if str(rec.get("course_id")) == str(course_id)]

    # ---------- finance ----------
    def record_payment(self, student_id, amount, method):
        """Add a payment record. amount: float convertible; method: str."""
        if not any(s.id == student_id for s in self.students):
            raise ValueError(f"Student id {student_id} does not exist.")
        try:
            amt = float(amount)
        except Exception:
            raise ValueError("Amount must be a number.")
        if amt < 0:
            raise ValueError("Amount cannot be negative.")
        record = {
            "student_id": student_id,
            "amount": amt,
            "method": str(method),
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.finance_log.append(record)
        self._save_data()
        logging.info(f"Payment recorded: student_id={student_id}, amount={amt}, method={method}")

    def get_payment_history(self, student_id):
        return [p for p in self.finance_log if str(p.get('student_id')) == str(student_id)]

    def export_report(self, kind, out_path):
        """Export 'finance' or 'attendance' log into CSV file."""
        if kind == "finance":
            data_to_export = self.finance_log
            headers = ["student_id", "amount", "method", "timestamp"]
        elif kind == "attendance":
            data_to_export = self.attendance_log
            headers = ["student_id", "course_id", "timestamp"]
        else:
            raise ValueError("Unknown report type. Use 'finance' or 'attendance'.")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in data_to_export:
                writer.writerow({h: row.get(h, "") for h in headers})
        logging.info(f"Report exported: kind={kind}, path={out_path}")

    # ---------- listing helpers used by UI ----------
    def list_students(self):
        out = []
        for s in self.students:
            sid = getattr(s, "id", None)
            name = getattr(s, "name", "")
            enrolled = getattr(s, "enrolled_course_ids", []) or []
            out.append({"id": sid, "name": name, "courses": len(enrolled)})
        return out

    def list_teachers(self):
        out = []
        for t in self.teachers:
            tid = getattr(t, "id", None)
            name = getattr(t, "name", "")
            spec = getattr(t, "speciality", "")
            out.append({"id": tid, "name": name, "speciality": spec})
        return out

    def list_courses(self):
        out = []
        for c in self.courses:
            cid = getattr(c, "id", None)
            name = getattr(c, "name", "")
            instr = getattr(c, "instrument", "")
            tid = getattr(c, "teacher_id", None)
            out.append({"id": cid, "name": name, "instrument": instr, "teacher_id": tid})
        return out

    # ---------- find helpers ----------
    def _find(self, coll, _id):
        return next((o for o in coll if str(o.id) == str(_id)), None)

    def find_student_by_id(self, sid): return self._find(self.students, sid)
    def find_teacher_by_id(self, tid): return self._find(self.teachers, tid)
    def find_course_by_id(self, cid):  return self._find(self.courses, cid)

    # ---------- optional searches ----------
    def find_students_by_name(self, name_substr: str):
        s = (name_substr or "").lower()
        return [x for x in self.students if s in (x.name or "").lower()]

    def find_teachers_by_name_or_speciality(self, keyword: str):
        k = (keyword or "").lower()
        return [x for x in self.teachers if k in (x.name or "").lower() or k in (x.speciality or "").lower()]
