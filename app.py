import os

import config  # noqa: F401 - vendor path + .env must load before Flask import

from flask import flash, g, redirect, url_for
from auth import is_admin, is_faculty, user_from_bearer_token
from config import (
    DATABASE,
    DEGREE_TYPES,
    MAJORS,
    RESEARCH_AREAS,
    UPLOAD_DIR,
)
from db import get_db, init_db, query_all, query_db, query_one
from routes import register_routes
from seed import seed_users

# Re-export for smoke_test.py and scripts that use `import app as appmod`.
__all__ = [
    "app",
    "create_app",
    "init_db",
    "seed_users",
    "query_db",
    "query_one",
    "query_all",
    "get_db",
]


def create_app():
    from flask import Flask

    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me-before-production"),
        DATABASE=DATABASE,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    @app.before_request
    def load_logged_in_user():
        from flask import session

        user_id = session.get("user_id")
        g.user = None
        if user_id is not None:
            g.user = query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if g.user is None:
            g.user = user_from_bearer_token()

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_globals():
        unread_notifications = 0
        alert_notifications = []
        if getattr(g, "user", None):
            n = query_one(
                "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
                (g.user["id"],),
            )
            unread_notifications = n["c"] if n else 0
            alert_notifications = query_all(
                "SELECT id, body, link, is_read, created_at FROM notifications "
                "WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
                (g.user["id"],),
            )
        return {
            "unread_notifications": unread_notifications,
            "alert_notifications": alert_notifications,
            "research_areas": RESEARCH_AREAS,
            "majors": MAJORS,
            "degree_types": DEGREE_TYPES,
            "is_admin": is_admin,
            "is_faculty": is_faculty,
        }

    @app.errorhandler(413)
    def too_large(error):
        flash("That file is too large. The limit is 8 MB.", "error")
        return redirect(url_for("profile_edit"))

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Initialized the SQLite database.")

    @app.cli.command("seed-users")
    def seed_users_command():
        init_db()
        seed_users()
        print("Inserted seed data for testing.")

    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    init_db()
    seed_users()
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    # threaded=True serves CSS/JS in parallel; debug reloader is dev-only.
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=debug,
        threaded=True,
    )
