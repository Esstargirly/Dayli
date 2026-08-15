from flask import Flask
from dotenv import load_dotenv

from app.config import Config
from app.extensions import db, migrate, login_manager

load_dotenv()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Blueprints registered here as each one is built.
    # from app.auth.routes import auth_bp
    # app.register_blueprint(auth_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app