# Acceptance test plan and cases

Baseline: `main`, `3d04e11f0450894bd403e64aeb7e548b19180c1f` · 17 November 2026.

Use with [Business scope](01_BUSINESS_PROBLEM.md), [User stories](02_USER_STORIES.md) and [Traceability](03_TRACEABILITY.md). **Every case below starts as Not run.** Expected gaps are based on code inspection; they are not recorded execution failures. This task generated documentation and did not run tests or modify database records.

## Test environment

Record the actual commit, browser, application URL, database target, schema revision and storage bucket before execution. Do not assume a locally running Flask process uses a local database: `DATABASE_URL` can point to shared Render.

Run destructive, retry, expiry, content-edit and analytics fixtures against an isolated PostgreSQL database, not the shared Render environment. Existing pytest fixtures may reset only an explicitly configured `exam_test` distinct from the development database; follow their reset guard. Do not copy production secrets into screenshots or evidence files.

For PDF integration use an approved private test bucket/file, or read-only access to an approved existing PDF. Record only bucket/path and material ID; redact signed URL tokens and API keys.

## Fixture catalogue

| Fixture | Required data |
|---|---|
| F-USER | Anonymous browser, student A, student B, teacher and administrator, each with a known test-only password |
| F-SUBJECT | Active subjects S1/S2 and an inactive subject; two published S1 lessons L1/L2, one S2 lesson, a draft and an archived lesson |
| F-PDF | Active S1 material M1 with a private bucket/path; another distinct PDF M2; supported legacy URL material; inactive material; nonexistent storage path |
| F-LINK | M1 linked to L1 and L2; M2 linked only to L2; one unlinked material; a cross-subject link attempt |
| F-QUESTION | Four reviewed active S1 questions Q1–Q4, four nonempty options each and exactly one correct option, with topic and explanation; an S2 question and a disabled question |
| F-QUIZ | A fixed S1 assessment with Q1–Q4, points 1 each, pass_score 50 and sufficient duration; an inactive assessment |
| F-WEIGHT | Separate assessment with points Q1=1, Q2=2, Q3=3, Q4=4. Correct Q1/Q4 only earns 5/10 = 50% |
| F-TIME | A short-duration test and controllable server clock/worker for expiry tests. Browser-clock changes alone do not simulate a server deadline |
| F-ANALYTICS | Under proposed D-03 policy: 4 started attempts, 2 completed scores 40 and 80, 1 in progress, 1 abandoned. Expected completion 50%, completed-score mean 60; finalize policy before asserting |
| F-ADAPT | D-01 approved proficiency transitions and question-pool examples, including no history, boundaries and exhaustion |
| F-RULE | D-06 approved rules plus active matching material/practice, inactive targets, repeated targets and no-match cases |

Do not insert fabricated algorithm thresholds or assume that numeric fixture IDs match existing cloud data. Capture IDs returned during fixture setup. Save the mapping in the run evidence.

## Running a case

1. Confirm its fixture and decisions are ready; otherwise mark Blocked with the reason.
2. Execute the listed action and record actual HTTP/UI/database behavior.
3. Compare every relevant acceptance criterion, not only the happy path.
4. Record Pass, Fail or Blocked, evidence, defect ID and tested commit.
5. Retest after a fix; previous evidence remains tied to its original commit.

For authenticated write requests, obtain CSRF tokens through the normal form/API flow. A test that disables CSRF cannot establish that the real browser workflow works.

## Accounts and permissions

| Case | Story | Action and fixture | Expected result |
|---|---|---|---|
| TC-01 | US-01 | Register a valid new F-USER student; inspect the created record and response. | One student account, hashed password, no hash/secret returned, clear success. |
| TC-02 | US-01 | Register duplicate email with changed case/spaces; try malformed email, empty name and too-short password. | Controlled 4xx responses; no duplicate or partial account. |
| TC-03 | US-01 | Include `role=admin` or `role=teacher` in registration. | Resulting account remains student; no privilege escalation. |
| TC-04 | US-02 | Log in each role through the browser; refresh and call `/api/auth/me`. | Correct identity persists; student redirects to `/account`, staff to `/admin`. |
| TC-05 | US-02 | Use wrong password/nonexistent email; tamper session role and invalid user ID. | No authenticated access; forged client role does not override database role. |
| TC-06 | US-03 | Login → logout → private request → login again, with real CSRF enabled; also omit/alter the token on a write. | Logout clears access, re-login works, missing/invalid CSRF is rejected. |
| TC-07 | US-04 | Anonymous and student callers invoke each staff create/edit/disable/read endpoint. | Anonymous API access denied; student gets 403 for staff actions. No data changed. |
| TC-08 | US-04 | Teacher/admin perform authorized sample content operations; student tries the same direct URLs. | Staff succeeds within shared-management policy; student denied at server, not merely UI. |

