# Requirements to code traceability

Hierarchy navigation: [Functions and use cases](05_FUNCTIONS_AND_USE_CASES.md) · [AC-to-test and reverse lookup](06_AC_TEST_TRACEABILITY.md). Structure updated 20 November 2026; prior code assessment is unchanged.


Baseline: `main`, `3d04e11f0450894bd403e64aeb7e548b19180c1f` · 17 November 2026.

Source workbook: `172880 - Agile_Project_Plan - Nhóm 18 .xlsx`, sheet **Agile Project Plan**. Row numbers below are physical worksheet rows. [Business scope](01_BUSINESS_PROBLEM.md) and [Stories](02_USER_STORIES.md) define intended behavior; [Tests](04_ACCEPTANCE_TESTS.md) define acceptance checks.

## How to interpret coverage

- **Candidate:** a relevant execution path was found by static inspection. Still requires acceptance evidence.
- **Partial:** some criteria are implemented, but important criteria are absent or inconsistent.
- **Missing:** no corresponding runtime workflow was found in inspected application routes/services/templates.
- **Decision:** expected behavior needs a documented product decision first.

These labels are implementation assessments, not test results. Existing test functions are evidence of test code, not proof they passed on this commit. The earlier 79-test run and live PDF checks in the conversation used an earlier code baseline; they must not be reused as acceptance results for this commit.

Paths in the tables are repository-relative. Function names provide stable navigation when line numbers change.

## Functional coverage

