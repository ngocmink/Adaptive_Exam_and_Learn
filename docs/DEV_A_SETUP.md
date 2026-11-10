# Dev A — database and read API handoff

## What was found

The application factory, dependencies, configuration, shared helpers and route
files were empty. No model files or migrations existed. ERD v1 and the response
contract were found in `docs/sprint_1_backend_frontend_plan.md`. The older
`DEV_TASKS_SPRINT_1.md` claims models already exist; that claim did not match
the repository. This implementation uses the ERD embedded in the former file.
The extra study/exam duration fields mentioned only in the other checklist are
not added. Confirm those in a future migration if needed.

## Team ownership and integration

- Dev A read endpoints live in `app/subject_routes.py` and
  `app/admin/read_routes.py`. Blueprints: `subjects_read`, `admin_read`.
- Dev B's `app/auth/routes.py` and `app/common/decorators.py`, and Dev C's
  `app/library/routes.py` and shared `app/admin/routes.py` are untouched.
- The factory registers only implemented Dev A blueprints. Teammates must add
  their own blueprint imports/registration once implemented. Do not register
  a second GET handler for any Dev A URL.
- The read guard accepts the documented `session['user_id']` or Flask-Login's
  authenticated user and re-reads the role from the database. It ignores
  session role claims. Staff access is shared by teachers/admins, matching
  the current contract; no per-teacher ownership restriction is documented.
- CSRF is enabled. Auth/write API owners must expose/use a CSRF token for
  session-authenticated writes; do not exempt the entire API.
- Existing templates/assets and the legacy application are preserved. This
  foundation does not wire the old UI or static/PDF URLs: those belong to
  teammates. Material file_url is metadata, not an access-controlled file server.
- Subjects are public and paginated (default limit 9); clients must consume
  pagination when populating a full dropdown. Counts include active content.

## Setup (PowerShell, project root)

Install Python 3.12+ and Docker Desktop with Linux containers. The verification
machine used Python 3.14; `requirements.lock.txt` records its resolved packages.

```powershell
Copy-Item .env.example .env
# Edit .env: set your own database password and a random SECRET_KEY.
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
docker compose up -d db
.\.venv\Scripts\python.exe -m flask --app app:create_app db upgrade
```

Compose publishes the database only on localhost, with a persistent volume.
`docker/init.sql` creates `exam_test` only on first initialization. If the volume
already existed, create it without deleting the development volume:

```powershell
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" exam_test'
```

The first migration creates ten model tables (plus Alembic bookkeeping),
`unaccent`, `pg_trgm`, foreign keys, checks, uniqueness and indexes. Migration
credentials need permission to create these extensions. Downgrade removes
model tables but intentionally leaves shared extensions installed.

## Demo seed (repeatable, no database reset)

Set `DEMO_ADMIN_PASSWORD`, `DEMO_TEACHER_PASSWORD`, `DEMO_STUDENT_PASSWORD`
in your local `.env` (at least 12 characters each), then run:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app seed
.\.venv\Scripts\python.exe -m flask --app app:create_app run --debug
```

Demo emails: `admin@example.test`, `teacher@example.test`,
`student@example.test`. There are three synthetic questions and two assessments.
Repeated seeding does not reset passwords or overwrite existing content.
For a clean demo, use a NEW dedicated development database, migrate and seed;
there is deliberately no command that wipes development data. The app currently
exposes only read APIs; Dev B must implement login before browser integration.

## Legacy Excel import

The actual files use `Type` to link material rows and questions. The importer
reads tailieu.xlsx + quiz.xlsx atomically, creates subjects/materials/questions,
and builds one sample assessment for each subject with questions.
IDs are assigned by PostgreSQL, so old numeric IDs do not cause collisions.
Source IDs are not preserved or used to attach old scores.

Difficulty is a numeric scale **1 to 10**, with 1 easiest and 10 hardest,
as requested by the project owner. Fractional values are preserved (the old
quiz uses 2 and 2.5). API difficulty values are JSON numbers, not category labels.
Filters use exact numeric equality, e.g. `?difficulty=2.5`. Values outside the
range, booleans, NaN and infinity are rejected. The database also enforces
the range. No difficulty mapping file is needed.

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app import-excel
```

The legacy file has no topic or explanation columns; these remain NULL rather
than inventing pedagogical content. Review and populate them before adaptive
learning or answer-review features. Imported materials default to 5.5 because
the source has no difficulty; treat this midpoint as an uncalibrated placeholder.

Users are skipped unless `--include-users` is explicitly supplied. Only
recognized Werkzeug scrypt/pbkdf2 SHA256 hash formats are accepted; plaintext
or unsupported hashes cause rollback, with no personal values in the error.
Existing users are not overwritten or promoted. Study type accepts only the
ERD labels; unknown values become NULL. All imported users are students.
Legacy scores and chatbot spreadsheets are NOT imported: no reliable relation
from their rows to user+assessment+answers has been supplied.

Natural keys make repeated imports safe: subject code derived from Type,
material subject/title/path, question subject/content, assessment subject/title.
Conflicting existing answers or difficulty cause rollback. This is a one-time
migration tool, not a synchronization engine for edited spreadsheets.
The optional `--reset-sequences` is for an explicit-ID maintenance import;
stop writers first, since it briefly locks all model tables. Normal imports
do not need it. PostgreSQL sequences may have gaps after rollback.

## Read APIs

All return `{success, message, data, pagination}`. Lists accept `page >= 1`,
`limit 1..100`, default 9. Invalid input returns JSON 400; an empty page is 200.

