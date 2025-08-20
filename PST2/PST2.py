# Music School Management System (MSMS)
import time 
import json
import os

r_path=None
# Global variable holding the JSON data file path.
# It is set by user input in main and reused across functions.

class Student:
    # Simple data holder for student entities.
    def __init__(self,name,id,enrolled_in=None):
        self.name=name
        self.id=id
        self.enrolled_in=enrolled_in or []
    @property
    def dictionary(self):
        # Convert instance to a serializable dictionary for storage.
        return {'id':self.id,'name':self.name,'enrolled_in':self.enrolled_in}
    # use @property can make it possible to use this method as attributes, it make the instance easily return dictionary to store in xxx_db

class Teacher:
    # Simple data holder for teacher entities.
    def __init__(self,name,id,speciality):
        self.name=name
        self.id=id
        self.speciality=speciality
    # Initialize attributes
    @property
    def dictionary(self):
        # Convert instance to a serializable dictionary for storage.
        return {'id':self.id,'name':self.name,'speciality':self.speciality}

def load_data():
    # Load application data from the JSON file specified by r_path.
    # Note: If r_path points to a directory or invalid path, open will raise an error.
    global r_path
    try:
        with open(r_path,"r",encoding="utf-8") as file:
            app_data=json.load(file)
        return app_data
    except FileNotFoundError as e:
        # If the file does not exist, prompt to create a new one and initialize structure.
        print(f"Error: {e}")
        x=input("do you want to create new file to store information. [Y/N]")
        if x=="Y":
            r_path = create_file()
            print("create successfully")
            app_data={
                "students":[],
                "teachers":[],
                "attendance":[],
                "next_student_id":1,
                "next_teacher_id":1
            }
            save_data(app_data)
            return app_data
        elif x=="N":
            # User declined to create a file; return None to let caller handle it.
            return
        else:
            # Invalid input branch; nothing is returned implicitly.
            print("invalid input")

def save_data(data):
    # Save the given data dictionary to r_path as pretty-printed JSON.
    # Note: If r_path does not exist or is a directory, the existence check below will fail or mislead.
    if not os.path.exists(r_path):
        print(f"there are no file path as {r_path}")
    else:
        try:
            with open(r_path,"w",encoding="utf-8") as file:
                json.dump(data,file,ensure_ascii=False,indent=4)
                print("save successfully")
        except OSError as e:
            # Catch file system errors such as permission denied or invalid path.
            print(f"Error: {e}")

def create_file():
    # Create a new empty file at user-specified folder and name, then return the full path.
    # Note: This function assumes the folder already exists and does not create directories.
    # Note: The file name can be any string; callers may wish to include .json extension.
    folder_path=input("the path of your folder:\n")
    name=input("the name of your file:\n")
    path=os.path.join(folder_path,name)
    if os.path.exists(folder_path):
        with open(path,"w",encoding="utf-8") as file:
            pass
    return (path)

def check_in(student_id,course_id):
    # Append an attendance record with current local timestamp for a student and course.
    app_data=load_data()
    ts = time.time()
    local_time=time.localtime(ts)
    t=time.strftime("%Y-%m-%d %H:%M",local_time)
    a={'student_id':student_id,'course_id':course_id,'timestamp':t}
    app_data["attendance"].append(a)
    save_data(app_data)

def print_student_card(student_id):
    # Generate a plain text ID badge for a student and save it to a user-chosen folder.
    # The file name is "<name>'s card.txt".
    app_data=load_data()
    path=None
    for i in app_data['students']:
        if student_id==i['id']:
            path=input("choose a folder to store this file:\n")
            path=os.path.join(path,f"{i['name']}'s card.txt")
            break
        else:
            continue
    if not path:
        # If the student is not found, notify and exit.
        print("no found")
        return
    try:
        with open(path,'w',encoding="utf-8") as f:
            # Simple formatted card content.
            f.write("========================\n")
            f.write(f"  MUSIC SCHOOL ID BADGE\n")
            f.write("========================\n")
            f.write(f"ID: {i['id']}\n")
            f.write(f"Name: {i['name']}\n")
            f.write(f"Enrolled In: {', '.join(i.get('enrolled_in', []))}\n")
        print(f"Printed student card to {path} successfully.")
    except Exception as e:
        # Any I O or path error is reported here.
        print(f"Error: {e}")

# Core helper functions

# add theacher into teacher_db
def add_teacher(name, speciality):
    # Create a teacher with the next available ID, append to list, increment counter, and persist.
    app_data=load_data()
    new_teacher = Teacher(name, app_data["next_teacher_id"], speciality)
    app_data["teachers"].append(new_teacher.dictionary)
    app_data['next_teacher_id'] += 1      # act as a counter for teacher's id
    save_data(app_data)
    print(f"Core: Teacher '{name}' added successfully.")   # use 'f' srting to output dictionary information (including key and value)

def remove_student(student_id):
    # Remove a student with matching id from the students list and persist changes.
    app_data=load_data()
    for i in app_data["students"]:
        if student_id==i['id']:
            app_data['students'].remove(i)
            save_data(app_data)
            print("save successfully")
            return
    else:
        print("no found")
    
# list all information of students
def list_students():
    # Print a simple table-like list of all students.
    app_data=load_data()
    print('-'*5,'Student List','-'*5)
    if app_data=={}:
        # This condition is rarely true; if load_data failed it may be None which is not handled here.
        print("There are no students")
        return
    # stop this function and output the failure
    for a in app_data['students']:
        print(f"id: {a['id']}  name: {a['name']}  enrolled_in: {a['enrolled_in']}")
    # use the the 'f' string to output all information of students (dictionary data type)

