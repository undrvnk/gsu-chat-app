import os
import secrets
import sqlite3

from flask import abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from auth import login_required, roles_required, validate_registration
from config import DOC_LABELS, DOC_TYPES, FACULTY_REVIEW_STATUSES, MAJORS, STUDENT_APP_STATUSES, UPLOAD_DIR
from db import query_all, query_db, query_one
from services.documents import allowed_file, get_missing_documents, get_user_documents
from services.matching import (
    add_notification,
    get_user_interests,
    is_bookmarked,
    match_score,
    notify_high_match_faculty,
    recommended_faculty,
    set_user_interests,
)



def register(app):
    # ----- Public + auth -----
    @app.route("/")
    def index():
        programs = query_all("SELECT * FROM programs ORDER BY id LIMIT 3")
        return render_template("index.html", programs=programs)
    
    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            full_name = request.form.get("full_name", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "student").strip().lower()
            major = request.form.get("major", "").strip()
            if role not in ("student", "teacher"):
                role = "student"
            if role == "teacher":
                major = ""
            error = validate_registration(username, email, password)
            if error is None:
                try:
                    cur = query_db(
                        "INSERT INTO users "
                        "(username, email, full_name, password_hash, role, major, verified) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            username,
                            email,
                            full_name,
                            generate_password_hash(password),
                            role,
                            major,
                            0 if role == "teacher" else 1,
                        ),
                    )
                    if role == "teacher":
                        new_id = cur.lastrowid
                        for admin in query_all("SELECT id FROM users WHERE role = 'admin'"):
                            add_notification(
                                admin["id"],
                                f"New faculty account '{username}' awaits verification.",
                                url_for("admin_faculty"),
                            )
                        flash(
                            "Faculty account created. An admin must verify it before it appears in the directory.",
                            "success",
                        )
                    else:
                        flash("Account created. You can sign in now.", "success")
                    return redirect(url_for("login"))
                except sqlite3.IntegrityError:
                    error = "That username or email is already registered."
            flash(error, "error")
        return render_template("register.html")
    
    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            identifier = request.form.get("identifier", "").strip().lower()
            password = request.form.get("password", "")
            user = query_one(
                "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
                (identifier, identifier),
            )
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid username/email or password.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash("Welcome back.", "success")
                return redirect(url_for("dashboard"))
        return render_template("login.html")
    
    @app.route("/logout", methods=("POST",))
    def logout():
        session.clear()
        flash("Signed out.", "success")
        return redirect(url_for("index"))
    
    # ----- Dashboard -----
    @app.route("/dashboard")
    @login_required
    def dashboard():
        role = g.user["role"]
        ctx = {"interests": get_user_interests(g.user["id"])}
        if role == "student":
            ctx["applications"] = query_all(
                "SELECT a.*, p.name AS program_name, p.deadline AS deadline "
                "FROM applications a JOIN programs p ON p.id = a.program_id "
                "WHERE a.student_id = ? ORDER BY a.updated_at DESC",
                (g.user["id"],),
            )
            ctx["missing_docs"] = [DOC_LABELS[d] for d in get_missing_documents(g.user["id"])]
            ctx["recommended"] = recommended_faculty(g.user["id"], limit=3)
            ctx["bookmarks"] = query_all(
                "SELECT u.* FROM bookmarks b JOIN users u ON u.id = b.target_id "
                "WHERE b.user_id = ? ORDER BY u.full_name",
                (g.user["id"],),
            )
        elif role == "teacher":
            ctx["student_count"] = query_one(
                "SELECT COUNT(*) AS c FROM users WHERE role = 'student'"
            )["c"]
            ctx["saved_students"] = query_all(
                "SELECT u.* FROM bookmarks b JOIN users u ON u.id = b.target_id "
                "WHERE b.user_id = ? ORDER BY u.full_name",
                (g.user["id"],),
            )
            ctx["my_notes"] = query_all(
                "SELECT n.*, u.full_name AS student_name, u.id AS student_id "
                "FROM faculty_notes n JOIN users u ON u.id = n.student_id "
                "WHERE n.faculty_id = ? ORDER BY n.created_at DESC LIMIT 5",
                (g.user["id"],),
            )
        elif role == "admin":
            ctx["counts"] = {
                "students": query_one("SELECT COUNT(*) AS c FROM users WHERE role = 'student'")["c"],
                "faculty": query_one("SELECT COUNT(*) AS c FROM users WHERE role = 'teacher'")["c"],
                "unverified": query_one("SELECT COUNT(*) AS c FROM users WHERE role = 'teacher' AND verified = 0")["c"],
                "programs": query_one("SELECT COUNT(*) AS c FROM programs")["c"],
            }
        return render_template("dashboard.html", **ctx)
