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
    # ----- Profile -----
    @app.route("/profile", methods=("GET", "POST"))
    @login_required
    def profile_edit():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            bio = request.form.get("bio", "").strip()
            interests = request.form.getlist("interests")
            if not email or "@" not in email:
                flash("A valid email is required.", "error")
                return redirect(url_for("profile_edit"))
            try:
                query_db(
                    "UPDATE users SET full_name = ?, email = ?, bio = ? WHERE id = ?",
                    (full_name, email, bio, g.user["id"]),
                )
            except sqlite3.IntegrityError:
                flash("That email is already used by another account.", "error")
                return redirect(url_for("profile_edit"))
            set_user_interests(g.user["id"], interests)
            if g.user["role"] == "student":
                query_db(
                    "UPDATE users SET major = ?, gpa = ?, prior_degree = ?, "
                    "prior_institution = ?, test_scores = ? WHERE id = ?",
                    (
                        request.form.get("major", "").strip(),
                        request.form.get("gpa", "").strip(),
                        request.form.get("prior_degree", "").strip(),
                        request.form.get("prior_institution", "").strip(),
                        request.form.get("test_scores", "").strip(),
                        g.user["id"],
                    ),
                )
            elif g.user["role"] == "teacher":
                query_db(
                    "UPDATE users SET title = ?, accepting_students = ?, lab_url = ?, "
                    "publications_url = ? WHERE id = ?",
                    (
                        request.form.get("title", "").strip(),
                        1 if request.form.get("accepting_students") else 0,
                        request.form.get("lab_url", "").strip(),
                        request.form.get("publications_url", "").strip(),
                        g.user["id"],
                    ),
                )
            flash("Profile updated.", "success")
            return redirect(url_for("profile_edit"))
    
        documents = get_user_documents(g.user["id"])
        return render_template(
            "profile_edit.html",
            user_interests=get_user_interests(g.user["id"]),
            documents=documents,
            doc_types=DOC_TYPES,
            doc_labels=DOC_LABELS,
        )
    
    @app.route("/u/<int:user_id>")
    @login_required
    def view_profile(user_id):
        profile = query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if profile is None or profile["role"] == "admin":
            abort(404)
        notes = []
        student_applications = []
        if g.user["role"] in ("teacher", "admin") and profile["role"] == "student":
            notes = query_all(
                "SELECT n.*, u.full_name AS author FROM faculty_notes n "
                "JOIN users u ON u.id = n.faculty_id WHERE n.student_id = ? "
                "ORDER BY n.created_at DESC",
                (user_id,),
            )
            student_applications = query_all(
                "SELECT a.*, p.name AS program_name FROM applications a "
                "JOIN programs p ON p.id = a.program_id "
                "WHERE a.student_id = ? ORDER BY a.updated_at DESC",
                (user_id,),
            )
        programs = []
        if profile["role"] == "teacher":
            programs = query_all(
                "SELECT p.* FROM program_faculty pf JOIN programs p ON p.id = pf.program_id "
                "WHERE pf.faculty_id = ? ORDER BY p.name",
                (user_id,),
            )
        my_score = None
        if g.user["id"] != user_id:
            my_score = match_score(
                get_user_interests(g.user["id"]), get_user_interests(user_id)
            )
        return render_template(
            "profile_view.html",
            profile=profile,
            profile_interests=get_user_interests(user_id),
            documents=get_user_documents(user_id),
            doc_labels=DOC_LABELS,
            notes=notes,
            programs=programs,
            bookmarked=is_bookmarked(g.user["id"], user_id),
            my_score=my_score,
            student_applications=student_applications,
        )
    
    @app.route("/documents/upload", methods=("POST",))
    @login_required
    def upload_document():
        doc_type = request.form.get("doc_type", "")
        if doc_type not in DOC_TYPES:
            flash("Unknown document type.", "error")
            return redirect(url_for("profile_edit"))
        file = request.files.get("file")
        if file is None or file.filename == "":
            flash("Please choose a file to upload.", "error")
            return redirect(url_for("profile_edit"))
        if not allowed_file(file.filename):
            flash("Allowed file types: pdf, doc, docx, txt, rtf, odt.", "error")
            return redirect(url_for("profile_edit"))
        user_dir = os.path.join(UPLOAD_DIR, str(g.user["id"]))
        os.makedirs(user_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1].lower()
        stored = f"{doc_type}_{secrets.token_hex(8)}{ext}"
        file.save(os.path.join(user_dir, stored))
        query_db(
            "INSERT INTO documents (user_id, doc_type, filename, original_name) "
            "VALUES (?, ?, ?, ?)",
            (g.user["id"], doc_type, stored, secure_filename(file.filename)),
        )
        flash(f"{DOC_LABELS[doc_type]} uploaded.", "success")
        return redirect(url_for("profile_edit"))
    
    @app.route("/documents/<int:doc_id>")
    @login_required
    def download_document(doc_id):
        doc = query_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
        if doc is None:
            abort(404)
        owner = doc["user_id"] == g.user["id"]
        reviewer = g.user["role"] in ("teacher", "admin")
        if not (owner or reviewer):
            abort(403)
        path = os.path.join(UPLOAD_DIR, str(doc["user_id"]), doc["filename"])
        if not os.path.isfile(path):
            abort(404)
        return send_file(path, as_attachment=True, download_name=doc["original_name"])
