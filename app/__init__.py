from flask import Flask
from flask_login import LoginManager
from app.models import User
from app.routes import bp as main_bp
from app.utils import get_data_file_path, load_json

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        file_path = get_data_file_path('user_info.json')
        try:
            users_data = load_json(file_path)
            users = {str(data['id']): User(id=data['id'], username=username, password=data['password']) for username, data in users_data.items()}
            print(users)
            return users.get(user_id)
        except:
            return None

    # Register blueprint
    app.register_blueprint(main_bp)

    return app
