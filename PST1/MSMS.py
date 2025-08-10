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
