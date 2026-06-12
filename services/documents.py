import os

from config import ALLOWED_EXTENSIONS, DOC_TYPES
from db import query_all


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


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS
