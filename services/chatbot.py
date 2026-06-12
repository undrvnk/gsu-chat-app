import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone

from config import BASE_DIR
from db import query_all

GSU_KNOWLEDGE = """
Georgia State University Department of Computer Science graduate offerings:
- M.S. in Computer Science: advanced training in computing fundamentals,
  processes, and applications. It includes focus areas such as AI, machine
  learning, deep learning, architecture, databases, data mining, big data,
  graphics and visualization, networks, security and privacy, parallel and
  distributed computing, cloud computing, cyber physical systems, IoT,
  programming languages, algorithms, simulation, and software engineering.
- Ph.D. in Computer Science: research-oriented program focused on advances in
  computer science, data science, cyber-security, and bioinformatics. Part-time
  study is possible, and competitive aid with tuition waivers may be available
  for full-time Ph.D. students.
- M.S. in Data Science and Analytics: includes a Big Data and Machine Learning
  concentration and is described as a three-semester program.
- Gateway to Computer Science Graduate Certificate: a one-year bridge program
  for students with non-computing bachelor's degrees who need preparation in
  programming, data structures, algorithms, and mathematics before MSCS study.

Helpful current facts:
- The CS department offers M.S. and Ph.D. degrees in Computer Science.
- Bioinformatics is available as a concentration for M.S. and Ph.D. CS.
- Security and Privacy is available as an M.S. CS concentration.
- The M.S. CS degree takes at least 31 semester hours, about 1.5-2 years, for
  applicants with a CS bachelor's degree. Students without a CS bachelor's
  degree may need at least 56 semester hours, about 2.5-3 years.
- M.S. CS application deadlines listed by GSU: Fall extended to July 15,
  Spring October 15, Summer March 1.
- Common M.S. CS application items include a baccalaureate degree in CS or
  equivalent preparation, a statement of background and goals, and three
  recommendation letters. International students may need TOEFL/IELTS.
- The Department of Computer Science office is at 25 Park Place, Suite 700,
  Atlanta, GA 30303. Phone: 404-413-5700.
- Director of Graduate Studies: Dr. Xiaojun Cao.

Official sources:
- https://csds.gsu.edu/graduate/
- https://www.gsu.edu/program/computer-science-ms/
- https://csds.gsu.edu/graduate-faqs/
"""


def load_extra_knowledge():
    """Concatenate every .md/.txt file under knowledge/ into the prompt context."""
    folder = os.path.join(BASE_DIR, "knowledge")
    chunks = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith((".md", ".txt")):
                try:
                    with open(os.path.join(folder, name), "r", encoding="utf-8") as fh:
                        text = fh.read().strip()
                except OSError:
                    continue
                if text:
                    chunks.append(text)
    return "\n\n".join(chunks)