def list_teachers():
    # Print a simple list of all teachers.
    app_data=load_data()
    print('-'*5,'Teacher List','-'*5)
    for teacher in app_data['teachers']:
        print(f"id: {teacher['id']}, name: {teacher['name']}  speciality: {teacher['speciality']}")
    # output the differnt values of very keys

def find_students(information):
    # Case-insensitive exact-name search for a student. Prints the dict if found.
    app_data=load_data()
    information=str(information).strip().lower()      # add str() function to make sure it can be operated by strip() and lower()
    for i in app_data['students']:
        if information==i['name'].lower():   
            print(i)
            return   # stop the loop and exit this function
    else:
        print(f'there are no information about {information}')

def find_teachers(information):
    # Case-insensitive search in either teacher name or speciality.
    app_data=load_data()
    information=str(information).strip().lower()      # use strip() firstly and lower() secondly fasten the speed
    for i in app_data['teachers']:
        if information in (i['name'].lower(),i['speciality'].lower()):   # store very value as tuple, and test whether information is in very tuple
            print(i)
            return   # stop the loop and exit this function
    else:
        print(f'there are no information about {information}')


# Front desk function

def find_student_by_id(student_id):
    # Return the student dict by id or None if not found.
    app_data=load_data()
    for a in app_data['students']:
        if a['id'] == student_id:
            return a   # as long as the student is found, return his information and stop this function
    else:
        return None
    # use if-else statement to get whether the stuent are in list

def front_desk_register(name, instrument):
    # Register a new student, save, enroll them in an instrument, then increment the student id counter and save again.
    # Note: The id is incremented after enrollment so the newly created id is used immediately for enrollment.
    app_data=load_data()
    try:
        new_student = Student(name, app_data['next_student_id'])
        app_data['students'].append(new_student.dictionary)  
        save_data(app_data)
        front_desk_enrol(new_student.id, instrument)    # call function in another function
        # Use function here to confirm the student is appended successfully; 
        # if not, print 'Error: Student ID {student_id} not found.'
        print(f"Front Desk: Successfully registered '{name}' and enrolled them in '{instrument}'.")
        app_data=load_data()
        app_data['next_student_id'] += 1          # Prepare for the next student registration
        save_data(app_data)
    except Exception as e:
        # Broad exception catch to prevent application crash from unexpected state
        print(f'error: {e}')          

def front_desk_enrol(student_id, instrument):
    # Enroll an existing student in a new instrument
    app_data = load_data()
    if app_data is None:
        # Exit if data loading failed
        return
    for a in app_data['students']:
        if a['id'] == student_id:
            a.setdefault('enrolled_in', [])
            a['enrolled_in'].append(instrument)
            save_data(app_data)
            print(f"Front Desk: Enrolled student {student_id} in '{instrument}'.")
            return
    print(f"Error: Student ID {student_id} not found.")

def front_desk_lookup(information):
    # Perform search for both students and teachers
    print(f'\t{information} is loading')
    find_students(information)
    find_teachers(information)

# Main application
def main():
    # Entry point for the program
    global r_path
    r_path=input("input the file path you want to load and fix:\n").strip()
    # If the file path is a directory, open will fail
    load_data()
    choice = 1
    while choice!='q':
        print("\n===== MSMS v2 (Persistent) =====")
        print("1. Register New Student")
        print("2. Enrol Existing Student")
        print("3. Lookup Student or Teacher")
        print("4. (Admin) List all Students")
        print("5. (Admin) List all Teachers")
        print("6. Check-in Student")
        print("7. Print Student Card")
        print("8. Remove Student")
        print("9. Restart")
        print("q. Quit")
        
        choice = input("Enter your choice: ").strip()

        if choice == '1':  
            # Register new student flow
            name = input("Enter student name: ")
            instrument = input("Enter instrument to enrol in: ")
            front_desk_register(name, instrument)
            time.sleep(3)     
            continue
        elif choice == '2':
            # Enrol an existing student
            try:
                student_id = int(input("Enter student ID: "))
                instrument = input("Enter instrument to enrol in: ")
                front_desk_enrol(student_id, instrument)
                time.sleep(3)
            except ValueError:
                # Handle non-integer ID inputs
                print("Invalid ID. Please enter a number.")
            finally:
                continue
        elif choice == '3':
            # Lookup student or teacher
            information = input("Enter search term: ")
            front_desk_lookup(information)
            time.sleep(3)
            continue
        elif choice == '4':
            # List all students
            list_students()
            time.sleep(5)
            continue
        elif choice == '5':
            # List all teachers
            list_teachers()
            time.sleep(5)
            continue
        elif choice == '6':  
            # Student check-in
            x=int(input("input your student_id:\n"))
            y=int(input("input your course_id:\n"))
            check_in(x,y)
            time.sleep(5)
        elif choice == '7':
            # Print student card
            information=int(input("input student's id:\n"))
            print_student_card(information)
            time.sleep(5)
        elif choice == '8':
            # Remove student
            information=int(input("input student's id:\n"))
            remove_student(information)
            time.sleep(5)
        elif choice == 'q':
            # Quit application
            print('see you')
            break
        elif choice == '9':
            # Restart program
            return main()
        else:
            # Handle invalid menu choices
            print("Invalid choice. Please try again.")
            continue

if __name__ == "__main__":
    # Program entry point
    main()