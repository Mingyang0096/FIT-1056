 Music School Management System (MSMS) — PST1 Prototype

This is a prototype project for FIT1056 PST1, developed in Python. It manages student registration, teacher data, course enrolment, and information lookup through a menu-driven interface. All data is stored in memory, with no need for file or database operations.

Project Features:

Models for Student and Teacher using Python classes
In-memory databases: student_db and teacher_db with auto-generated IDs
Core functions: add teachers, list students/teachers, search by name or speciality
Front desk features: register student, enrol in course, look up student/teacher info
Simple command-line interaction with user-friendly prompts and basic error handling

How to Run:

Open a Python 3 environment
Run the command: python MSMS.py
Follow on-screen menu instructions to interact

File Structure:
MSMS.py: main program with all code
README.md: project documentation (this file)

Design Notes:

Data stored in dictionaries inside lists, making it easy to manage and display
Global counters used to generate unique IDs
Lookup uses string matching by name or speciality
CLI interface uses input and sleep for smoother interaction

Assumptions: each student can enrol in multiple courses; teacher names are not required to be unique


Common Issues & Suggestions:

Search by teacher speciality is case-sensitive — consider normalizing case
Student search requires exact name match — partial or multi-result search could improve usability
Error handling can be more precise to help debugging
Output formatting could be enhanced (e.g. aligned columns)


Demo Prep Suggestions:

Show how to register and enrol a student
Enrol an existing student in a new course
Demonstrate lookup and listing functions
Be ready to explain design choices, data structures, and improvements


Git Submission Tips:

Commit after finishing each feature
Push to the individual branch on GitHub
Use clear commit messages like “feat: implement core helper functions”
