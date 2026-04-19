from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    db.init_app(app)
    Migrate(app, db)

    from .views import views
    from .routes import routes
    from .populate_groups import populate_groups_if_needed

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(routes, url_prefix='/')

    from .models import User, SystemState, AccessCredential
    from .routes import generate_credential, send_credentials_email

    login_manager = LoginManager()
    login_manager.login_view = 'routes.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    with app.app_context():

        # ⚠️ Still not ideal, but kept because you already use it
        db.create_all()

        # 🔹 Seed groups ONCE if empty
        populate_groups_if_needed()

        state = SystemState.query.first()
        if not state:
            state = SystemState(credentials_generated=False)
            db.session.add(state)
            db.session.commit()

        if not state.credentials_generated:
            generated = []

            for _ in range(1000):
                pid, pwd, h = generate_credential()
                db.session.add(
                    AccessCredential(public_id=pid, secret_hash=h)
                )
                generated.append((pid, pwd))

            state.credentials_generated = True
            db.session.commit()

            send_credentials_email(generated)

    return app
