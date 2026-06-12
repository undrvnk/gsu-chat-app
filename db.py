import os
import sqlite3

from flask import g

from config import DATABASE, UPLOAD_DIR

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
        db.execute(
            "UPDATE users SET verified = 1 WHERE role = 'teacher' AND verified = 0 "
            "AND username IN ('advisor')"
        )
        db.commit()
    finally:
        db.close()


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