| Endpoint | Access | Filters |
|---|---|---|
| GET /api/subjects | Public | page, limit; active subjects only |
| GET /api/admin/questions | Admin/Teacher | subject_id, difficulty, topic (exact), search, include_inactive |
| GET /api/admin/questions/<id> | Admin/Teacher | Includes correct options and explanation, including inactive records |
| GET /api/admin/materials | Admin/Teacher | subject_id, difficulty, search, include_inactive |
| GET /api/admin/assessments | Admin/Teacher | subject_id, type, search, include_inactive |

`include_inactive` defaults false; use true/false or 1/0. Search is literal,
case/accent insensitive. Questions return correct answers ONLY on protected
admin endpoints. Never reuse that serializer for the student test-taking API.
Assessment lists return metadata and question count, not answers.

## Model invariants and teammate requirements

- QuestionOption has a partial unique index: at most one correct option.
  Call `Question.validate_for_use()` after assembling options and before
  publishing a question or using it in an assessment; this requires FOUR
  options and exactly ONE correct answer. The index alone permits zero.
- AttemptAnswer has one row per attempt/question and a composite foreign key
  enforcing that the selected option belongs to that question. A blank answer
  may have selected_option_id=NULL. Attempt API owners must also check that
  the question belongs to the attempt's assessment (not expressible with the
  current ERD foreign keys alone).
- Email normalizes to lowercase; the database also enforces normalization.
- Referenced questions/users/materials are protected against unsafe deletes.
  Question edits are NOT snapshotted by this ERD. Before Sprint 2, agree on
  versioning or snapshots so old attempts are preserved; do not silently edit
  used questions. A persisted deadline is also a Sprint 2 schema decision.
- Scores/point values are finite; pass_score is a percentage 0..100 following
  the ERD example `score < 50`. Confirm the final grading scale with the team.

## PostgreSQL tests

Tests use migrations, not SQLite or create_all. They TRUNCATE only model tables
in an explicitly acknowledged `exam_test` database, never exam_dev.

```powershell
# DATABASE_URL and TEST_DATABASE_URL are loaded from .env by the test setup.
$env:ALLOW_TEST_DB_RESET = 'yes'
.\.venv\Scripts\python.exe -m pytest -q
```

Do not point TEST_DATABASE_URL at a database with data you need. Guards require
the exact name exam_test and a different development target. API tests set a
test session directly because Dev B auth endpoints do not exist yet. CSRF is
disabled ONLY in the test app. End-to-end login/browser checks remain for
integration with Dev B/C.

## Initial verification before Docker was installed (historical)

- Python 3.14.7; PostgreSQL 18.4 in an isolated, localhost-only cluster on port
  55432, stored under the gitignored `.local-pg/` directory.
- Docker is not installed here. PostgreSQL 16 Compose startup is NOT verified.
- Fresh migration applied; model/migration comparison reported no pending
  operations. Migration downgrade/re-upgrade was exercised only on exam_test.
- PostgreSQL integration suite: 45 tests, including permissions, numeric
  difficulty limits/fractions, constraints, import rollback, seed/import
  repetition, explicit-ID sequence repair, and test database reset guards.
- Actual content import ran twice successfully against the isolated
  exam_dev_numeric database: 3 subjects, 3 materials, 12 questions, 0 users.
  All 12 source questions have no topic/explanation fields; manual review is
  required. Legacy numeric difficulty 2 and 2.5 was preserved.
- `pip check` passed. No existing database service was modified, and no
  teammate route or legacy frontend files were edited.
- The temporary PostgreSQL cluster is stopped after verification. It is not
  your Docker environment or a configured production/development deployment.

To use the temporary local verification instance instead of Docker:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D .local-pg -l .local-pg/server.log -o '-h 127.0.0.1 -p 55432' -w start
$env:DATABASE_URL = 'postgresql+psycopg://deva@127.0.0.1:55432/exam_dev_numeric'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://deva@127.0.0.1:55432/exam_test'
# Set SECRET_KEY to your own random value; set demo passwords before seed.
```

This disposable cluster uses trust authentication on localhost only and is
for local verification; use password authentication for the shared environment.
The earlier empty exam_dev database is an intermediate verification artifact;
use exam_dev_numeric if inspecting the final imported schema.

## Docker PostgreSQL 16 verification (current)


Docker Desktop is now installed and the Compose setup has been verified.

- Server: PostgreSQL 16.15, image postgres:16-alpine.
- Local address: 127.0.0.1:55433 (the existing local PostgreSQL service keeps 5432).
- Databases: exam_dev and isolated exam_test, created successfully at first startup.
- Persistent Docker volume: adaptive_exam_and_learn_exam_pgdata.
- Migration upgrade and model/schema comparison passed.
- Demo seeding and actual legacy content import each ran twice without duplication.
- Final development counts: 3 demo users, 4 subjects, 4 materials, 15 questions,
  60 options, 4 assessments. Legacy personal accounts were not imported.
- All 45 PostgreSQL integration tests passed on the Docker PostgreSQL 16 instance.
- Container restarted; all ten model-table record counts were unchanged, demo
  passwords still verified, public read API returned 200, protected API returned
  401 for an anonymous request.
- Container is left running and healthy; the earlier local PostgreSQL 18 cluster
  remains stopped. The other existing Docker containers were not modified.

Your local .env was generated with random database, app and demo passwords.
Do not commit it. Demo accounts are admin@example.test, teacher@example.test,
student@example.test; their passwords are the respective DEMO_*_PASSWORD values
in that file. Auth login routes still require Dev B's implementation.

Normal startup (PowerShell, project root):

```powershell
docker compose up -d --wait db
.\.venv\Scripts\python.exe -m flask --app app:create_app run --debug
```

The backend reads .env automatically. Only the database runs in Docker in this
development setup; Flask runs in the project virtual environment on the host.
To stop the database while preserving it, use `docker compose stop db`.
