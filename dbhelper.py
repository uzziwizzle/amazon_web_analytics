import pymongo
from datetime import date, datetime
from bson.objectid import ObjectId

DATABASE = "quickweb"


class DBHelper:

    def __init__(self):
        client = pymongo.MongoClient(
            #username ="shiptool",
            #password = "@",
            host="127.0.0.1",
            port=27017,
            # authSource="test"
        )   

        self.db = client[DATABASE]
       
    def get_user(self, email):
        return self.db.users.find_one({
            "email": email
        })
    # def get_user_id(self, id):
    #     return self.db.users.find_one({
    #         "_id":  ObjectId(id)
    #     })

    def get_user_by_phone(self, phone):
        return self.db.users.find_one({
            "phone": phone
        })


    def add_user(self, email, salt, hashed, phone):
        self.db.users.insert({
            "email": email,
            "salt": salt,
            "hashed": hashed,
            "phone": phone
            
        })
    #user permission
    def update_user(self, email, salt, hashed):
        return self.db.users.update({'email': email }, {'$set': {'salt': salt,"hashed":hashed}})





 