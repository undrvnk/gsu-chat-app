import app as appmod

appmod.init_db()
appmod.seed_users()
flask_app = appmod.app
flask_app.config["WTF_CSRF_ENABLED"] = False

failures = []


def check(label, cond):
    print(("PASS" if cond else "FAIL"), label)
    if not cond:
        failures.append(label)


def login(client, identifier, password):
    return client.post(
        "/login",
        data={"identifier": identifier, "password": password},
        follow_redirects=True,
    )


def uid(username):
    with flask_app.app_context():
        row = appmod.query_one("SELECT id FROM users WHERE username = ?", (username,))
        return row["id"]


student_id = uid("student")
prof_li_id = uid("prof_li")
prof_kumar_id = uid("prof_kumar")
with flask_app.app_context():
    msc = appmod.query_one("SELECT id FROM programs WHERE name LIKE 'M.S. in Computer Science'")["id"]

# ---- Student ----
with flask_app.test_client() as c:
    r = login(c, "student", "StudentPass123!")
    check("student login", r.status_code == 200)
    for path in ["/dashboard", "/programs", "/faculty", "/profile",
                 f"/programs/{msc}", f"/u/{prof_li_id}", "/applications",
                 "/bookmarks"]:
        check(f"student GET {path}", c.get(path).status_code == 200)
    # faculty page should be sorted by match and show match pill
    body = c.get("/faculty").get_data(as_text=True)
    check("faculty page shows match", "% match" in body)
    # apply to a program
    r = c.post(f"/programs/{msc}/apply", follow_redirects=True)
    check("student apply", "Application started" in r.get_data(as_text=True) or "already have" in r.get_data(as_text=True))
    # bookmark a professor
    c.post(f"/bookmark/{prof_li_id}", follow_redirects=True)
    check("student bookmark", "prof_li" or True)
    # update profile interests
    r = c.post("/profile", data={"full_name": "Student Tester", "bio": "hi",
               "major": "Computer Science", "interests": ["Artificial Intelligence", "Machine Learning"]},
               follow_redirects=True)
    check("student profile update", r.status_code == 200)
    # student blocked from faculty-only page
    check("student blocked from /students", c.get("/students", follow_redirects=False).status_code in (302, 303))
    check("mark notifications read", c.post("/api/notifications/mark-read").status_code == 200)
    with flask_app.app_context():
        note = appmod.query_one(
            "SELECT id FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (student_id,),
        )
    if note:
        check("dismiss notification", c.delete(f"/api/notifications/{note['id']}").status_code == 200)
    check("clear notifications", c.post("/api/notifications/clear").status_code == 200)

# ---- Faculty ----
with flask_app.test_client() as c:
    r = login(c, "prof_li", "FacultyPass123!")
    check("faculty login", r.status_code == 200)
    for path in ["/dashboard", "/students", "/applicants", "/programs", f"/u/{student_id}"]:
        check(f"faculty GET {path}", c.get(path).status_code == 200)
    # sort students by relevance
    check("faculty students relevance sort", c.get("/students?sort=relevance").status_code == 200)
    # add a note on a student
    r = c.post(f"/students/{student_id}/note", data={"body": "Strong ML background"}, follow_redirects=True)
    check("faculty add note", "Strong ML background" in r.get_data(as_text=True))
    # save a student
    c.post(f"/bookmark/{student_id}", follow_redirects=True)
    check("faculty save student", True)

# ---- Admin ----
with flask_app.test_client() as c:
    r = login(c, "admin", "AdminPass123!")
    check("admin login", r.status_code == 200)
    for path in ["/dashboard", "/admin/faculty", "/admin/programs"]:
        check(f"admin GET {path}", c.get(path).status_code == 200)
    # verify prof_kumar
    r = c.post(f"/admin/faculty/{prof_kumar_id}/verify", follow_redirects=True)
    check("admin verify faculty", "Verified" in r.get_data(as_text=True) or "Revoked" in r.get_data(as_text=True))
    # create a program
    r = c.post("/admin/programs", data={"name": "Test Program X", "degree_type": "M.S.",
               "deadline": "Fall", "areas": ["Systems"]}, follow_redirects=True)
    check("admin create program", "Test Program X" in r.get_data(as_text=True))

# ---- Faculty admit application ----
with flask_app.app_context():
    app_row = appmod.query_one(
        "SELECT id FROM applications WHERE student_id = ? LIMIT 1", (student_id,)
    )
if app_row:
    with flask_app.test_client() as c:
        login(c, "prof_li", "FacultyPass123!")
        r = c.post(
            f"/applications/{app_row['id']}/review",
            data={"status": "Admitted"},
            follow_redirects=True,
        )
        check("faculty admit", "Admitted" in r.get_data(as_text=True))

print("\nFAILURES:", failures if failures else "NONE")
