import os
from app.user import User

class StudentUser(User):
    """Represents a student user with enrolled course tracking."""

    def __init__(self, user_id, name, enrolled_course_ids=None):
        # Call parent constructor to validate and set name/id
        super().__init__(user_id, name)

        # Ensure both id and user_id exist for compatibility
        self.user_id = user_id  

        # Initialize enrolled courses
        self.enrolled_course_ids = list(enrolled_course_ids) if enrolled_course_ids else []

    def enroll_course(self, course_id):
        """Enroll the student in a course if not already enrolled."""
        if course_id not in self.enrolled_course_ids:
            self.enrolled_course_ids.append(course_id)

    def drop_course(self, course_id):
        """Remove a course from the student's enrollment list."""
        if course_id in self.enrolled_course_ids:
            self.enrolled_course_ids.remove(course_id)

    def update_name(self, new_name):
        """Update the student's name using the same validation as User."""
        super().update_name(new_name)

    def to_dict(self):
        """Serialize the student to a dictionary for JSON storage."""
        return {
            "user_id": self.user_id, 
            "name": self.name,
            "enrolled_course_ids": self.enrolled_course_ids
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize a student from a dictionary."""
        uid = data.get("user_id", data.get("id"))
        name = data.get("name", "")
        enrolled = data.get("enrolled_course_ids", [])
        return cls(uid, name, enrolled)

    def to_table(self):
        """Return student data as a list for table display."""
        return [
            self.user_id,
            self.name,
            ", ".join(map(str, self.enrolled_course_ids)) if self.enrolled_course_ids else "-"
        ]

    def save_card(self, folder, enrolled_display=None, filename=None):
        """Save a simple text ID card to the specified folder and return the file path.
        enrolled_display: list of course names to show (optional).
        filename: override filename (optional).
        """
        import os as _os
        from datetime import datetime as _dt
        _os.makedirs(folder, exist_ok=True)
        if not filename:
            filename = f"student_{self.id}_card.txt"
        path = _os.path.join(folder, filename)
        lines = [
            "MSMS Student ID Card",
            f"ID: {self.id}",
            f"Name: {self.name}",
            "Courses: " + (", ".join(enrolled_display) if enrolled_display else "-"),
            f"Generated: {_dt.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path
