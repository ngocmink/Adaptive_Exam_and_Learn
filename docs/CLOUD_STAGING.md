# Free shared staging on Render

This branch combines Dev A database/read APIs with the current main branch's
auth, library, admin and frontend. Main and feature/dev-a-foundation are unchanged.
It does not implement future exam-taking, scoring or adaptive-learning features.

## What runs in the cloud

- One free Docker web service running Flask with Gunicorn (HTTPS via Render).
- One free managed PostgreSQL 16 database named exam_staging.
- Templates, CSS/JS and the bundled sample PDF are part of the app image.
- Migrations and repeatable synthetic seeding run before Gunicorn starts.
- No local .env, personal user spreadsheet, local database or Docker volume is
  copied into the image. Cloud credentials are generated separately by Render.
- Database has no public IP allowlist entries: only internal connections.
- Tests remain local/CI; no cloud exam_test database is created or reset.

## Account action required

1. Sign up at https://dashboard.render.com/ using GitHub (Naemnguu).
2. Authorize Render to access ngocmink/Adaptive_Exam_and_Learn. The repository
   owner may need to approve the GitHub app installation.
3. Choose New > Blueprint and select this repository and feature/cloud-staging.
4. Ensure Blueprint path is render.yaml. Confirm BOTH resources show Free.
   Do not choose an upgrade or add a paid resource for this test deployment.
5. Apply the Blueprint; wait for the database and web service to become healthy.
6. Open the web service's onrender.com URL. /health must return status=ok.
7. Open /login. Demo users are admin@example.test, teacher@example.test and
   student@example.test. Retrieve their generated DEMO_*_PASSWORD values from
   the web service Environment settings and share privately with testers.

No hosting account is connected or cloud URL created by preparing these files.

## Free plan limits

Render free web services sleep after 15 minutes idle; waking may take about a
minute. Their writable filesystem is ephemeral: file uploads will not persist.
Use the bundled PDF or external document links for testing. A shared upload
store requires a separate decision; do not claim durable uploads on this plan.
Free Postgres expires 30 days after creation. Export needed records before that
deadline. This is a temporary staging environment, not production hosting.
No payment method is required by this configuration; review current provider
quotas and keep billing disabled if you require strictly free operation.

References: https://render.com/docs/free and https://render.com/docs/blueprint-spec

## Deploy updates

Automatic deployment is off. Push reviewed changes to feature/cloud-staging,
then choose Manual Deploy > Deploy latest commit in Render. Database migrations
must remain backward compatible; do not reset the cloud database on redeploy.

## Local integration test

Keep local .env unchanged and use the existing Docker database. Run:

```powershell
docker compose up -d --wait db
$env:ALLOW_TEST_DB_RESET='yes'
.\.venv\Scripts\python.exe -m pytest -q
```

Only exam_test is reset. To preview the site locally use flask run --debug.
To reproduce cloud startup locally, do NOT reuse COOKIE_SECURE=true over HTTP.

## Integration decisions

- Preserve the ten tested models and numeric 1..10 difficulty scale.
- Adapt incoming write API filters/forms to numeric difficulty (fractions allowed).
- Keep one handler for each read API URL, using Dev A's protected read endpoints.
- Register incoming page/auth/library/write blueprints in the shared factory.
- Use Flask-WTF for both template tokens and API X-CSRF-Token validation.
- Keep database credentials and secrets outside the Git repository and image.

## Verification before publishing this branch

- 53 PostgreSQL integration tests passed sequentially, including the 45
  foundation checks and new UI/auth/CSRF/numeric API/static-file checks.
- Production image built with Python 3.12 on Linux and Gunicorn 23.
- Real HTTP smoke check passed against a NEW exam_staging_smoke database:
  initial migrations, repeatable seed, homepage/login/register, bundled PDF,
  token-protected admin login, admin read API, and numeric public library API.
- Image verified to exclude .env, seed_data and .git. The temporary web
  container was removed; existing development data was not reset.
- Blueprint has been checked against the documented Render fields but has NOT
  been applied or validated inside a signed-in Render account. Cloud deployment
  and public URL verification remain pending account/repository authorization.
