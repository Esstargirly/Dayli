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

    with app.app_context():
        from app import models  # noqa: F401 — registers tables with SQLAlchemy metadata

    from app.auth.routes import auth_bp
    from app.onboarding.routes import onboarding_bp
    from app.dashboard.routes import dashboard_bp
    from app.ai.routes import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ai_bp)

    @app.route("/")
    def index():
        from flask import render_template
        return render_template("welcome.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app