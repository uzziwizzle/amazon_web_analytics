from dbhelper import DBHelper

DB = DBHelper()

class User:
    def __init__(self, email):
        self.email = email
    
    def get_id(self):
        return self.email

    def is_active(self):
        return True

    def is_anonymous(self):
        return False
    
    def is_authenticated(self):
        return True

    def is_admin(self):
        checkedAdmin = DB.check_admin(self.email)
        if checkedAdmin['organization']== "admin":
            return True
        return False

    def get_user(self):
        user = DB.get_user(self.email)
        return user

