import pymongo
from datetime import date, datetime
from bson.objectid import ObjectId

DATABASE = "amazon_web_analytics"


class DBHelper:

    def __init__(self):
        client = pymongo.MongoClient(
            host="127.0.0.1",
            port=27017,
        )   

        self.db = client[DATABASE]
       
    def get_user(self, email):
        return self.db.users.find_one({
            "email": email
        })


    def get_user_by_phone(self, phone):
        return self.db.users.find_one({
            "phone": phone
        })


    def add_user(self, email, salt, hashed, phone):
        self.db.users.insert_one({
            "email": email,
            "salt": salt,
            "hashed": hashed,
            "phone": phone
            
        })
    def upload_data(self, email, file, date,type,duration):
        self.db.upload_data.insert_one({
            
            "user": email,
            "file": file,
            "date": date,
            'type':type,
            'duration':duration
            
        })
    #user permission
    def update_user(self, email, salt, hashed):
        return self.db.users.update({'email': email }, {'$set': {'salt': salt,"hashed":hashed}})





 