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
    # ----- Faculty: browse students -----
    @app.route("/students")
    @roles_required("teacher", "admin")
    def students():
        selected_major = request.args.get("major", "").strip()
        selected_interest = request.args.get("interest", "").strip()
        sort = request.args.get("sort", "name").strip()
        rows = query_all("SELECT * FROM users WHERE role = 'student' ORDER BY full_name")
        my_areas = set(get_user_interests(g.user["id"]))
        cards = []
        for s in rows:
            if selected_major and selected_major in MAJORS and s["major"] != selected_major:
                continue
            areas = get_user_interests(s["id"])
            if selected_interest and selected_interest not in areas:
                continue
            cards.append(
                {
                    "user": s,
                    "interests": areas,
                    "score": match_score(my_areas, set(areas)),
                    "matched": sorted(my_areas & set(areas)),
                    "saved": is_bookmarked(g.user["id"], s["id"]),
                }
            )
        if sort == "relevance":
            cards.sort(key=lambda c: (-c["score"], c["user"]["full_name"] or ""))
        elif sort == "gpa":
            def gpa_key(c):
                try:
                    return -float(c["user"]["gpa"])
                except (TypeError, ValueError):
                    return 0.0
            cards.sort(key=gpa_key)
        else:
            cards.sort(key=lambda c: (c["user"]["full_name"] or "").lower())
        return render_template(
            "students.html",
            cards=cards,
            selected_major=selected_major,
            selected_interest=selected_interest,
            sort=sort,
        )
    
    @app.route("/students/<int:student_id>/note", methods=("POST",))
    @roles_required("teacher", "admin")
    def add_note(student_id):
        student = query_one("SELECT * FROM users WHERE id = ? AND role = 'student'", (student_id,))
        if student is None:
            abort(404)
        body = request.form.get("body", "").strip()
        if body:
            query_db(
                "INSERT INTO faculty_notes (faculty_id, student_id, body) VALUES (?, ?, ?)",
                (g.user["id"], student_id, body),
            )
            flash("Note added.", "success")
        return redirect(url_for("view_profile", user_id=student_id))
    
    @app.route("/notes/<int:note_id>/edit", methods=("POST",))
    @roles_required("teacher", "admin")
    def edit_note(note_id):
        note = query_one("SELECT * FROM faculty_notes WHERE id = ?", (note_id,))
        if note is None:
            abort(404)
        if g.user["role"] != "admin" and note["faculty_id"] != g.user["id"]:
            flash("You can only edit your own notes.", "error")
            return redirect(url_for("view_profile", user_id=note["student_id"]))
        body = request.form.get("body", "").strip()
        if not body:
            flash("Note cannot be empty.", "error")
            return redirect(url_for("view_profile", user_id=note["student_id"]))
        query_db("UPDATE faculty_notes SET body = ? WHERE id = ?", (body, note_id))
        flash("Note updated.", "success")
        return redirect(url_for("view_profile", user_id=note["student_id"]))
    
    @app.route("/notes/<int:note_id>/delete", methods=("POST",))
    @roles_required("teacher", "admin")
    def delete_note(note_id):
        note = query_one("SELECT * FROM faculty_notes WHERE id = ?", (note_id,))
        if note is None:
            abort(404)
        if g.user["role"] != "admin" and note["faculty_id"] != g.user["id"]:
            flash("You can only delete your own notes.", "error")
            return redirect(url_for("view_profile", user_id=note["student_id"]))
        student_id = note["student_id"]
        query_db("DELETE FROM faculty_notes WHERE id = ?", (note_id,))
        flash("Note deleted.", "success")
        return redirect(url_for("view_profile", user_id=student_id))
    
    @app.route("/applicants")
    @roles_required("teacher", "admin")
    def applicants():
        rows = query_all(
            "SELECT a.*, u.full_name AS student_name, u.id AS student_id, u.email AS student_email, "
            "u.major AS major, u.gpa AS gpa, p.name AS program_name "
            "FROM applications a JOIN users u ON u.id = a.student_id "
            "JOIN programs p ON p.id = a.program_id "
            "ORDER BY a.updated_at DESC"
        )
        return render_template("applicants.html", applications=rows)
    
    @app.route("/applications/<int:app_id>/review", methods=("POST",))
    @roles_required("teacher", "admin")
    def review_application(app_id):
        application = query_one(
            "SELECT a.*, p.name AS program_name, u.full_name AS student_name "
            "FROM applications a "
            "JOIN programs p ON p.id = a.program_id "
            "JOIN users u ON u.id = a.student_id "
            "WHERE a.id = ?",
            (app_id,),
        )
        if application is None:
            abort(404)
        status = request.form.get("status", "").strip()
        if status not in FACULTY_REVIEW_STATUSES:
            flash("Invalid review status.", "error")
            return redirect(request.referrer or url_for("applicants"))
        query_db(
            "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, app_id),
        )
        reviewer = g.user["full_name"] or g.user["username"]
        if status == "Under Review" and application["status"] in ("Admitted", "Rejected"):
            flash_msg = "Admission decision undone. Application is under review again."
        else:
            flash_msg = f"Application marked as {status}."
        add_notification(
            application["student_id"],
            f"{reviewer} updated your {application['program_name']} application to: {status}.",
            url_for("applications"),
        )
        flash(flash_msg, "success")
        return redirect(request.referrer or url_for("applicants"))
