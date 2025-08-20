Here is a plain text README for your uploaded program with only newline and tab formatting.

Music School Management System (MSMS)

1	Overview
The Music School Management System is a Python-based command line application for managing student, teacher, enrollment, and attendance data in a music school. It uses JSON files for persistent storage and provides an interactive menu for CRUD operations.

2	Main Features
- Persistent data storage using JSON files
- Student management
	- Register new students with unique IDs
	- Add instruments for existing students
	- List all students
	- Remove students
	- Print student ID card to a text file
- Teacher management
	- Add new teachers with specialities
	- List all teachers
	- Search teachers by name or speciality
- Attendance management
	- Check in students with a timestamp and course ID
- Search functions
	- Search students by name
	- Search teachers by name or speciality
- File handling
	- Load existing JSON data files
	- Create and initialize new data files

3	Requirements
- Python 3.7 or higher
- Standard library only (os, json, time)
- Works on Windows, macOS, and Linux

4	How to Run
1. Open a terminal and navigate to the project directory
2. Run the program
	python PST2.py
3. When prompted, enter the full path to an existing JSON data file or choose to create a new one

5	Menu Options
===== MSMS v2 (Persistent) =====
1	Register New Student
2	Enrol Existing Student
3	Lookup Student or Teacher
4	(Admin) List all Students
5	(Admin) List all Teachers
6	Check-in Student
7	Print Student Card
8	Remove Student
9	Restart
q	Quit

6	Example JSON Data Structure
{
	"students": [
		{
			"id": 1,
			"name": "Alice",
			"enrolled_in": ["Piano", "Violin"]
		}
	],
	"teachers": [
		{
			"id": 1,
			"name": "Mr. Smith",
			"speciality": "Piano"
		}
	],
	"attendance": [
		{
			"student_id": 1,
			"course_id": 101,
			"timestamp": "2025-08-15 10:30"
		}
	],
	"next_student_id": 2,
	"next_teacher_id": 2
}

7	Defensive Programming Notes
- The program handles missing files by prompting to create a new one
- It is recommended to check that file paths point to actual files before calling open
- Only provide complete file paths including the file name and extension

8	Important Notes
- Enter valid file paths including the file name and extension when loading data
- Printed student cards are saved to a chosen folder as plain text
- Deleted student records cannot be recovered without manually editing the JSON data