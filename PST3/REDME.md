School Management System

Overview
This is a modular, object-oriented school management system implemented in Python. It manages students, teachers, courses, and attendance records with persistent storage using JSON files and provides a command-line interface for user interaction.

Features
- Add, update, and delete students and teachers
- Create and manage courses
- Enroll students in courses
- Record and view attendance
- Search for students and teachers by name or speciality
- View summarized tables of all entities
- Persistent data storage in JSON format
- Modular design with separation of concerns

Project Structure
- main.py: Command-line interface entry point
- schedule.py: Core controller managing business logic and data operations
- student.py: StudentUser class definition
- teacher.py: TeacherUser and Course class definitions
- user.py: Base User class definition
- data/: Directory containing JSON data files (students.json, teachers.json, courses.json, attendance.json)

Getting Started
Requirements:
- Python 3.7 or higher
- No external dependencies besides standard Python libraries

Running the program:
Execute `python main.py` from the command line. Follow the menu prompts to interact with the system.

Data Persistence
All data is saved in the data directory as JSON files:
- Students, teachers, courses, and attendance logs are stored separately.
- Attendance records are intentionally retained even after deletion of students or courses to preserve historical data.

Data Consistency
- The ScheduleManager class serves as the single point of modification for all data, ensuring consistency.
- Unique IDs link students, teachers, and courses to maintain relationships.
- All CRUD operations are routed through ScheduleManager to avoid conflicts.
- Attendance data is preserved independently from active student or course lists.

Module Descriptions
- User: Base class providing common attributes and validation for users.
- StudentUser: Extends User with course enrollment tracking.
- TeacherUser: Extends User with speciality and assigned course management.
- Course: Represents a course including enrolled students and assigned teacher.
- ScheduleManager: Manages all CRUD operations and attendance logging.

Notes
- This system emphasizes retention of attendance history.
- Input validation is minimal and assumes cooperative user inputs.
- No networking or database is involved; all operations are local.

Potential Future Enhancements
- Batch import/export support via CSV
- Automated unit tests for robustness
- Graphical user interface development
- Role-based access controls


-----challenges and solutions-----
During development, several issues were encountered and resolved.

1. property 'id' of 'StudentUser' object has no setter Cause: Subclass defined a read‑only id property overriding the base class attribute. Fix: Removed the @property id in subclass or added a setter; unified to use self.id.

2. 'StudentUser' object has no attribute 'user_id' Cause: Methods accessed self.user_id while base class only defined self.id. Fix: Added self.user_id = user_id in constructor or replaced with self.id.

3. Enrol Existing Student → Enrolment failed Cause: The course ID entered did not exist in the system. Fix: Verify course existence via “List Courses” or add the course before enrolment.

4. Course.__init__() takes 4 positional arguments but 5 were given Cause: instrument argument passed but not defined in Course.__init__. Fix: Added instrument parameter to Course class or removed it from call.

5. JSON file missing on first run Cause: Program attempted to load a non‑existent file. Fix: _load_data now creates an empty default JSON file if missing.

6. Long stack trace on Ctrl+C Cause: KeyboardInterrupt in debug mode prints full call stack. Fix: Catch KeyboardInterrupt in main() and exit gracefully.

7. Name validation failed after switching to relative path Cause: New JSON file loaded contained teacher names with punctuation (e.g., Dr.). Fix: Cleaned JSON names or relaxed regex to allow more characters.

8. JSON teacher names with invalid characters Cause: Regex in User class only allowed letters and spaces. Fix: Updated JSON to remove invalid characters or adjusted regex to permit them.