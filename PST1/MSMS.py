import time    # wait user look information

# Define four global variables
student_db = []
teacher_db = []
next_student_id = 1
next_teacher_id = 1

# The defination of two class 'Student' and 'Teacher'
class Student:
    def __init__(self, student_id, name,enrolled_in=None):
        self.id = student_id
        self.name = name
        self.enrolled_in = enrolled_in or []    # make sure when user input None, there are no breakdown when 'append'
# Initailize attributes
    @property
    def dictionary(self):
        return {'id':self.id,'name':self.name,'enrolled_in':self.enrolled_in}
    # use @property can make it possible to use this method as attributes, it make the instance easily return dictionary to store in xxx_db

class Teacher:
    def __init__(self, teacher_id, name, speciality):
        self.id = teacher_id
        self.name = name
        self.speciality = speciality
    # Initialize attributes
    @property
    def dictionary(self):
        return {'id':self.id,'name':self.name,'speciality':self.speciality}



# Core helper functions

# add theacher into teacher_db
def add_teacher(name, speciality):
    global next_teacher_id      # introduce global variable 'next_teahcer_id'
    new_teacher = Teacher(next_teacher_id, name, speciality)
    teacher_db.append(new_teacher.dictionary)
    next_teacher_id += 1      # act as a counter for teacher's id
    print(f"Core: Teacher '{name}' added successfully.")   # use 'f' srting to output dictionary information (including key and value)

# list all information of students
def list_students():
    print('-'*5,'Student List','-'*5)
    if student_db==[]:
        print("There are no students")
        return
    # stop this function and output the failure
    for a in student_db:
        print(f"id: {a['id']}  name: {a['name']}  enrolled_in: {a['enrolled_in']}")
    # use the the 'f' string to output all information of students (dictionary data type)

def list_teachers():
    print('-'*5,'Teacher List','-'*5)
    for teacher in teacher_db:
        print(f"id: {teacher['id']}, name: {teacher['name']}  speciality: {teacher['speciality']}")
    # output the differnt values of very keys

def find_students(information):
    information=str(information).strip().lower()      # add str() function to make sure it can be operated by strip() and lower()
    for i in student_db:
        if information==i['name'].lower():   
            return i   # stop the loop and exit this function
    else:
        print(f'there are no information about {information}')

def find_teachers(information):
    information=str(information).strip().lower()      # use strip() firstly and lower() secondly fasten the speed
    for i in teacher_db:
        if information in (i['name'].lower(),i['speciality']):   # store very value as tuple, and test whether information is in very tuple
            return i   # stop the loop and exit this function
    else:
        print(f'there are no information about {information}')


# Front desk function

def find_student_by_id(student_id):
    for a in student_db:
        if a['id'] == student_id:
            return a   # as long as the student is found, return his information and stop this function
    else:
        return None
    # use if-else statement to get whether the stuent are in list

def front_desk_register(name, instrument):
    global next_student_id
    try:
        new_student = Student(next_student_id, name)
        student_db.append(new_student.dictionary)   # store as dictionary
        
    
        front_desk_enrol(new_student.id, instrument)    # call function in another function
        # use fuction there to exam whether this student is appended successfully, if not print 'Error: Student ID {student_id} not found.'
        print(f"Front Desk: Successfully registered '{name}' and enrolled them in '{instrument}'.")
        next_student_id += 1          # prepare for next student
    except Exception as e:
        print(f'error: {e}')          # prevent there are no information in student[enrolled_in] which may cause breakdown

def front_desk_enrol(student_id, instrument):
    student = find_student_by_id(student_id)
    if student:
        student['enrolled_in'].append(instrument)
        print(f"Front Desk: Enrolled student {student_id} in '{instrument}'.")
    else:
        print(f"Error: Student ID {student_id} not found.")
    # test whether this student in student_db list

def front_desk_lookup(information):
    print(f'\t{information} is loading')
    find_students(information)
    find_teachers(information)


# Main application
def main():
    # provide initail data (two teacher)
    add_teacher("Dr. Keys", "Piano")
    add_teacher("Ms. Fret", "Guitar")
    choice = 1
    while choice!='q':
        print("\n===== Music School Front Desk =====")
        print("1. Register New Student")
        print("2. Enrol Existing Student")
        print("3. Lookup Student or Teacher")
        print("4. (Admin) List all Students")
        print("5. (Admin) List all Teachers")
        print("q. Quit")
        
        choice = input("Enter your choice: ").strip()

        # Register New Student
        if choice == '1':  
            name = input("Enter student name: ")
            instrument = input("Enter instrument to enrol in: ")
            front_desk_register(name, instrument)
            time.sleep(3)     # wait user look information
            continue
        # Enrol Existing Student
        elif choice == '2':
            try:
                student_id = int(input("Enter student ID: "))
                instrument = input("Enter instrument to enrol in: ")
                front_desk_enrol(student_id, instrument)
                time.sleep(3)
            except ValueError:
                print("Invalid ID. Please enter a number.")
            finally:
                continue   # make sure the program go into next loop
        # Lookup Student or Teacher
        elif choice == '3':
            information = input("Enter search term: ")
            front_desk_lookup(information)
            time.sleep(3)
            continue
        # List all Students
        elif choice == '4':
            list_students()
            time.sleep(5)
            continue
        # List all Teachers
        elif choice == '5':
            list_teachers()
            time.sleep(5)
            continue
        # Protect form other condition
        elif choice not in ['1','2','3','4','5','q']:
            print("Invalid choice. Please try again.")
            continue

# The entry of main program
if __name__ == "__main__":
    main()