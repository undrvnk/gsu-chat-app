from functools import wraps

from flask import g, jsonify, redirect, request, url_for

from db import query_one


def validate_registration(username, email, password):
    if not username:
        return "Username is required."
    if not email or "@" not in email:
        return "A valid email is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required."}), 401
                return redirect(url_for("login"))
            if g.user["role"] not in roles:
                flash_msg = "You do not have access to that page."
                from flask import flash

                flash(flash_msg, "error")
                return redirect(url_for("dashboard"))
            return view(**kwargs)

        return wrapped_view

    return decorator


def user_from_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    if not token:
        return None
    return query_one("SELECT * FROM users WHERE api_token = ?", (token,))


def is_faculty(user):
    return user is not None and user["role"] == "teacher"


def is_admin(user):
    return user is not None and (user["role"] == "admin" or user["is_admin"])
