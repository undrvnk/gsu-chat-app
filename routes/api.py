import secrets

from flask import g, jsonify, request

from auth import login_required
from db import query_all, query_db, query_one
from services.chatbot import generate_chat_answer, now_iso
from werkzeug.security import check_password_hash, generate_password_hash



def register(app):
    # ----- Notifications (dropdown popup, not a full page) -----
    @app.route("/api/notifications/mark-read", methods=("POST",))
    @login_required
    def mark_notifications_read():
        query_db(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (g.user["id"],),
        )
        return jsonify({"ok": True})
    
    @app.route("/api/notifications/<int:notification_id>", methods=("DELETE",))
    @login_required
    def dismiss_notification(notification_id):
        row = query_one(
            "SELECT id FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, g.user["id"]),
        )
        if not row:
            return jsonify({"ok": False, "error": "Not found"}), 404
        query_db(
            "DELETE FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, g.user["id"]),
        )
        return jsonify({"ok": True})
    
    @app.route("/api/notifications/clear", methods=("POST",))
    @login_required
    def clear_notifications():
        query_db("DELETE FROM notifications WHERE user_id = ?", (g.user["id"],))
        return jsonify({"ok": True})
    
    # ----- JSON API -----
    @app.route("/api/chat", methods=("POST",))
    def api_chat():
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Message is required."}), 400
        answer = generate_chat_answer(message)
        if g.user:
            query_db(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
                (g.user["id"], "user", message),
            )
            query_db(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
                (g.user["id"], "assistant", answer),
            )
        return jsonify({"reply": answer})
    
    @app.route("/api/login", methods=("POST",))
    def api_login():
        data = request.get_json(silent=True) or {}
        identifier = (data.get("identifier") or "").strip().lower()
        password = data.get("password") or ""
        user = query_one(
            "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
            (identifier, identifier),
        )
        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username/email or password."}), 401
        token = secrets.token_urlsafe(32)
        query_db("UPDATE users SET api_token = ? WHERE id = ?", (token, user["id"]))
        return jsonify(
            {
                "token": token,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                },
            }
        )
    
    @app.route("/api/users", methods=("GET",))
    @login_required
    def api_users():
        search = request.args.get("search", "").strip()
        if search:
            pattern = f"%{search}%"
            users = query_all(
                "SELECT id, username, email, full_name, role, major, is_admin, created_at "
                "FROM users WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ? ORDER BY id",
                (pattern, pattern, pattern),
            )
        else:
            users = query_all(
                "SELECT id, username, email, full_name, role, major, is_admin, created_at "
                "FROM users ORDER BY id"
            )
        return jsonify({"users": [dict(row) for row in users]})
    
    @app.route("/api/users/<int:user_id>", methods=("GET",))
    @login_required
    def api_user_detail(user_id):
        user = query_one(
            "SELECT id, username, email, full_name, role, major, is_admin, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        if user is None:
            return jsonify({"error": "User not found."}), 404
        return jsonify({"user": dict(user)})
    
    @app.route("/health")
    def health():
        return jsonify({"ok": True, "time": now_iso()})
