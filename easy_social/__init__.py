from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask
from sqlalchemy.pool import NullPool

from .extensions import db, login_manager, migrate
from .media import media_url
from .models import User


def _validate_database_url(database_url: str) -> None:
    if not database_url:
        return
    if "[YOUR-PASSWORD]" in database_url:
        raise ValueError(
            "DATABASE_URL still contains [YOUR-PASSWORD]. Replace it with the "
            "Supabase database password from Project Settings > Database."
        )

    parsed = urlsplit(database_url)
    if not parsed.hostname or not parsed.hostname.endswith(".pooler.supabase.com"):
        return

    if parsed.username == "postgres":
        raise ValueError(
            "Supabase pooler DATABASE_URL must use username "
            "postgres.<project-ref>, not postgres. Copy the transaction pooler "
            "connection string from Supabase Project Settings > Database."
        )
    if not parsed.password:
        raise ValueError(
            "Supabase pooler DATABASE_URL is missing a password. Use the "
            "database password from Supabase Project Settings > Database."
        )


def _database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return ""
    _validate_database_url(database_url)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _engine_options(database_url: str) -> dict:
    if not database_url.startswith("postgresql"):
        return {}
    return {
        "pool_pre_ping": True,
        "poolclass": NullPool,
        "connect_args": {"prepare_threshold": None},
    }


def _is_vercel() -> bool:
    return os.environ.get("VERCEL") == "1"


def _default_database_uri(app: Flask) -> str:
    if _is_vercel():
        return "sqlite:////tmp/easy_social.sqlite"
    return f"sqlite:///{Path(app.instance_path) / 'easy_social.sqlite'}"


def _default_upload_folder(app: Flask) -> str:
    if _is_vercel():
        return "/tmp/easy_social_uploads"
    return str(Path(app.root_path) / "static" / "uploads")


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    database_url = _database_url()
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=database_url or _default_database_uri(app),
        SQLALCHEMY_ENGINE_OPTIONS=_engine_options(database_url),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=_default_upload_folder(app),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        MEDIA_STORAGE_BACKEND=os.environ.get("MEDIA_STORAGE_BACKEND", "local"),
        SUPABASE_URL=os.environ.get("SUPABASE_URL"),
        SUPABASE_SERVICE_ROLE_KEY=os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        SUPABASE_STORAGE_BUCKET=os.environ.get("SUPABASE_STORAGE_BUCKET", "easy-social-media"),
        CAPTCHA_TESTING_SHOW_ANSWER=False,
    )

    if test_config:
        app.config.update(test_config)
        if "SQLALCHEMY_ENGINE_OPTIONS" not in test_config:
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _engine_options(
                app.config["SQLALCHEMY_DATABASE_URI"]
            )

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///") and not _is_vercel():
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if app.config["MEDIA_STORAGE_BACKEND"] == "local":
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    from .auth import bp as auth_bp
    from .social import bp as social_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(social_bp)
    app.jinja_env.globals["media_url"] = media_url

    if app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:////tmp/easy_social.sqlite":

        @app.before_request
        def ensure_tmp_database() -> None:
            db.create_all()
            if User.query.first() is None:
                from scripts.import_fake_data import DEFAULT_DATA_DIR, import_fake_data

                import_fake_data(DEFAULT_DATA_DIR)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        db.create_all()
        print("Initialized the database.")

    return app
