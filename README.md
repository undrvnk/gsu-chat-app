# GSU CS Grad Portal

A Flask portal for Georgia State University Computer Science graduate
admissions. Students build profiles and get matched to faculty, faculty
discover and review applicants, admins manage the system, and an AI chatbot
answers admissions questions.

## Install

On the server, production uses **nginx** (port 5000) in front of **gunicorn**:

```bash
sudo apt update
sudo apt install -y python3-flask gunicorn nginx
```

A no-root local install is also prepared in `vendor/` for development machines
without system packages.

## Initialize and Seed the Database

```bash
python3 -c 'import app; app.init_db()'
python3 -c 'import app; app.init_db(); app.seed_users()'
```

Seed logins:

- `admin` / `AdminPass123!` (admin)
- `advisor` / `AdvisorPass123!` (faculty, verified)
- `prof_cao` / `FacultyPass123!` (faculty, verified, accepting)
- `prof_li` / `FacultyPass123!` (faculty, verified, accepting)
- `prof_chen` / `FacultyPass123!` (faculty, verified)
- `prof_kumar` / `FacultyPass123!` (faculty, **unverified** - verify via admin)
- `student` / `StudentPass123!` (student, Computer Science)
- `maya` / `StudentPass123!` (student, Data Science and Analytics)
- `leo` / `StudentPass123!` (student, Cybersecurity)
- `nina` / `StudentPass123!` (student, Computer Science)

## Run the App

### Production (server)

Do **not** use `python3 app.py` on the live server. One-time setup:

```bash
bash scripts/setup-nginx.sh
```

That installs a **systemd** service (`gsu-chat-app`) running gunicorn, plus nginx
on port **5000** (matches the existing router port-forward rule).

Day-to-day commands:

```bash
sudo systemctl status gsu-chat-app    # is it running?
sudo systemctl restart gsu-chat-app   # after code changes
sudo systemctl reload nginx
journalctl -u gsu-chat-app -n 50      # view logs
```

The app starts automatically on boot.

### Local development

For quick testing on your laptop:

```bash
FLASK_DEBUG=1 python3 app.py
```

Open `http://127.0.0.1:5000`.

### Live URLs

```text
http://70.133.221.153:5000     # public (any network)
http://192.168.1.165:5000      # local network only (faster at home)
```

On your home Wi-Fi, prefer the `192.168...` address. The public IP can be slow
from inside your own network (router hairpin NAT).

## CI/CD (GitHub Actions)

Pushes and pull requests to `main` run `smoke_test.py` automatically (see
`.github/workflows/ci.yml`).

```bash
git add .
git commit -m "Describe your change"
git push    # triggers CI on GitHub
```

Optional auto-deploy is configured in `.github/workflows/deploy.yml` but **off
by default**. To enable it, set repository variable `DEPLOY_ENABLED=true` and
add secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`.

## LLM Connection (OpenRouter, free models only)

Configuration lives in a git-ignored `.env` file (see `.env.example`):

```bash
OPENAI_API_KEY=sk-or-...                 # OpenRouter key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

Cost safety: the app only calls the LLM when `OPENAI_MODEL` ends with `:free`.
If the primary free model is rate-limited, it automatically fails over to other
free models, and if all fail it falls back to built-in knowledge. To allow a
paid model you must explicitly set `ALLOW_PAID_MODELS=1`.

## Training the bot on your own Q&A

Drop any `.md` or `.txt` file into the `knowledge/` folder (e.g.
`knowledge/admissions_qa.md`). Its contents are appended to the chatbot's
knowledge base on startup. Paste the Q&A pairs from your admissions document
there and restart:

```bash
sudo systemctl restart gsu-chat-app
```

---

## User stories

Stories below reflect what the portal supports today. Each story maps to a
concrete page, action, or API endpoint in the running app.

### Public and landing

- **As a visitor**, I want to see a landing page with GSU branding and a short
  overview of graduate programs, so that I understand what the portal offers
  before creating an account.
- **As a visitor**, I want to read featured program summaries on the home page,
  so that I can get a quick sense of M.S., Ph.D., and certificate options.

### Account registration and login

- **As a prospective student**, I want to register with username, email, full
  name, password, and intended major, so that I can start building my profile
  immediately after sign-up.
- **As a prospective faculty member**, I want to register as faculty without
  selecting a student major, so that my account is created with the correct role.
- **As a newly registered faculty member**, I want my account to remain hidden
  from the student-facing faculty directory until an admin verifies me, so that
  only approved advisors appear to applicants.
- **As a newly registered faculty member**, I want admins to receive a
  notification that my account needs verification, so that approval does not
  depend on me following up manually.
- **As any user**, I want to log in with either my username or email plus
  password, so that I am not forced to remember which identifier I used at
  registration.
- **As any logged-in user**, I want to log out from the top navigation, so that
  I can end my session on a shared machine.

