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