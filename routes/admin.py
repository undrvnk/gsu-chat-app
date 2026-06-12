import sqlite3

from flask import abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from auth import roles_required, validate_registration
from db import query_all, query_db, query_one
from services.matching import add_notification



def register(app):
    # ----- Admin: faculty management -----
    @app.route("/admin/faculty", methods=("GET", "POST"))
    @roles_required("admin")
    def admin_faculty():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            full_name = request.form.get("full_name", "").strip()
            title = request.form.get("title", "").strip()
            password = request.form.get("password", "")
            error = validate_registration(username, email, password)
            if error:
                flash(error, "error")
            else:
                try:
                    query_db(
                        "INSERT INTO users "
                        "(username, email, full_name, password_hash, role, title, verified) "
                        "VALUES (?, ?, ?, ?, 'teacher', ?, 1)",
                        (username, email, full_name, generate_password_hash(password), title),
                    )
                    flash(f"Faculty account '{username}' created and verified.", "success")
                except sqlite3.IntegrityError:
                    flash("That username or email already exists.", "error")
            return redirect(url_for("admin_faculty"))
        faculty = query_all("SELECT * FROM users WHERE role = 'teacher' ORDER BY verified, full_name")
        return render_template("admin/faculty.html", faculty=faculty)
    
    @app.route("/admin/faculty/<int:user_id>/verify", methods=("POST",))
    @roles_required("admin")
    def admin_verify_faculty(user_id):
        faculty = query_one("SELECT * FROM users WHERE id = ? AND role = 'teacher'", (user_id,))
        if faculty is None:
            abort(404)
        new_state = 0 if faculty["verified"] else 1
        query_db("UPDATE users SET verified = ? WHERE id = ?", (new_state, user_id))
        if new_state:
            add_notification(user_id, "Your faculty account has been verified.", url_for("dashboard"))
            flash(f"Verified {faculty['full_name'] or faculty['username']}.", "success")
        else:
            flash(f"Revoked verification for {faculty['full_name'] or faculty['username']}.", "success")
        return redirect(url_for("admin_faculty"))
    
    # ----- Admin: program management -----
    @app.route("/admin/programs", methods=("GET", "POST"))
    @roles_required("admin")
    def admin_programs():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Program name is required.", "error")
                return redirect(url_for("admin_programs"))
            areas = ",".join(request.form.getlist("areas"))
            try:
                query_db(
                    "INSERT INTO programs (name, degree_type, research_areas, funding_available, deadline, description, url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        name,
                        request.form.get("degree_type", "M.S."),
                        areas,
                        1 if request.form.get("funding_available") else 0,
                        request.form.get("deadline", "").strip(),
                        request.form.get("description", "").strip(),
                        request.form.get("url", "").strip(),
                    ),
                )
                flash("Program created.", "success")
            except sqlite3.IntegrityError:
                flash("A program with that name already exists.", "error")
            return redirect(url_for("admin_programs"))
        programs = query_all("SELECT * FROM programs ORDER BY name")
        return render_template("admin/programs.html", programs=programs)
    
    @app.route("/admin/programs/<int:program_id>/edit", methods=("POST",))
    @roles_required("admin")
    def admin_edit_program(program_id):
        program = query_one("SELECT * FROM programs WHERE id = ?", (program_id,))
        if program is None:
            abort(404)
        areas = ",".join(request.form.getlist("areas"))
        query_db(
            "UPDATE programs SET degree_type = ?, research_areas = ?, funding_available = ?, "
            "deadline = ?, description = ?, url = ? WHERE id = ?",
            (
                request.form.get("degree_type", "M.S."),
                areas,
                1 if request.form.get("funding_available") else 0,
                request.form.get("deadline", "").strip(),
                request.form.get("description", "").strip(),
                request.form.get("url", "").strip(),
                program_id,
            ),
        )
        flash("Program updated.", "success")
        return redirect(url_for("admin_programs"))
    
    @app.route("/admin/programs/<int:program_id>/delete", methods=("POST",))
    @roles_required("admin")
    def admin_delete_program(program_id):
        query_db("DELETE FROM programs WHERE id = ?", (program_id,))
        flash("Program deleted.", "success")
        return redirect(url_for("admin_programs"))