### Dashboard (all roles)

- **As a logged-in user**, I want a role-specific dashboard, so that I see the
  tools and summaries most relevant to me as a student, faculty member, or
  admin.
- **As any logged-in user**, I want my research interests displayed on the
  dashboard (or a prompt to add them), so that I am reminded to keep my profile
  current for matching.

### Student: profile and documents

- **As a student**, I want to edit my profile with full name, email, and bio,
  so that faculty can learn who I am beyond application paperwork.
- **As a student**, I want to record my academic background (major, GPA, prior
  degree, prior institution, test scores), so that faculty can evaluate my
  qualifications in context.
- **As a student**, I want to select multiple research interests from a shared
  list of CS research areas, so that the portal can match me to relevant faculty.
- **As a student**, I want to upload a resume/CV, transcript, and statement of
  purpose (pdf, doc, docx, txt, rtf, odt; max 8 MB), so that my application
  materials live in one place.
- **As a student**, I want to replace a document by uploading a new file of the
  same type, so that I can fix mistakes without contacting staff.
- **As a student**, I want to download documents I have uploaded, so that I
  can confirm what is on file.

### Student: program discovery and applications

- **As a student**, I want to browse all graduate programs, so that I can
  compare degree options in one place.
- **As a student**, I want to filter programs by research area, degree type
  (M.S., Ph.D., Certificate), and funding availability, so that I can narrow
  the list to programs that fit my goals.
- **As a student**, I want to open a program detail page with description,
  deadlines, research areas, funding info, and associated faculty, so that I can
  decide whether to apply.
- **As a student**, I want to start an application for a program from its detail
  page, so that tracking begins as soon as I commit to applying.
- **As a student**, I want to be prevented from starting duplicate applications
  to the same program, so that my application list stays accurate.
- **As a student**, I want to view all of my applications on a dedicated page,
  so that I can track every program I have applied to.
- **As a student**, I want to update each application's status to **Started**
  or **Submitted**, so that I can reflect my own progress before faculty review.
- **As a student**, I want to remove an application I no longer intend to
  pursue, so that my tracker only shows active targets.
- **As a student**, I want to see a missing-documents checklist on my dashboard
  and applications page, so that I know which required uploads are still
  outstanding.
- **As a student**, I want to see application deadlines alongside each
  tracked application, so that I do not miss important dates.

### Student: faculty matching and bookmarks

- **As a student**, I want to browse verified faculty sorted by how well their
  research areas match my interests, so that I can prioritize relevant
  advisors.
- **As a student**, I want to see a match score and overlapping research areas
  on each faculty card, so that I understand why someone was recommended.
- **As a student**, I want to filter faculty by research area and by whether
  they are accepting students, so that I can focus on realistic contacts.
- **As a student**, I want recommended faculty on my dashboard, so that I do
  not have to search from scratch every visit.
- **As a student**, I want to bookmark faculty profiles, so that I can return
  to promising advisors quickly.
- **As a student**, I want a bookmarks page listing everyone I saved, so that
  my shortlist is easy to manage.
- **As a student**, I want to open any faculty or student profile and see their
  public information, so that I can research people before emailing them.

### Student: contact and notifications

- **As a student**, I want to see a faculty member's email on their profile
  with a mailto link, so that I can ask program or research questions directly.
- **As a student**, I want to receive an in-app alert when faculty update my
  application status (e.g. Admitted or Rejected), so that I learn about
  decisions without checking email constantly.

### Faculty: profile and visibility

- **As a faculty member**, I want to edit my profile with title, bio, research
  areas, lab/website link, and publications link, so that students can evaluate
  my lab and interests.
- **As a faculty member**, I want to toggle whether I am accepting students, so
  that the directory reflects my current availability.
- **As a faculty member**, I want to see a warning on my dashboard when my
  account is still unverified, so that I know why I am not appearing to
  students.
- **As a faculty member**, I want to receive a notification when an admin
  verifies my account, so that I know I am now visible in the directory.

### Faculty: discovering and saving students

- **As a faculty member**, I want to browse all student profiles, so that I
  can proactively find strong candidates.
- **As a faculty member**, I want to filter students by major and research
  interest, so that I can focus on students aligned with my areas.
- **As a faculty member**, I want to sort students by name, relevance to my
  research areas, or GPA, so that I can order the list the way I prefer.
- **As a faculty member**, I want to see a match score when viewing a student
  profile, so that I can gauge overlap with my research interests.
- **As a faculty member**, I want to bookmark (save) student profiles, so that
  I can track candidates I am considering.
- **As a faculty member**, I want saved students and recent notes on my
  dashboard, so that my ongoing review work is easy to resume.

### Faculty: notes on applicants

- **As a faculty member**, I want to leave private notes on a student's profile
  that are visible to other faculty, so that the admissions committee can share
  impressions.
