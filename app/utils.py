import json
import os
from app.models import User

def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_data_file_path(filename):
    return os.path.join(os.path.dirname(__file__), 'data', filename)

def load_users():
    file_path = get_data_file_path('user_info.json')
    try:
        users_data = load_json(file_path)
        return {username: User(id=data['id'], username=username, password=data['password']) for username, data in users_data.items()}
    except FileNotFoundError:
        return {}

def save_users(users):
    file_path = get_data_file_path('user_info.json')
    users_data = {username: user.__dict__ for username, user in users.items()}
    save_json(file_path, users_data)