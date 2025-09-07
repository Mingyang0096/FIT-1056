import time
from app.schedule import ScheduleManager

"""
Main CLI interface for the MSMS v3 (Object-Oriented) system.
Provides menu-driven access to student, teacher, and course management.
Integrates with ScheduleManager for all business logic and data handling.
Designed for front-desk operations with immediate user feedback.
"""

def front_desk_daily_roster(manager, day):
    """Display all lessons for a given day in a tabular format."""
    print(f"\n--- Daily Roster for {day} ---")
    lessons = manager.get_lessons_by_day(day)
    if not lessons:
        print("No lessons scheduled for this day.")
        return

    # Column headers with fixed-width formatting
    print(f"{'Course ID':<10} {'Course Name':<20} {'Teacher':<20} {'Students'}")
    print("-" * 70)
    for lesson in lessons:
        students = ", ".join(lesson["students"]) or "None"
        print(f"{lesson['course_id']:<10} {lesson['course_name']:<20} {lesson['teacher']:<20} {students}")

def switch_course(manager, student_id, from_id, to_id):
    """Move a student from one course to another."""
    ok = manager.switch_student_course(student_id, from_id, to_id)
    if ok:
        print(f"Student {student_id} moved from course {from_id} to {to_id}.")
    else:
        print("Switch failed. Check student and course IDs.")

def main():
    manager = ScheduleManager()  # Central controller for all operations
    while True:
        # Main menu display
        print("\n===== MSMS v3 (Object-Oriented) =====")
        print("1. Register New Student")
        print("2. Enrol Existing Student")
        print("3. Lookup Students/Teachers")
        print("4. List Students")
        print("5. List Teachers")
        print("6. Add Teacher")
        print("7. Add Course")
        print("8. List Courses")
        print("9. Check-in Student")
        print("10. Print Student Card")
        print("11. Remove Student")
        print("12. Remove Teacher")
        print("13. Remove Course")
        print("14. Daily Roster")
        print("15. Switch Course")
        print("q. Quit")

        choice = input("Enter choice: ").strip()

        if choice == '1':
            name = input("Student name: ").strip()
            course_id = input("Initial course ID: ").strip()
            # Allow optional initial course assignment
            if course_id:
                manager.add_student(name, [int(course_id)])
            else:
                manager.add_student(name)
            print("Student registered.")
            time.sleep(1)

        elif choice == '2':
            sid = int(input("Student ID: "))
            cid = int(input("Course ID: "))
            if manager.enrol_student_in_course(sid, cid):
                print("Enrolment successful.")
            else:
                print("Enrolment failed.")
            time.sleep(1)

        elif choice == '3':
            term = input("Search term (regex): ").strip()
            # Search both students and teachers using regex
            students = manager.find_students_by_name(term)
            teachers = manager.find_teachers_by_name_or_speciality(term)
            print("\nMatched Students:")
            for s in students:
                print(f"  {s.id}: {s.name}")
            print("\nMatched Teachers:")
            for t in teachers:
                print(f"  {t.id}: {t.name} ({t.speciality})")
            time.sleep(1)

        elif choice == '4':
            print("\nStudents:")
            for info in manager.list_students():
                print(f"  {info['id']}: {info['name']} [{info['courses']} courses]")
            time.sleep(1)

        elif choice == '5':
            print("\nTeachers:")
            for info in manager.list_teachers():
                print(f"  {info['id']}: {info['name']} ({info['speciality']})")
            time.sleep(1)

        elif choice == '6':
            name = input("Teacher name: ").strip()
            spec = input("Speciality: ").strip()
            manager.add_teacher(name, spec)
            print("Teacher added.")
            time.sleep(1)

        elif choice == '7':
            name = input("Course name: ").strip()
            instr = input("Instrument: ").strip()
            tid = int(input("Teacher ID: ").strip())
            manager.add_course(name, instr, tid)
            print("Course added.")
            time.sleep(1)

        elif choice == '8':
            print("\nCourses:")
            for c in manager.list_courses():
                print(f"  {c['id']}: {c['name']} ({c['instrument']}) → Teacher {c['teacher_id']}")
            time.sleep(1)

        elif choice == '9':
            sid = int(input("Student ID: "))
            cid = int(input("Course ID: "))
            if manager.check_in(sid, cid):
                print("Check-in recorded.")
            else:
                print("Check-in failed.")
            time.sleep(1)

        elif choice == '10':
            sid = int(input("Student ID: "))
            student = manager.find_student_by_id(sid)
            if not student:
                print("Invalid student ID.")
            else:
                folder = input("Folder to save card: ").strip()
                # Collect enrolled course names for display on card
                names = [manager.find_course_by_id(cid).name
                         for cid in student.enrolled_course_ids
                         if manager.find_course_by_id(cid)]
                path = student.save_card(folder, enrolled_display=names)
                print(f"Card saved to {path}.")
            time.sleep(1)

        elif choice == '11':
            sid = int(input("Student ID: "))
            if manager.remove_student(sid):
                print("Student removed.")
            else:
                print("Removal failed.")
            time.sleep(1)

        elif choice == '12':
            tid = int(input("Teacher ID: "))
            if manager.remove_teacher(tid):
                print("Teacher removed.")
            else:
                print("Removal failed.")
            time.sleep(1)

        elif choice == '13':
            cid = int(input("Course ID: "))
            if manager.remove_course(cid):
                print("Course removed.")
            else:
                print("Removal failed.")
            time.sleep(1)

        elif choice == '14':
            day = input("Day (e.g. Monday): ").strip()
            front_desk_daily_roster(manager, day)
            time.sleep(1)

        elif choice == '15':
            sid = int(input("Student ID: "))
            old = int(input("From Course ID: "))
            new = int(input("To Course ID: "))
            switch_course(manager, sid, old, new)
            time.sleep(1)

        elif choice.lower() == 'q':
            print("Goodbye!")
            break

        else:
            print("Invalid choice.")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