## Catalogue and PDFs

| Case | Story | Action and fixture | Expected result |
|---|---|---|---|
| TC-09 | US-05 | List subjects with active/inactive F-SUBJECT data and known material/test counts. | Active subjects only; counts reconcile without join multiplication. |
| TC-10 | US-05 | List lessons by S1; test invalid `subject_id=x`, another subject, draft and archived rows. | Correct ordered scope; invalid filter rejected. Draft expected result follows D-05; document current exposure. |
| TC-11 | US-05, US-12 | Use learner subject/lesson controls and compare selection with `/api/lessons` and actual links. | Label, selected IDs and retrieved content agree; no subject ID accidentally used as a lesson ID. |
| TC-12 | US-06 | Combine material search, S1, L2 and supported difficulty; try accented and unaccented search. | Only matching active records; expected accent behavior and metadata consistent. |
| TC-13 | US-06 | Use a result set larger than one page; request page 0, negative/oversized limits, invalid difficulty and no matches. | Valid stable pages/totals; invalid inputs rejected; meaningful empty state. Check literal `%`/`_` search policy rather than assuming wildcard escaping. |
| TC-14 | US-06, US-12 | With F-LINK, call `/api/materials?lesson_id=L2` and traverse pages; compare all-material listing. | HTTP 200; M1/M2 each appear once; no duplicate-alias SQL error. Static inspection identifies this as high risk. |
| TC-15 | US-07 | Open M1 then M2 as student; compare distinctive PDF content to bucket/path. | Correct different files, visible reader, no mismatched lesson/file assumption. |
| TC-16 | US-07 | Call `/api/materials/M1/file` anonymously, with nonexistent material, inactive material and inactive parent subject. | 401 for anonymous; 404 for unavailable content; no signing before permission checks. |
| TC-17 | US-07 | Open private PDF; inspect response headers/page source; reopen after expiry using a fresh application request. | Temporary same-storage-origin URL, one-hour configured expiry, no-store redirect, no secret in page; new authorized request can obtain a fresh link. Use accelerated mocked time for automation. |
| TC-18 | US-07 | Simulate missing key/config, missing object, timeout, malformed response and unexpected redirect origin. | Controlled 503/404/502 as applicable; no credential or upstream-body leakage. |
| TC-19 | US-07 | Open supported `pdf/...`, `/static/pdf/...` and external PDF URL records; attempt `../` traversal. | Supported legacy documents still open; traversal is rejected. Supabase `file_url=NULL` is valid with complete bucket/path. |
| TC-20 | US-08 | Search assessments and combine subject, linked lesson and type filters; inspect displayed counts/duration. | Correct active assessments and accurate metadata; stable pagination. |
| TC-21 | US-08 | Request public assessment list/detail as anonymous; inspect JSON; request inactive/nonexistent ID. | No answer key/explanations leaked in public summaries; unavailable detail rejected. |

## Staff content and mapping

