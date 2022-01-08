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
    def upload_changes(self, email, file, date,type,duration,id):
        self.db.upload_changes.insert_one({
            
            "user": email,
            "file": file,
            "date": date,
            'type':type,
            'duration':duration,
            'recommendation_id':id,
            'created_at':datetime.utcnow()
            
        })
    def upload_recomendations(self, email, file, date,country,type,duration):
        self.db.upload_recomendations.insert_one({
            "user": email,
            "file": file,
            "date": date,
            'type': type,
            'country':country,
            'duration':duration,
            'created_at':datetime.utcnow()
            
        })
    #user permission
    def update_user(self, email, salt, hashed):
        return self.db.users.update({'email': email }, {'$set': {'salt': salt,"hashed":hashed}})

# get latest value
    def finddata(self, date): 
        return self.db.upload_recomendations.find({'date':date}).sort('_id',-1).limit(1)

    def findallrecomendationsdate(self, date):
        return self.db.upload_recomendations.find({'date':date})
    def findallrecomendations(self):
        return self.db.upload_recomendations.find({})



    





 