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