| Case | Story | Action and fixture | Expected result |
|---|---|---|---|
| TC-22 | US-09 | Staff registers a PDF by path, then edits only its title; replace storage source with supported URL and vice versa. | One correct record; metadata edit retains source; replacement clears the obsolete source fields. |
| TC-23 | US-09 | Send incomplete bucket/path, both URL and path, wrong bucket, absolute path, traversal, control characters and non-PDF path. | Controlled rejection, no partial record; no unintended bucket signing. |
| TC-24 | US-09 | Disable M1, refresh catalogue, request its file directly, then inspect prior references. | Hidden from new learner use and file access denied; record retained; historical treatment follows D-04. |
| TC-25 | US-10 | Staff creates/updates a reviewed four-option question with subject/topic/explanation/difficulty. | Correct values and one correct option persisted; staff detail matches. |
| TC-26 | US-10 | Try 3/5/empty options, zero/two correct options, difficulty 0/11/NaN/Infinity. | Rejected atomically; no unusable published question or partial options. |
| TC-27 | US-10 | Filter staff questions by subject/topic/difficulty with paging; student requests detail. | Correct matching records for staff; student denied; no key leakage. |
| TC-28 | US-11 | Create/update an assessment with ordered valid questions, duration, threshold and type; toggle activation. | Correct membership/order/settings; disabled assessment absent to learners and cannot be started. |
| TC-29 | US-11 | Add an S2 question to an S1 assessment; submit duplicate/nonexistent question IDs; use invalid settings. | Same-subject and reference rules enforced; no partial changes. Current same-subject enforcement is a known inspection gap. |
| TC-30 | US-11 | Attempt to publish/create a zero-question assessment. | Expected behavior follows D-02; do not accept silent zero-question grading as a finalized policy. |
| TC-31 | US-12, US-25 | Link M1 to L1/L2, repeat the pair and attempt cross-subject links; inspect imported mapping against actual PDFs. | Reuse works; duplicate/cross-subject links rejected; every intended map is explicit and correct. Record the absence of a supported manager link-edit flow. |

## Attempt lifecycle and grading

Cases TC-32–TC-45 must use isolated data. Several are expected to reveal gaps because current code creates the attempt only during submission.

| Case | Story | Action and fixture | Expected result |
|---|---|---|---|
| TC-32 | US-13 | Student A opens F-QUIZ and starts work; inspect attempt before submitting. | Owned in-progress attempt, stable ID, real start time and server deadline exist before answers are finalized. |
| TC-33 | US-13, US-14 | Answer two questions, wait for saved acknowledgement, reload and resume. | Same owned attempt, answers/order preserved and remaining time not reset. |
| TC-34 | US-14 | Disconnect network before an answer save, change answer, reconnect and retry. | Unsaved/error state is truthful; acknowledged work retained; retry follows documented conflict handling. |
| TC-35 | US-04, US-18 | Student B requests A's result/resume IDs; anonymous repeats. | No private result/work leakage. Existing result route uses 404 for a non-owner. |
| TC-36 | US-15 | Start F-TIME, reload, change browser time and restart JavaScript countdown. | Deadline is unchanged and enforced by server; UI eventually reconciles to it. |
| TC-37 | US-15 | Save some answers, close all quiz pages, wait beyond deadline, then reopen. | Server finalizes from valid saved work without a browser submitting the form; no extended time. |
| TC-38 | US-10, US-18 | Complete an attempt, then change/disable question content/options or assessment membership in the isolated fixture. | Historical result remains interpretable under D-04; capture current drift rather than approving it. |
| TC-39 | US-14, US-15, US-17 | Send an answer save after expiry/completion and race a save with finalization. | Late changes rejected; deterministic accepted-answer boundary; completed result unchanged. |
| TC-40 | US-16 | On F-QUIZ, submit 2 correct, 1 wrong, 1 omitted. Include forged score/correctness fields. | 50%, correct=2, wrong=1, omitted=1; four answer records; client score ignored; threshold 50 passes. |
| TC-41 | US-16 | On F-WEIGHT answer Q1/Q4 correctly only; separately test all correct and none correct. | Weighted score 50%, then 100% and 0%; stable one-decimal display and correct totals. Set weights through fixture/import if UI fixes points to 1. |
| TC-42 | US-16 | Submit another question's option ID, a question not served, and an attempted user/assessment identity override. | Foreign option cannot earn credit; no answer for an unserved question; caller cannot choose another user's identity. Record whether invalid option is rejected or treated as omitted and reconcile the API contract. |
| TC-43 | US-17 | Send the same finalization twice and concurrently for one attempt. | One authoritative final attempt/result and answer set; retries return that result. Current POST-new-attempt behavior is an inspection gap. |
| TC-44 | US-18 | Review own completed, incomplete and zero-question fixtures; compare UI to saved record. | Final-only answer disclosure; correct/incorrect/omitted counts and durations accurate; no divide-by-zero. Zero-question acceptance follows D-02. |
| TC-45 | US-19 | A has several attempts, B has one and a third user none; open history, paginate and reopen an entry. | Only own attempts, stable order, correct target result/resume and empty state. No history workflow was found in this baseline. |