| Story | WBS and workbook rows | Code evidence | Assessment and remaining work | Test cases |
|---|---|---|---|---|
| US-01 Registration | 1.6 / r17 | `app/auth/routes.py::register`; `app/models/schema.py::User` | Candidate: normalization, duplicate check, student role and hash exist. Execute API/CSRF/error cases. | 01–03 |
| US-02 Login | 1.6 / r17 | `app/auth/routes.py::login`, `me`; `app/common/decorators.py` | Candidate: credentials, sessions and role redirects exist. Verify actual browser cookie/CSRF flow. | 04–05 |
| US-03 Logout | 1.6 / r17 | `app/auth/routes.py::logout`; `app/common/csrf.py` | Candidate: session clearing exists. Verify token rotation and private access afterward. | 06 |
| US-04 Authorization | 0.1 / r7; 1.8 / r19; 2.5 / r26 | `role_required`; `app/common/read_access.py::staff_required`; `quiz_results` | Candidate for inspected endpoints; execute the complete endpoint/role matrix and ID tampering. | 07–08, 35 |
| US-05 Subjects/lessons | 1.7 / r18; 3.3 / r33 | `app/subject_routes.py::subjects`, `lessons` | Partial: lesson filtering/order exists, but invalid subject values are silently ignored and drafts are included. D-05 resolves publication policy. | 09–11 |
| US-06 Material discovery | 1.7 / r18 | `app/library/routes.py::list_materials`, `_material_data`; `js/account.js` | Partial: search, subject/lesson/difficulty filters and lesson metadata exist. The lesson-filter path joins `LessonMaterial` and then outer-joins it again without aliases; verify likely duplicate-table SQL failure. Check inactive-parent consistency and wildcard behavior. | 12–14 |
| US-07 PDF reading | 1.7 / r18; 1.9 / r20; later storage decision | `material_file`; `app/common/material_storage.py`; `templates/material_reader.html` | Candidate: protected redirect and one-hour signing exist; missing/inactive content and storage failures have branches. Signed links remain bearer access until expiry. | 15–19 |
| US-08 Assessment discovery | 1.7 / r18; 2.6 / r27 | `list_assessments`, `assessment_detail`, `_assessment_data` | Candidate: subject/type/lesson filtering and answer-free summaries exist. Lesson membership is derived through linked questions. Check metadata and parent/content activation consistency. | 20–21 |
| US-09 Material management | 1.8 / r19; later storage decision | `app/admin/routes.py::create_material`, `update_material`, `disable_material`; `material_source`; `js/admin.js` | Candidate for registration/edit/disable of an already-uploaded PDF. No automatic storage synchronization or upload form was found. | 22–24 |
| US-10 Question management | 1.8 / r19; 2.6 / r27 | `create_question`, `update_question`, `disable_question`; `question_json`; `Question.validate_for_use` | Partial: CRUD and four-option validation exist. Explanation/topic are optional in the schema, and historical-safe editing is not resolved. | 25–27, 38 |
| US-11 Assessment management | 1.8 / r19; 2.6 / r27 | `create_assessment`, `update_assessment`, `toggle_assessment`; `AssessmentQuestion` | Partial: settings and duplicate IDs are checked; a same-subject question rule and nonempty-publication rule are not enforced by this code. | 28–30 |
| US-12 Lesson links | 3.3 / r33; later hierarchy decision | `app/models/hierarchy.py`; `app/seed/import_database_excel.py` lesson-material/question-lesson sections; catalogue filters | Partial: link constraints/import paths exist; no dedicated staff link CRUD UI/API was found. Verify filtered catalogue SQL and actual mappings. | 11, 14, 31 |
| US-13 Start/resume | 2.3 / r24 | `app/library/routes.py::quiz_page`; `Attempt` | Partial: GET renders questions but does not create an attempt; POST creates a completed attempt. No owned in-progress resume workflow found. | 32–33 |
| US-14 Autosave | 2.1 / r22; 2.3 / r24 | `templates/quiz.html` change/progress handler; `quiz_page` | Missing: option changes update browser UI only; no answer-save endpoint or acknowledged save state found. Answers are persisted at POST submission. | 33–34, 39 |
| US-15 Deadline | 2.3 / r24; 2.4 / r25 | `templates/quiz.html` countdown; `Attempt` | Partial: browser countdown and automatic form submission exist. No stored `expires_at`, server expiry enforcement or closed-page finalization found. | 36–37, 39 |
| US-16 Grading | 2.4 / r25 | `quiz_page` POST grading loop; `QuestionOption`, `AttemptAnswer` | Partial: server chooses valid options and computes weighted percentage. It grades received form values on a newly created attempt, not an owned attempt's previously saved answers; true start time is absent. | 40–42 |
| US-17 Idempotent submission | 2.4 / r25 | `quiz_page` creates `Attempt` on every POST | Missing: no stable submitted-attempt identity or idempotent finalization guard. Duplicate POSTs can create separate attempts. | 43, 39 |
| US-18 Result review | 2.5 / r26 | `quiz_results`; `templates/results.html` | Partial: owner check, score, correct count, selected/correct options and explanations exist. Omitted/incorrect counts and duration are not fully presented; historical review uses current content; final-status guard absent. | 35, 38, 44 |
| US-19 History | 2.5 / r26 | `Attempt` persistence and `/quiz/results` | Missing: no history listing endpoint or learner history view found. Stored rows do not establish a usable history feature. | 45 |
| US-20 Supporting materials/topics | 3.3 / r33 | Subject/lesson classification and question-derived assessment filter | Partial: lesson/subject connections exist; no explicit assessment-material attachment management or related-topic presentation found. | 46 |
| US-21 Proficiency | 3.1 / r31; 3.2 / r32 | Difficulty fields only | Missing + Decision D-01: no learner proficiency computation/presentation found. Question difficulty is not learner proficiency. | 47 |
| US-22 Adaptive practice | 3.2 / r32 | Fixed `assessment.assessment_questions` selection | Missing + Decision D-01: no response-dependent selector or exhausted-pool behavior found. | 48 |
| US-23 Recommendations | 3.4 / r34 | `app/models/schema.py::LearningRule` | Missing + Decision D-06: table exists; no rule evaluator, recommendation API or learner output found. | 49 |
| US-24 Analytics | 3.5 / r35 | Staff catalogue endpoints only | Missing + Decision D-03: no learning analytics aggregation API or dashboard found. Catalogue counts are not learning analytics. | 50 |
| US-25 Content readiness | 0.4 / r10; 2.6 / r27 | Seed/import modules; models; staff management | Partial: demo/import/constraints exist; reviewed explanations, exact file mappings and import rejection accounting need evidence. No publication-review workflow found. | 31, 51 |

## Engineering and delivery coverage

