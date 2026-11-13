# Learner Dashboard Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Restore the legacy learner dashboard at `/account`, populate it from the current database APIs, and retain the separate admin/teacher dashboard.

**Architecture:** Keep the existing Flask route and auth boundary, switch its template to the legacy learner layout, and move dynamic course/material/assessment rendering into a focused static JavaScript file. Preserve the current API contracts and reader route; keep admin routing and dashboard untouched.

**Tech Stack:** Flask/Jinja, HTML, existing CSS, vanilla JavaScript, current JSON APIs.

**Spec:** `docs/superpowers/specs/2026-11-13-learner-dashboard-design.md`

## Global Constraints

- Keep `/account` protected by the existing login decorator and keep admin/teacher at `/admin`.
- Use the current `/api/subjects`, `/api/materials`, `/api/assessments`, `/reading?id=...`, and `/api/auth/logout` interfaces.
- Keep question text and correct answers out of the learner page.
- Use Flask `url_for` for static files, safe DOM text assignment for API content, and send the CSRF token on logout.
- Preserve the legacy account page structure and existing CSS assets; make it usable on narrow screens.

## Review Focus

- No active subjects or learning content: page remains usable and shows clear empty states.
- API failure or malformed response: show a readable error and keep the rest of the page usable.
- User-controlled strings in content: display as text without interpreting HTML.
- Missing CSRF token or logout failure: report failure without pretending the user logged out.
- Learner account versus admin/teacher role: learner sees `/account`; manager dashboard stays separate.

## Files

- Modify `app/library/routes.py`: make `/account` render the legacy learner template with the current user.
- Modify `templates/account.html`: retain the legacy layout, replace obsolete template variables/forms with dynamic content hooks, include CSRF metadata and the dynamic script.
- Modify `asset/style.css`: add scoped styles for dynamic records, status states, and responsive layout without replacing the existing design.
- Create `js/account.js`: load paginated subjects/materials/assessments from existing APIs, render cards safely, and handle logout.
- Leave `templates/admin_dashboard.html`, `app/admin/routes.py`, and login role redirects unchanged.

## Task 1: Restore the learner dashboard

**Interfaces:** Consumes existing API response envelopes and current route `/reading?id=<material id>`; produces the learner-facing `/account` view.

- [x] Modify `learner_page` to pass `user` into `account.html`; verify `/admin` still uses its own route and template by code inspection.
- [x] Update `account.html` to retain its visual sections and asset references, remove the legacy POST form and undefined `user_email`/`tai_lieus` references, and add dynamic list/status containers plus CSRF metadata.
- [x] Create `js/account.js` to load all pages of active subjects and content from the three existing read APIs, filter displayed content by selected subject, provide materials/assessment switching, show loading/empty/error feedback, link materials to `/reading?id=...`, show only public assessment metadata, and submit logout with CSRF.
- [x] Add scoped responsive styles to `asset/style.css` for the dynamic list controls/cards/status containers.
- [x] Run `python -m compileall app` to check Python syntax and inspect the changed routes/templates/scripts for stale legacy endpoints, unsafe HTML insertion, or broken static URLs.

## Verification

Run `python -m compileall app`. Review the diff and confirm the account route, assets, and JS all use the current endpoint names. No database migration or API change is required.
