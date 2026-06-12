from flask import url_for

from config import RESEARCH_AREAS
from db import query_all, query_db, query_one


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