EXTRA_KNOWLEDGE = load_extra_knowledge()
KNOWLEDGE_BASE = GSU_KNOWLEDGE + (
    "\n\nAdditional admissions Q&A:\n" + EXTRA_KNOWLEDGE if EXTRA_KNOWLEDGE else ""
)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def query_db(sql, params=()):
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return cursor


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db = sqlite3.connect(DATABASE)
    try:
        db.executescript(SCHEMA_SQL)
        db.commit()
    finally:
        db.close()
    ensure_schema_columns()
    normalize_admins()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    api_token TEXT UNIQUE,
    role TEXT NOT NULL DEFAULT 'student',
    major TEXT NOT NULL DEFAULT '',
    is_admin INTEGER NOT NULL DEFAULT 0,
    bio TEXT NOT NULL DEFAULT '',
    gpa TEXT NOT NULL DEFAULT '',
    prior_degree TEXT NOT NULL DEFAULT '',
    prior_institution TEXT NOT NULL DEFAULT '',
    test_scores TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    accepting_students INTEGER NOT NULL DEFAULT 0,
    lab_url TEXT NOT NULL DEFAULT '',
    publications_url TEXT NOT NULL DEFAULT '',
    verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    flagged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_interests (
    user_id INTEGER NOT NULL,
    interest TEXT NOT NULL,
    PRIMARY KEY (user_id, interest),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    degree_type TEXT NOT NULL DEFAULT 'M.S.',
    research_areas TEXT NOT NULL DEFAULT '',
    funding_available INTEGER NOT NULL DEFAULT 0,
    deadline TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS program_faculty (
    program_id INTEGER NOT NULL,
    faculty_id INTEGER NOT NULL,
    PRIMARY KEY (program_id, faculty_id),
    FOREIGN KEY (program_id) REFERENCES programs (id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookmarks (
    user_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, target_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    link TEXT NOT NULL DEFAULT '',
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    viewer_id INTEGER NOT NULL,
    viewed_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Started',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, program_id),
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (program_id) REFERENCES programs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS faculty_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chatbot_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_schema_columns():
    """Add any newer columns to a pre-existing users/chat_messages table."""
    db = sqlite3.connect(DATABASE)
    try:
        user_cols = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        additions = {
            "api_token": "TEXT",
            "role": "TEXT NOT NULL DEFAULT 'student'",
            "major": "TEXT NOT NULL DEFAULT ''",
            "bio": "TEXT NOT NULL DEFAULT ''",
            "gpa": "TEXT NOT NULL DEFAULT ''",
            "prior_degree": "TEXT NOT NULL DEFAULT ''",
            "prior_institution": "TEXT NOT NULL DEFAULT ''",
            "test_scores": "TEXT NOT NULL DEFAULT ''",
            "title": "TEXT NOT NULL DEFAULT ''",
            "accepting_students": "INTEGER NOT NULL DEFAULT 0",
            "lab_url": "TEXT NOT NULL DEFAULT ''",
            "publications_url": "TEXT NOT NULL DEFAULT ''",
            "verified": "INTEGER NOT NULL DEFAULT 0",
        }
        for col, decl in additions.items():
            if col not in user_cols:
                db.execute(f"ALTER TABLE users ADD COLUMN {col} {decl}")
        chat_cols = {row[1] for row in db.execute("PRAGMA table_info(chat_messages)").fetchall()}
        if "flagged" not in chat_cols:
            db.execute("ALTER TABLE chat_messages ADD COLUMN flagged INTEGER NOT NULL DEFAULT 0")
        db.commit()
    finally:
        db.close()


def normalize_admins():
    db = sqlite3.connect(DATABASE)
    try:
        db.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")
        # Faculty accounts that pre-date verification default to verified.
        db.execute("UPDATE users SET verified = 1 WHERE role = 'teacher' AND verified = 0 AND username IN ('advisor')")
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
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
                flash("You do not have access to that page.", "error")
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


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------
def get_user_interests(user_id):
    rows = query_all(
        "SELECT interest FROM user_interests WHERE user_id = ? ORDER BY interest",
        (user_id,),
    )
    return [r["interest"] for r in rows]


def set_user_interests(user_id, interests):
    valid = [i for i in interests if i in RESEARCH_AREAS]
    query_db("DELETE FROM user_interests WHERE user_id = ?", (user_id,))
    for interest in valid:
        query_db(
            "INSERT OR IGNORE INTO user_interests (user_id, interest) VALUES (?, ?)",
            (user_id, interest),
        )


def match_score(set_a, set_b):
    set_a, set_b = set(set_a), set(set_b)
    if not set_a or not set_b:
        return 0
    return round(100 * len(set_a & set_b) / len(set_a | set_b))


def add_notification(user_id, body, link=""):
    query_db(
        "INSERT INTO notifications (user_id, body, link) VALUES (?, ?, ?)",
        (user_id, body, link),
    )


def get_user_documents(user_id):
    rows = query_all(
        "SELECT * FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,),
    )
    latest = {}
    for row in rows:
        latest.setdefault(row["doc_type"], row)
    return latest


def get_missing_documents(user_id):
    have = set(get_user_documents(user_id).keys())
    return [d for d in DOC_TYPES if d not in have]


def recommended_faculty(student_id, limit=None):
    interests = set(get_user_interests(student_id))
    faculty = query_all(
        "SELECT * FROM users WHERE role = 'teacher' AND verified = 1 ORDER BY full_name"
    )
    results = []
    for f in faculty:
        areas = set(get_user_interests(f["id"]))
        score = match_score(interests, areas)
        results.append(
            {
                "user": f,
                "score": score,
                "matched": sorted(interests & areas),
                "areas": sorted(areas),
            }
        )
    results.sort(key=lambda r: (-r["score"], r["user"]["full_name"] or ""))
    if limit:
        results = results[:limit]
    return results


def notify_high_match_faculty(student, program, threshold=50):
    """Notify verified faculty when a strongly matching student applies."""
    student_interests = set(get_user_interests(student["id"]))
    if not student_interests:
        return
    faculty = query_all(
        "SELECT DISTINCT u.* FROM users u "
        "LEFT JOIN program_faculty pf ON pf.faculty_id = u.id AND pf.program_id = ? "
        "WHERE u.role = 'teacher' AND u.verified = 1 AND u.accepting_students = 1",
        (program["id"],),
    )
    name = student["full_name"] or student["username"]
    for f in faculty:
        score = match_score(student_interests, set(get_user_interests(f["id"])))
        if score >= threshold:
            add_notification(
                f["id"],
                f"High match ({score}%): {name} applied to {program['name']}.",
                url_for("view_profile", user_id=student["id"]),
            )


def is_bookmarked(user_id, target_id):
    return query_one(
        "SELECT 1 FROM bookmarks WHERE user_id = ? AND target_id = ?",
        (user_id, target_id),
    ) is not None


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------
def dynamic_knowledge():
    parts = []
    try:
        programs = query_all(
            "SELECT name, degree_type, research_areas, funding_available, deadline, description "
            "FROM programs ORDER BY name"
        )
    except sqlite3.Error:
        programs = []
    if programs:
        lines = ["Graduate programs currently listed in this system:"]
        for p in programs:
            funding = "yes" if p["funding_available"] else "no"
            lines.append(
                f"- {p['name']} ({p['degree_type']}). Research areas: {p['research_areas']}. "
                f"Funding available: {funding}. Deadlines: {p['deadline']}. {p['description']}"
            )
        parts.append("\n".join(lines))
    try:
        corrections = query_all("SELECT content FROM chatbot_corrections ORDER BY id")
    except sqlite3.Error:
        corrections = []
    if corrections:
        parts.append(
            "Administrator corrections (authoritative; override any conflicting info):\n"
            + "\n".join("- " + c["content"] for c in corrections)
        )
    return "\n\n".join(parts)


def llm_is_enabled():
    if not os.environ.get("OPENAI_API_KEY"):
        return False
    if os.environ.get("ALLOW_PAID_MODELS"):
        return True
    return os.environ.get("OPENAI_MODEL", "").endswith(":free")


DEFAULT_FREE_FALLBACKS = [
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
]


def candidate_models():
    primary = os.environ.get("OPENAI_MODEL", "")
    extra = os.environ.get("OPENAI_FALLBACK_MODELS", "")
    fallbacks = [m.strip() for m in extra.split(",") if m.strip()] or DEFAULT_FREE_FALLBACKS
    ordered = [primary] + fallbacks
    allow_paid = bool(os.environ.get("ALLOW_PAID_MODELS"))
    seen, result = set(), []
    for model in ordered:
        if not model or model in seen:
            continue
        seen.add(model)
        if allow_paid or model.endswith(":free"):
            result.append(model)
    return result


def call_openai_compatible_llm(message, extra_knowledge=""):
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "GSU CS Grad Chat",
    }
    knowledge = KNOWLEDGE_BASE + ("\n\n" + extra_knowledge if extra_knowledge else "")
    system_prompt = (
        "You are an AI assistant for Georgia State University Computer Science "
        "graduate programs. Use only the facts in the provided knowledge. If a "
        "question needs current official confirmation, say to verify with GSU. "
        "If asked to compare programs, summarize the key differences clearly. If "
        "asked how to apply, give concise numbered steps (create an account, "
        "complete your profile, pick a program, upload resume/transcript/statement "
        "of purpose, submit before the deadline, then track your status).\n"
        "Formatting rules: reply in short, friendly plain text for a small chat "
        "window. Do NOT use markdown tables or the '|' character. Avoid heavy "
        "symbols. You may use simple '- ' bullet points and **bold** for a few key "
        "terms, but keep formatting minimal and readable.\n"
        "Knowledge:\n" + knowledge
    )

    for model in candidate_models():
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError):
            continue
    return None


def generate_chat_answer(message):
    if llm_is_enabled():
        reply = call_openai_compatible_llm(message, extra_knowledge=dynamic_knowledge())
        if reply:
            return reply

    lowered = message.lower()
    if "deadline" in lowered:
        return (
            "For GSU M.S. in Computer Science, the currently listed deadlines are "
            "Fall: July 15, Spring: October 15, and Summer: March 1. Always confirm "
            "on the official program page before applying."
        )
    if ("non" in lowered and "cs" in lowered) or "background" in lowered:
        return (
            "GSU welcomes capable students from non-CS backgrounds, but applicants "
            "are expected to have core CS foundations. Missing foundation courses "
            "may be assigned before regular M.S. or Ph.D. coursework. The Gateway "
            "to Computer Science certificate is a one-year bridge option."
        )
    if "fund" in lowered or "assistantship" in lowered or "tuition" in lowered:
        return (
            "Accepted students may be considered for funding, including fellowships, "
            "teaching assistantships, research assistantships, office assistantships, "
            "and on-campus jobs. Some assistantships can include tuition waivers."
        )
    if "apply" in lowered or "step" in lowered:
        return (
            "To apply: 1) create an account, 2) complete your profile and research "
            "interests, 3) pick a program, 4) upload your resume, transcript, and "
            "statement of purpose, 5) submit before the deadline, 6) track your status."
        )
    if "program" in lowered or "degree" in lowered or "graduate" in lowered:
        return (
            "GSU Computer Science graduate options include the M.S. in Computer "
            "Science, Ph.D. in Computer Science, M.S. in Data Science and Analytics, "
            "and the Gateway to Computer Science Graduate Certificate."
        )
    return (
        "I can help with Georgia State CS graduate-program questions about degrees, "
        "deadlines, admissions preparation, concentrations, funding, and contacts. "
        "Try asking: 'What programs are offered?' or 'How do I apply?'"
    )


def now_iso():
    return datetime.now(timezone.utc).isoformat()


