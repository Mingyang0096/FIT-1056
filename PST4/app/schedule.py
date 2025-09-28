import os
import json
import datetime
from app.student import StudentUser
from app.teacher import TeacherUser, Course

class ScheduleManager:
    """
    Central controller for managing students, teachers, courses, and attendance.
    Handles CRUD operations, enrolment logic, and persistent JSON storage.
    Maintains ID counters to ensure unique identifiers across entities.
    Designed for integration with CLI or other front-end interfaces.
    """

    def __init__(self, data_path="data/msms.json"):
        self.data_path = data_path
        self.students, self.teachers, self.courses, self.attendance_log = [], [], [], []
        self.next_student_id = self.next_teacher_id = self.next_course_id = 1
        self._load_data()

    # ===== Internal Helpers =====
    def _load_data(self):
        """Load data from JSON file into memory. Create file if it does not exist."""
        if not os.path.exists(self.data_path):
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            # Create an empty default data structure
            empty_data = {
                "students": [],
                "teachers": [],
                "courses": [],
                "attendance": [],
                "next_student_id": 1,
                "next_teacher_id": 1,
                "next_course_id": 1
            }
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, indent=4, ensure_ascii=False)
            return  # No data to load yet

        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.students = [StudentUser.from_dict(s) for s in data.get("students", [])]
        self.teachers = [TeacherUser.from_dict(t) for t in data.get("teachers", [])]
        self.courses = [Course.from_dict(c) for c in data.get("courses", [])]
        self.attendance_log = data.get("attendance", [])
        self.next_student_id = data.get("next_student_id", 1)
        self.next_teacher_id = data.get("next_teacher_id", 1)
        self.next_course_id = data.get("next_course_id", 1)

    def _save_data(self):
        """Save in-memory data back to JSON file."""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        data = {
            "students": [s.to_dict() for s in self.students],
            "teachers": [t.to_dict() for t in self.teachers],
            "courses": [c.to_dict() for c in self.courses],
            "attendance": self.attendance_log,
            "next_student_id": self.next_student_id,
            "next_teacher_id": self.next_teacher_id,
            "next_course_id": self.next_course_id
        }
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _find(self, collection, _id):
        """Find object by ID in a given collection."""
        return next((obj for obj in collection if str(obj.id) == str(_id)), None)

    def find_student_by_id(self, student_id): return self._find(self.students, student_id)
    def find_teacher_by_id(self, teacher_id): return self._find(self.teachers, teacher_id)
    def find_course_by_id(self, course_id): return self._find(self.courses, course_id)

    # ===== Student Management =====
    def add_student(self, name, enrolled_course_ids=None):
        self.students.append(StudentUser(self.next_student_id, name, enrolled_course_ids or []))
        self.next_student_id += 1
        self._save_data()

    def remove_student(self, student_id):
        student = self.find_student_by_id(student_id)
        if not student: return False
        for c in self.courses:
            if student_id in c.enrolled_student_ids:
                c.enrolled_student_ids.remove(student_id)
        self.students = [s for s in self.students if s.id != student_id]
        self._save_data()
        return True

    def list_students(self):
        return [{"id": s.id, "name": s.name, "courses": len(s.enrolled_course_ids)} for s in self.students]

    def find_students_by_name(self, name):
        return [s for s in self.students if name.lower() in s.name.lower()]

    # ===== Teacher Management =====
    def add_teacher(self, name, speciality):
        self.teachers.append(TeacherUser(self.next_teacher_id, name, speciality))
        self.next_teacher_id += 1
        self._save_data()

    def remove_teacher(self, teacher_id):
        teacher = self.find_teacher_by_id(teacher_id)
        if not teacher: return False
        for c in self.courses:
            if c.teacher_id == teacher_id:
                c.teacher_id = None
        self.teachers = [t for t in self.teachers if t.id != teacher_id]
        self._save_data()
        return True

    def list_teachers(self):
        return [{"id": t.id, "name": t.name, "speciality": t.speciality} for t in self.teachers]

    def find_teachers_by_name_or_speciality(self, keyword):
        return [t for t in self.teachers if keyword.lower() in t.name.lower() or keyword.lower() in t.speciality.lower()]

    # ===== Course Management =====
    def add_course(self, name, instrument, teacher_id):
        self.courses.append(Course(self.next_course_id, name, instrument, teacher_id))
        self.next_course_id += 1
        self._save_data()

    def remove_course(self, course_id):
        course = self.find_course_by_id(course_id)
        if not course: return False
        for s in self.students:
            if course_id in s.enrolled_course_ids:
                s.enrolled_course_ids.remove(course_id)
        self.courses = [c for c in self.courses if c.id != course_id]
        self._save_data()
        return True

    def list_courses(self):
        return [{"id": c.id, "name": c.name, "instrument": c.instrument, "teacher_id": c.teacher_id} for c in self.courses]

    def enrol_student_in_course(self, student_id, course_id):
        s, c = self.find_student_by_id(student_id), self.find_course_by_id(course_id)
        if not s or not c: return False
        if student_id not in c.enrolled_student_ids: c.enrolled_student_ids.append(student_id)
        if course_id not in s.enrolled_course_ids: s.enrolled_course_ids.append(course_id)
        self._save_data()
        return True

    def unenrol_student_from_course(self, student_id, course_id):
        s, c = self.find_student_by_id(student_id), self.find_course_by_id(course_id)
        if not s or not c: return False
        if student_id in c.enrolled_student_ids: c.enrolled_student_ids.remove(student_id)
        if course_id in s.enrolled_course_ids: s.enrolled_course_ids.remove(course_id)
        self._save_data()
        return True

    def switch_student_course(self, student_id, from_course_id, to_course_id):
        if not self.unenrol_student_from_course(student_id, from_course_id): return False
        return self.enrol_student_in_course(student_id, to_course_id)

    # ===== Attendance =====
    def check_in(self, student_id, course_id):
        if not self.find_student_by_id(student_id) or not self.find_course_by_id(course_id):
            return False
        self.attendance_log.append({
            "student_id": student_id,
            "course_id": course_id,
            "timestamp": datetime.datetime.now().isoformat()
        })
        self._save_data()
        return True

    def get_attendance_by_student(self, student_id):
        return [r for r in self.attendance_log if str(r.get("student_id")) == str(student_id)]

    def get_attendance_by_course(self, course_id):
        return [r for r in self.attendance_log if str(r.get("course_id")) == str(course_id)]

    # ===== Schedule =====
    def get_lessons_by_day(self, day):
        """Return lessons scheduled for a given day."""
        lessons = []
        for course in self.courses:
            for lesson in getattr(course, "lessons", []):
                if lesson.get("day", "").lower() == day.lower():
                    teacher = self.find_teacher_by_id(course.teacher_id)
                    student_names = [
                        self.find_student_by_id(sid).name
                        for sid in course.enrolled_student_ids
                        if self.find_student_by_id(sid)
                    ]
                    lessons.append({
                        "course_id": course.id,
                        "course_name": course.name,
                        "teacher": teacher.name if teacher else "Unknown",
                        "students": student_names
                    })
        return lessons

    # ===== Data Maintenance =====
    def reset_data(self):
        """Clear all data and reset ID counters."""
        self.students.clear()
        self.teachers.clear()
        self.courses.clear()
        self.attendance_log.clear()
        self.next_student_id = self.next_teacher_id = self.next_course_id = 1
