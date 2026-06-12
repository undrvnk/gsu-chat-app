import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VENDOR_SITE = os.path.join(BASE_DIR, "vendor", "usr", "lib", "python3", "dist-packages")
if os.path.isdir(VENDOR_SITE) and VENDOR_SITE not in sys.path:
    sys.path.insert(0, VENDOR_SITE)

UPLOAD_DIR = os.path.join(BASE_DIR, "instance", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"}

MAJORS = [
    "Computer Science",
    "Data Science and Analytics",
    "Cybersecurity",
    "Bioinformatics",
    "Software Engineering",
    "Undecided",
]

RESEARCH_AREAS = [
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
    "Systems",
    "Security & Privacy",
    "Networks",
    "Databases",
    "Bioinformatics",
    "Computer Vision",
    "Natural Language Processing",
    "Human-Computer Interaction",
    "Theory & Algorithms",
    "Software Engineering",
    "Cloud Computing",
]

DEGREE_TYPES = ["M.S.", "Ph.D.", "Certificate"]

DOC_TYPES = ["resume", "transcript", "sop"]
DOC_LABELS = {
    "resume": "Resume / CV",
    "transcript": "Transcript",
    "sop": "Statement of Purpose",
}

APP_STATUSES = ["Started", "Submitted", "Under Review", "Admitted", "Rejected"]
STUDENT_APP_STATUSES = ["Started", "Submitted"]
FACULTY_REVIEW_STATUSES = ["Under Review", "Admitted", "Rejected"]


def load_dotenv(path=None):
    """Minimal .env loader so secrets stay out of source. No external deps."""
    path = path or os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()

DATABASE = os.environ.get(
    "DATABASE_URL", os.path.join(BASE_DIR, "instance", "gsu_chat.sqlite3")
)
