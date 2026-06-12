import sqlite3

from config import DATABASE
from db import normalize_admins
from werkzeug.security import generate_password_hash

def seed_users():
    """Idempotent demo data: users, interests, faculty profiles, and programs."""
    users = [
        # username, email, full_name, password, role, major, is_admin
        ("admin", "admin@example.com", "Admin User", "AdminPass123!", "admin", "", 1),
        ("advisor", "advisor@example.com", "Graduate Advisor", "AdvisorPass123!", "teacher", "", 0),
        ("student", "student@example.com", "Student Tester", "StudentPass123!", "student", "Computer Science", 0),
        ("maya", "maya@example.com", "Maya Patel", "StudentPass123!", "student", "Data Science and Analytics", 0),
        ("leo", "leo@example.com", "Leo Garcia", "StudentPass123!", "student", "Cybersecurity", 0),
        ("nina", "nina@example.com", "Nina Wright", "StudentPass123!", "student", "Computer Science", 0),
        ("prof_cao", "cao@example.com", "Dr. Xiaojun Cao", "FacultyPass123!", "teacher", "", 0),
        ("prof_li", "li@example.com", "Dr. Wei Li", "FacultyPass123!", "teacher", "", 0),
        ("prof_chen", "chen@example.com", "Dr. Mei Chen", "FacultyPass123!", "teacher", "", 0),
        ("prof_kumar", "kumar@example.com", "Dr. Raj Kumar", "FacultyPass123!", "teacher", "", 0),
    ]
    faculty_profiles = {
        "advisor": ("Graduate Coordinator", 1, 1, "Advises incoming graduate students."),
        "prof_cao": ("Professor & Director of Graduate Studies", 1, 1, "Research in networks, security, and optical systems."),
        "prof_li": ("Associate Professor", 1, 1, "Machine learning and data-driven systems."),
        "prof_chen": ("Assistant Professor", 0, 1, "Bioinformatics and computational biology."),
        "prof_kumar": ("Assistant Professor", 1, 0, "Distributed systems and cloud computing."),
    }
    interests_map = {
        "student": ["Artificial Intelligence", "Machine Learning"],
        "maya": ["Data Science", "Machine Learning"],
        "leo": ["Security & Privacy", "Networks"],
        "nina": ["Bioinformatics", "Data Science"],
        "advisor": ["Artificial Intelligence", "Machine Learning"],
        "prof_cao": ["Networks", "Security & Privacy"],
        "prof_li": ["Machine Learning", "Data Science"],
        "prof_chen": ["Bioinformatics", "Data Science"],
        "prof_kumar": ["Systems", "Cloud Computing"],
    }
    student_profiles = {
        "student": ("3.7", "B.S. Computer Science", "Georgia State University", "GRE 320, TOEFL 105", "Aspiring ML researcher interested in applied AI."),
        "maya": ("3.9", "B.S. Statistics", "Emory University", "GRE 327", "Data scientist focused on predictive modeling."),
        "leo": ("3.5", "B.S. Cybersecurity", "Kennesaw State University", "GRE 312", "Security enthusiast exploring network defense."),
        "nina": ("3.8", "B.S. Biology", "University of Georgia", "GRE 318, TOEFL 110", "Bridging biology and computing through bioinformatics."),
    }
    programs = [
        ("M.S. in Computer Science", "M.S.",
         "Artificial Intelligence,Machine Learning,Systems,Security & Privacy,Databases,Software Engineering",
         1, "Fall: July 15; Spring: October 15; Summer: March 1",
         "Advanced graduate study across the breadth of computer science.",
         "https://cas.gsu.edu/program/computer-science-ms/"),
        ("Ph.D. in Computer Science", "Ph.D.",
         "Artificial Intelligence,Security & Privacy,Data Science,Bioinformatics,Networks",
         1, "Fall only (apply by January 15)",
         "Research-oriented doctoral program with competitive funding.",
         "https://csds.gsu.edu/graduate/"),
        ("M.S. in Data Science and Analytics", "M.S.",
         "Data Science,Machine Learning",
         0, "Fall: July 15; Spring: October 15",
         "Three-semester program with a Big Data and Machine Learning concentration.",
         "https://csds.gsu.edu/graduate/"),
        ("Gateway to Computer Science Graduate Certificate", "Certificate",
         "Software Engineering",
         0, "Rolling admission",
         "One-year bridge program for students from non-computing backgrounds.",
         "https://csds.gsu.edu/graduate/"),
    ]
    program_links = {
        "M.S. in Computer Science": ["prof_li", "prof_kumar", "advisor"],
        "Ph.D. in Computer Science": ["prof_cao", "prof_chen", "prof_li"],
        "M.S. in Data Science and Analytics": ["prof_li", "prof_chen"],
    }

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    try:
        for username, email, full_name, password, role, major, is_admin in users:
            db.execute(
                "INSERT OR IGNORE INTO users "
                "(username, email, full_name, password_hash, role, major, is_admin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (username, email, full_name, generate_password_hash(password), role, major, is_admin),
            )

        def uid(username):
            row = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            return row["id"] if row else None

        for username, (title, accepting, verified, bio) in faculty_profiles.items():
            db.execute(
                "UPDATE users SET title = ?, accepting_students = ?, verified = ?, bio = ? "
                "WHERE username = ?",
                (title, accepting, verified, bio, username),
            )
        for username, (gpa, degree, inst, scores, bio) in student_profiles.items():
            db.execute(
                "UPDATE users SET gpa = ?, prior_degree = ?, prior_institution = ?, "
                "test_scores = ?, bio = ? WHERE username = ?",
                (gpa, degree, inst, scores, bio, username),
            )
        for username, interests in interests_map.items():
            user_id = uid(username)
            if user_id is None:
                continue
            for interest in interests:
                db.execute(
                    "INSERT OR IGNORE INTO user_interests (user_id, interest) VALUES (?, ?)",
                    (user_id, interest),
                )
        for name, degree, areas, funding, deadline, desc, url in programs:
            db.execute(
                "INSERT OR IGNORE INTO programs "
                "(name, degree_type, research_areas, funding_available, deadline, description, url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, degree, areas, funding, deadline, desc, url),
            )
        for program_name, faculty_usernames in program_links.items():
            prow = db.execute("SELECT id FROM programs WHERE name = ?", (program_name,)).fetchone()
            if prow is None:
                continue
            for fu in faculty_usernames:
                fid = uid(fu)
                if fid:
                    db.execute(
                        "INSERT OR IGNORE INTO program_faculty (program_id, faculty_id) VALUES (?, ?)",
                        (prow["id"], fid),
                    )
        db.commit()
    finally:
        db.close()
    normalize_admins()

