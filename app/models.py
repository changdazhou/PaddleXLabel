from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin

class User():
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    # Flask-Login requires these methods
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)