import re
import time
from app.user import User

class TeacherUser(User):
    """
    Represents a teacher in the system, extending the base User class.
    Tracks speciality, assigned courses, and last update timestamp.
    Provides safe update methods with validation and timestamp refresh.
    Designed for easy serialization and table-friendly output.
    """
    def __init__(self, teacher_id, name, speciality):
        # Call parent constructor for ID/name validation
        super().__init__(teacher_id, name)
        self.speciality = speciality
        self.course_ids = []  # Stores assigned course IDs
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")  # Initial timestamp

    def assign_course(self, course_id):
        """Assign a course if not already assigned."""
        if course_id not in self.course_ids:
            self.course_ids.append(course_id)
            self._update_timestamp()

    def remove_course(self, course_id):
        """Remove a course if currently assigned."""
        if course_id in self.course_ids:
            self.course_ids.remove(course_id)
            self._update_timestamp()

    def update_name(self, new_name):
        """Update name with regex validation before saving."""
        if not re.match(r"^[A-Za-z\s]+$", new_name):
            raise ValueError("Name must contain only letters and spaces.")
        super().update_name(new_name)
        self._update_timestamp()

    def update_speciality(self, new_speciality):
        """Update speciality; must be non-empty."""
        if not new_speciality.strip():
            raise ValueError("Speciality cannot be empty.")
        self.speciality = new_speciality
        self._update_timestamp()

    def _update_timestamp(self):
        """Refresh last_updated to current time."""
        self.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        """Serialize teacher data for storage or transfer."""
        return {
            "id": self.id,
            "name": self.name,
            "speciality": self.speciality,
            "course_ids": self.course_ids,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild TeacherUser from a dictionary."""
        teacher = cls(data["id"], data["name"], data["speciality"])
        teacher.course_ids = data.get("course_ids", [])
        teacher.last_updated = data.get("last_updated", time.strftime("%Y-%m-%d %H:%M:%S"))
        return teacher

    def to_table(self):
        """Return teacher data as a list for tabular display."""
        return [
            self.id,
            self.name,
            self.speciality,
            ", ".join(self.course_ids) if self.course_ids else "-",
            self.last_updated
        ]


class Course:
    """
    Represents a course with an assigned teacher and enrolled students.
    Supports student enrollment/removal and optional instrument info.
    Provides serialization for storage and table-friendly output.
    Keeps enrolled students as a simple in-memory list.
    """
    def __init__(self, course_id, name, teacher_id, instrument=None):
        self.id = course_id
        self.name = name
        self.teacher_id = teacher_id
        self.enrolled_student_ids = []  # Tracks enrolled student IDs
        self.instrument = instrument

    def enroll_student(self, student_id):
        """Add a student if not already enrolled."""
        if student_id not in self.enrolled_student_ids:
            self.enrolled_student_ids.append(student_id)

    def remove_student(self, student_id):
        """Remove a student if currently enrolled."""
        if student_id in self.enrolled_student_ids:
            self.enrolled_student_ids.remove(student_id)

    def to_dict(self):
        """Serialize course data for storage or transfer."""
        return {
            "id": self.id,
            "name": self.name,
            "teacher_id": self.teacher_id,
            "enrolled_student_ids": self.enrolled_student_ids
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild Course from a dictionary."""
        course = cls(data["id"], data["name"], data["teacher_id"])
        course.enrolled_student_ids = data.get("enrolled_student_ids", [])
        return course

    def to_table(self):
        """Return course data as a list for tabular display."""
        return [
            self.id,
            self.name,
            self.teacher_id,
            ", ".join(self.enrolled_student_ids) if self.enrolled_student_ids else "-"
        ]
