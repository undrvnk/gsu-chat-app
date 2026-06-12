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
    # ----- Faculty directory + matching + bookmarks -----
    @app.route("/faculty")
    @login_required
    def faculty_directory():
        area = request.args.get("area", "").strip()
        accepting = request.args.get("accepting", "").strip()
        my_interests = set(get_user_interests(g.user["id"]))
        rows = query_all(
            "SELECT * FROM users WHERE role = 'teacher' AND verified = 1 ORDER BY full_name"
        )
        cards = []
        for f in rows:
            areas = get_user_interests(f["id"])
            if area and area not in areas:
                continue
            if accepting == "1" and not f["accepting_students"]:
                continue
            cards.append(
                {
                    "user": f,
                    "areas": areas,
                    "score": match_score(my_interests, set(areas)),
                    "matched": sorted(my_interests & set(areas)),
                    "bookmarked": is_bookmarked(g.user["id"], f["id"]),
                }
            )
        if g.user["role"] == "student":
            cards.sort(key=lambda c: (-c["score"], c["user"]["full_name"] or ""))
        return render_template(
            "faculty.html",
            cards=cards,
            selected_area=area,
            selected_accepting=accepting,
        )
    
    @app.route("/bookmark/<int:user_id>", methods=("POST",))
    @login_required
    def toggle_bookmark(user_id):
        target = query_one("SELECT id FROM users WHERE id = ?", (user_id,))
        if target is None:
            abort(404)
        if is_bookmarked(g.user["id"], user_id):
            query_db(
                "DELETE FROM bookmarks WHERE user_id = ? AND target_id = ?",
                (g.user["id"], user_id),
            )
            flash("Bookmark removed.", "success")
        else:
            query_db(
                "INSERT OR IGNORE INTO bookmarks (user_id, target_id) VALUES (?, ?)",
                (g.user["id"], user_id),
            )
            flash("Bookmarked.", "success")
        return redirect(request.referrer or url_for("dashboard"))
    
    @app.route("/bookmarks")
    @login_required
    def bookmarks():
        rows = query_all(
            "SELECT u.* FROM bookmarks b JOIN users u ON u.id = b.target_id "
            "WHERE b.user_id = ? ORDER BY u.full_name",
            (g.user["id"],),
        )
        return render_template("bookmarks.html", people=rows)
    
    # ----- Application tracking (student) -----
    @app.route("/applications")
    @roles_required("student")
    def applications():
        rows = query_all(
            "SELECT a.*, p.name AS program_name, p.deadline AS deadline, p.degree_type AS degree_type "
            "FROM applications a JOIN programs p ON p.id = a.program_id "
            "WHERE a.student_id = ? ORDER BY a.updated_at DESC",
            (g.user["id"],),
        )
        missing = [DOC_LABELS[d] for d in get_missing_documents(g.user["id"])]
        all_programs = query_all("SELECT id, name FROM programs ORDER BY name")
        applied_ids = {r["program_id"] for r in rows}
        available = [p for p in all_programs if p["id"] not in applied_ids]
        return render_template(
            "applications.html",
            applications=rows,
            missing_docs=missing,
            statuses=STUDENT_APP_STATUSES,
            available_programs=available,
        )
    
    @app.route("/applications/<int:app_id>/status", methods=("POST",))
    @roles_required("student")
    def update_application_status(app_id):
        application = query_one(
            "SELECT * FROM applications WHERE id = ? AND student_id = ?",
            (app_id, g.user["id"]),
        )
        if application is None:
            abort(404)
        status = request.form.get("status", "")
        if status not in STUDENT_APP_STATUSES:
            flash("You can only mark your application as Started or Submitted.", "error")
            return redirect(url_for("applications"))
        query_db(
            "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, app_id),
        )
        flash("Application status updated.", "success")
        return redirect(url_for("applications"))
    
    @app.route("/applications/<int:app_id>/delete", methods=("POST",))
    @roles_required("student")
    def delete_application(app_id):
        query_db(
            "DELETE FROM applications WHERE id = ? AND student_id = ?",
            (app_id, g.user["id"]),
        )
        flash("Application removed.", "success")
        return redirect(url_for("applications"))