| WBS / rows | Required evidence | Evidence in repository and remaining verification |
|---|---|---|
| 0.1 / r7 | Personas, needs, permissions and main journeys | This requirements package supplies a derived baseline; PO/team approval and interview validation remain external evidence. |
| 0.2 / r8 | Prioritized scope, sprint goals and adaptive algorithm boundary | Workbook provides sprint scope. D-01/D-06 and final Must/Should/Could approval remain open. |
| 0.3 / r9 | Responsibilities for eight people and working agreements | Workbook roles and project docs are references, not proof of individual assignment/review practice. |
| 0.4 / r10 | Content sources, review owners and risk responses | US-25 and decisions capture acceptance needs. Verify actual source/review/risk records separately. |
| 1.1 / r12 | At least six approved stories with testable criteria | Twenty-five stories are supplied here; approval is not implied by generation. |
| 1.2 / r13; 2.1 / r22 | Figma flows, including save/error/offline/expiry/history states | Runtime templates exist; no supplied Figma artifact was inspected. UX acceptance needs the actual design. |
| 1.3 / r14 | Component responsibilities, API contracts, pagination/errors/permissions | Routes and common modules provide code evidence; final documented contract/reviewer agreement still needs review. |
| 1.4 / r15; 2.2 / r23 | ERD, schema, seed and data-preserving migrations | Models, migrations and seed modules exist. Later design has 13 app tables rather than the original 10. Test installation and populated upgrades in isolation (TC-52). |
| 1.5 / r16 | Clone/run instructions, automated PR build, staging and secret exclusion | Dockerfile, Compose, Render config and setup docs exist. No `.github` workflow directory was present in this snapshot; CI completion is unproven. Check runtime service settings, not YAML alone. |
| 1.9 / r20; 2.7 / r28; 3.6 / r36 | Integration, regression, negative paths, UAT and retest evidence | Existing tests cover database/import/read access and storage; full attempt/adaptive/analytics acceptance is not covered. Execute the attached plan. |
| 2.8 / r29; 3.8 / r38 | Review minutes, revised backlog, release commit and known gaps | These documents can inform the review but do not replace meeting minutes or release approval. |
| 3.1 / r31 | Approved algorithm examples and fallback policy | Decision D-01 blocks final adaptive outputs. |
| 3.7 / r37; milestone 4 / r39 | Reproducible setup, diagrams/report/slides/demo, handover and instructor acceptance | Repository docs partially support setup. Demo evidence for missing runtime features cannot be claimed. Instructor acceptance must be recorded separately. |

## Existing automated tests worth reusing

| Test file | Relevant examples | What it does not prove |
|---|---|---|
| `tests/test_deva.py` | `test_seed_repeatable_and_passwords_hashed`, `test_role_permissions`, `test_anonymous_and_forged_role` | Complete browser authentication acceptance or password-recovery support |
| `tests/test_deva.py` | `test_filters_pagination_and_stable_order`, `test_bad_filters`, `test_accent_insensitive_search_and_literal_wildcard` | New learner lesson-filter query behavior; several tests target staff endpoints |
| `tests/test_deva.py` | `test_unique_correct_and_required_correct`, `test_selected_option_must_belong_to_question` | Published question completeness on every write, assessment membership, or historical snapshots |
| `tests/test_deva.py` | Import/sequence/conflict/plaintext rejection tests; `test_database_reset_guard` | Every path of the newer normalized workbook importer or cloud restore readiness |
| `tests/test_material_storage.py` | `test_anonymous_cannot_sign`, `test_active_content_available_to_authenticated_roles`, `test_unavailable_content_never_signed` | Full curriculum-to-file mapping accuracy or instantaneous revocation of already issued links |
| `tests/test_material_storage.py` | Reader, legacy URL, source editing, invalid source, constraints, upstream failure and static-root tests | Real current storage availability or current Render deployment correctness |

## Review findings to turn into defects or decisions

1. Attempt rows begin and end at submission time; autosave/resume and real elapsed time are not implemented.
2. A browser-only countdown does not satisfy the WBS's server deadline and closed-page requirements.
3. Each POST constructs a new attempt, so repeated submission is not idempotent.
4. Result review reconstructs questions/options from current active content. Editing or disabling content can change historical presentation; D-04 needs a policy.
5. A direct result request checks owner but does not explicitly require final status.
6. Learner history, executable LearningRule suggestions, proficiency, adaptive selection and analytics were not found.
7. Draft lessons are exposed, and an invalid lesson subject filter is silently ignored. Confirm policy and raise validation defects where applicable.
8. The material lesson filter may produce a duplicate table join; reproduce with TC-14 before reporting it as a confirmed runtime failure.
9. Assessment question membership does not enforce subject consistency at the write/database layer. TC-29 should establish the observed behavior.
10. Source correctness is separate from storage connectivity: a working signed URL does not establish that a PDF belongs to its linked lesson.

No code, workbook or database was changed to produce this review. Test cases remain unexecuted in this documentation task.
