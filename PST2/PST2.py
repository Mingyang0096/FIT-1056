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