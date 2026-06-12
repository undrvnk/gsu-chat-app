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
    # ----- Program discovery -----
    @app.route("/programs")
    @login_required
    def programs():
        area = request.args.get("area", "").strip()
        degree = request.args.get("degree", "").strip()
        funding = request.args.get("funding", "").strip()
        rows = query_all("SELECT * FROM programs ORDER BY name")
        filtered = []
        for p in rows:
            if area and area not in [a.strip() for a in p["research_areas"].split(",")]:
                continue
            if degree and p["degree_type"] != degree:
                continue
            if funding == "1" and not p["funding_available"]:
                continue
            filtered.append(p)
        return render_template(
            "programs.html",
            programs=filtered,
            selected_area=area,
            selected_degree=degree,
            selected_funding=funding,
        )
    
    @app.route("/programs/<int:program_id>")
    @login_required
    def program_detail(program_id):
        program = query_one("SELECT * FROM programs WHERE id = ?", (program_id,))
        if program is None:
            abort(404)
        faculty = query_all(
            "SELECT u.* FROM program_faculty pf JOIN users u ON u.id = pf.faculty_id "
            "WHERE pf.program_id = ? AND u.verified = 1 ORDER BY u.full_name",
            (program_id,),
        )
        applied = None
        if g.user["role"] == "student":
            applied = query_one(
                "SELECT * FROM applications WHERE student_id = ? AND program_id = ?",
                (g.user["id"], program_id),
            )
        return render_template(
            "program_detail.html",
            program=program,
            areas=[a.strip() for a in program["research_areas"].split(",") if a.strip()],
            faculty=faculty,
            applied=applied,
        )
    
    @app.route("/programs/<int:program_id>/apply", methods=("POST",))
    @roles_required("student")
    def apply_program(program_id):
        program = query_one("SELECT * FROM programs WHERE id = ?", (program_id,))
        if program is None:
            abort(404)
        try:
            query_db(
                "INSERT INTO applications (student_id, program_id) VALUES (?, ?)",
                (g.user["id"], program_id),
            )
            flash(f"Application started for {program['name']}.", "success")
            notify_high_match_faculty(g.user, program)
        except sqlite3.IntegrityError:
            flash("You already have an application for that program.", "error")
        return redirect(url_for("applications"))