## Adaptive learning and analytics

| Case | Story | Action and fixture | Expected result |
|---|---|---|---|
| TC-46 | US-20 | Staff adds/removes assessment supporting PDFs and topics; student opens them; disable a target. | Explicit attachments and approved related topics visible only when accessible; removed/disabled targets unavailable. Currently no full runtime workflow found. |
| TC-47 | US-21 | Execute each approved F-ADAPT initial/update/boundary example; compare another student's access. | Exact approved proficiency outputs with explanation/scope; personal data protected. Blocked until D-01 is approved and implementation exists. |
| TC-48 | US-22 | Run correct/incorrect answer sequences, inspect served IDs, exhaust the pool and retest fixed assessments. | Approved response-dependent selection, no repeats, deterministic fallback and no fixed-mode regression. Blocked on D-01/runtime implementation. |
| TC-49 | US-23 | Finalize weak-topic/no-error attempts with F-RULE, duplicate/inactive/missing targets; request as another student. | Relevant deduplicated suggestions with reasons; distinct no-review/no-content states; ownership enforced. Blocked on D-06/runtime implementation. |
| TC-50 | US-24 | Use F-ANALYTICS with known answers/omissions; compare dashboard/API and test role denial. | Under approved fixture policy, 4 started, 2 completed, 50% completion and mean 60; correct distributions/error denominators and denied student access. Blocked until D-03/runtime implementation. |

## Data, deployment and regression

| Case | Story or enabler | Action and fixture | Expected result |
|---|---|---|---|
| TC-51 | US-25 | Import a small reviewed workbook twice; include invalid/skipped rows and explicit IDs. | Intended content appears once, links correct, sequences safe, no unreported missing content. Verify each importer separately; legacy importer tests do not cover the normalized workbook importer automatically. |
| TC-52 | WBS 1.4, 2.2 | On disposable PostgreSQL, run empty install and populated upgrade; compare schema and old record values. | Correct current schema, no unexplained data loss, expected constraints and recorded migration revision. Historical destructive migrations require backup-aware evaluation. |
| TC-53 | WBS 1.5, 3.7 | Follow setup/deploy instructions using an isolated configuration; inspect actual runtime branch/start command and ignored files. | Reproducible app; matching code/schema; no secrets/backups in Git/image; correct database target. Verify health semantics rather than assuming HTTP 200 checks DB. |
| TC-54 | WBS 1.9, 2.7, 3.6 | Full browser journey: login → filter → PDF → staff edit → student refresh → fixed quiz → result; then repeat after restart. | No blocker across implemented flow; retain evidence of missing history/adaptive/recommendation/analytics rather than omitting them from the release report. |

## Defect and evidence template

Copy this block for each execution; do not replace an expected result with what the code happens to do.

```text
Case ID:
Story and AC IDs:
Commit / environment / schema revision:
Executed by / date:
Fixture IDs and relevant setup:
Exact steps / request (redacted):
Expected result:
Actual result:
Status: Not run | Pass | Fail | Blocked
Evidence path / screenshot / safe response excerpt:
Defect ID and severity:
Retest commit and outcome:
```

Severity guidance: a security/privacy breach, lost accepted answers, incorrect grading or blocked main learning flow should prevent acceptance of the affected feature. Cosmetic issues should be tracked separately. An unimplemented committed requirement remains a gap even when unrelated automated tests pass.

## Release checklist

- [ ] Every user story has an owner, approved AC and linked case IDs.
- [ ] D-01–D-07 are resolved where they affect committed acceptance.
- [ ] Core account, library, content and fixed-assessment paths have evidence on the release commit.
- [ ] Autosave, deadline, idempotency and privacy tests have results rather than inferred completion.
- [ ] Adaptive/recommendation/analytics gaps are either completed or explicitly accepted as a scope change by the PO/instructor.
- [ ] Data sources and PDF mappings are reviewed; empty or incorrect links are not hidden by successful file delivery.
- [ ] Setup, migration, backup, rollback limitations and known defects are documented.
- [ ] Retests, UAT approval and the final release commit are recorded for WBS 3.8 and milestone 4.