- **As a faculty member**, I want to edit or delete my own notes from the
  profile page (actions appear on hover), so that I can correct mistakes without
  leaving the page.
- **As an admin**, I want to edit or delete any faculty note, so that I can
  moderate inappropriate or outdated comments.

### Faculty: applicant review

- **As a faculty member**, I want an Applicants table with columns for name,
  program, major, and status, so that I can review everyone in a consistent
  layout.
- **As a faculty member**, I want to admit or reject an application directly
  from the Applicants page or from a student's profile, so that I can make
  decisions in context.
- **As a faculty member**, I want destructive actions (admit, reject, delete
  note) to require confirmation in a modal, so that I do not change status by
  accident.
- **As a faculty member**, I want to undo an Admit or Reject decision and
  return an application to Under Review, so that I can reverse a mistake.
- **As a faculty member**, I want to view a student's uploaded documents from
  their profile, so that I can read materials while reviewing their application.
- **As a faculty member**, I want to receive a notification when a high-matching
  student (50%+ interest overlap) applies to a program, so that I can review
  strong candidates quickly.

### Admin: faculty management

- **As an admin**, I want a dashboard summary of student count, faculty count,
  unverified faculty, and program count, so that I can see system health at a
  glance.
- **As an admin**, I want to create verified faculty accounts directly, so that
  I can onboard advisors without waiting for self-registration.
- **As an admin**, I want to verify or revoke verification for faculty
  accounts, so that I control who appears in the student directory.
- **As an admin**, I want verified faculty to be notified automatically, so that
  they know when they become visible to students.

### Admin: program management

- **As an admin**, I want to create graduate program listings with name, degree
  type, research areas, funding flag, deadline, description, and external URL,
  so that students browse accurate catalog data.
- **As an admin**, I want to edit existing program details, so that deadlines
  and descriptions stay current.
- **As an admin**, I want to delete programs that are no longer offered, so that
  students do not apply to outdated listings.

### Notifications (all logged-in roles)

- **As a logged-in user**, I want an Alerts dropdown in the top navigation with
  an unread badge, so that I can see new activity without leaving my current
  page.
- **As a logged-in user**, I want notifications marked read when I open the
  Alerts panel, so that the badge clears after I have seen them.
- **As a logged-in user**, I want to dismiss individual notifications with an
  × button, so that I can clear items I have handled.
- **As a logged-in user**, I want a Clear all action, so that I can empty my
  notification list in one step.
- **As a logged-in user**, I want notification links to take me to the relevant
  page (profile, applications, admin panel, etc.), so that I can act on alerts
  immediately.

### AI admissions assistant (all pages)

- **As any visitor or logged-in user**, I want an AI chat widget on every page,
  so that I can ask admissions questions without hunting through static pages.
- **As a user**, I want the AI to answer questions about GSU CS graduate
  programs, concentrations, deadlines, funding, and application steps using
  built-in knowledge plus live program data from the database, so that answers
  reflect what is actually listed in the portal.
- **As a user**, I want the AI to fall back to built-in knowledge when the LLM
  is unavailable or rate-limited, so that I still get a useful response.
- **As a logged-in user**, I want my chat messages stored, so that conversation
  history can be reviewed later.
- **As an operator**, I want to extend the bot by adding `.md` or `.txt` files
  under `knowledge/`, so that custom Q&A is picked up on server restart without
  code changes.

### JSON API (integrations and Postman)

- **As an integrator**, I want `GET /health`, so that I can confirm the server
  is running.
- **As an integrator**, I want `POST /api/login` to obtain a bearer token, so
  that I can call protected endpoints from Postman or another client.
- **As an integrator**, I want `GET /api/users` and `GET /api/users/<id>` with
  optional search, so that I can list and inspect user records programmatically.
- **As an integrator**, I want `POST /api/chat`, so that I can send admissions
  questions to the same assistant used in the web UI.
- **As a logged-in web user**, I want notification APIs for mark-read, dismiss,
  and clear-all, so that the Alerts dropdown can update without full page
  reloads.

---

## API quick reference

Login in the browser for web pages, or call `POST /api/login` in Postman and
send the returned token as `Authorization: Bearer <token>`.

```text
GET  /health
POST /api/login
GET  /api/users
GET  /api/users?search=student
GET  /api/users/1
POST /api/chat
POST /api/notifications/mark-read
DELETE /api/notifications/<id>
POST /api/notifications/clear
```

API login body:

```json
{
  "identifier": "admin",
  "password": "AdminPass123!"
}
```

Chat body:

```json
{
  "message": "What GSU CS graduate programs are available?"
}
```

Import `gsu_chat_api.postman_collection.json` into Postman and set
`base_url` to `http://70.133.221.153:5000` (or `http://192.168.1.165:5000`
on the local network).
