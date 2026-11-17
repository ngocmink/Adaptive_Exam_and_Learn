# Business problem and scope

Project: Adaptive Exam and Learn · Team 18  
Review date: 17 November 2026  
Code baseline: `main`, commit `3d04e11f0450894bd403e64aeb7e548b19180c1f`

## Purpose and sources

This document explains the problem the product should solve. Read it with [User stories](02_USER_STORIES.md), [Requirements traceability](03_TRACEABILITY.md) and [Acceptance test cases](04_ACCEPTANCE_TESTS.md).

The requirements source is `172880 - Agile_Project_Plan - Nhóm 18 .xlsx`, sheet **Agile Project Plan**, rows 7–39. Source references below use WBS IDs and physical worksheet row numbers. The workbook was read without modification. Workbook task statuses are planning information, not evidence that functionality passes acceptance.

The following business problem is a synthesis of the workbook and project context, not a verbatim statement from a customer interview. Product decisions that the sources do not settle are identified explicitly.

## Business problem

Students need to find learning materials for the subject and topic they are studying, practise with suitable questions, understand mistakes and decide what to study next. A folder of PDFs or a fixed question list does not provide the complete cycle: discovery, practice, reliable assessment, explanation, progress review and targeted follow-up.

Teachers need a manageable, consistent catalogue of materials, questions and assessments. Administrators and teachers also need trustworthy usage and result statistics to identify weak topics and content problems. When files, classifications, questions and results are maintained independently, incorrect links and inconsistent grading can undermine both learning and reporting.

The product should connect these activities in one website while protecting account access and each student's results. Its proposed adaptive functionality must make an observable change to question selection or follow-up content; storing difficulty values alone does not constitute adaptive learning.

## Users and expected value

| Actor | Need | Expected value |
|---|---|---|
| Student | Find appropriate PDFs and assessments, practise, understand results, revisit history | Less effort locating relevant content and a clear next learning action |
| Teacher | Create, update and disable learning content; inspect learning outcomes | A consistent content library and evidence for improving teaching materials |
| Administrator | Manage shared content access and inspect system-wide learning statistics | Controlled operations and trustworthy reporting |
| Content reviewer | Check sources, question correctness, explanations and classification | Usable learning data rather than unverified file uploads |
| Operator or DevOps | Reproduce installation and deploy compatible application/schema versions | A testable and maintainable shared environment |

There is no evidence of a separate content-reviewer permission role in the application. It is a team responsibility unless the team approves additional authorization behavior. The current account roles are `student`, `teacher` and `admin`.

## Business outcomes and acceptance evidence

| Outcome | Evidence needed | Source |
|---|---|---|
| Students can locate and open relevant content | Subject/lesson search, filtering, pagination and correct PDF delivery | WBS 1.7, 3.3 |
| Staff can maintain the catalogue safely | Authorized create/edit/disable actions visible consistently to learners | WBS 1.8 |
| Assessment records are reliable | Saved work, server time limits, server grading, one finalization per attempt, private results/history | WBS 2.3–2.5 |
| Practice responds to learner performance | Approved proficiency examples and adaptive next-question tests | WBS 3.1–3.2 |
| Results lead to useful follow-up | Topic-level recommendations with reasons and appropriate empty states | WBS 3.4 |
| Staff can understand learning outcomes | Dashboard numbers reconciled to a controlled fixture | WBS 3.5 |
| The delivered product can be reproduced and demonstrated | Setup, migration, test, demo and handover records | WBS 1.5, 3.6–3.8, milestone 4 |

No response-time target, improvement percentage or learning-gain target is specified in the workbook. Agree on measurable thresholds before treating performance or educational effectiveness as an acceptance gate.

## Scope and current terminology

### Committed functional scope from the WBS

- Registration, login, persistent sessions, logout and role-aware navigation.
- A searchable and paginated library of materials and assessments.
- Staff management of materials, four-option questions and assessments.
- Starting and resuming owned attempts, autosave, server-controlled timing, submission and grading.
- Private results with explanations and a personal attempt history.
- Proficiency calculation, adaptive practice and fallback when suitable questions run out.
- Subject/topic classification, assessment supporting materials and related topics.
- LearningRule-based review recommendations and authorized learning analytics.

### Accepted design decisions from the project discussion

- The hierarchy is **Subject → Lesson**. A lesson represents a chapter-sized unit; there is no separate current Chapter entity.
- Materials are document records. PDF bytes live in Supabase Storage; PostgreSQL stores their bucket/path and other metadata. Existing external/local PDF URL support remains.
- A PDF can support several lessons through `lesson_materials`. Questions link through `question_lessons`.
- Materials have no `author_id` account relationship. Assessment creator identity remains separate.
- Difficulty ranges from **1 to 10**; current code permits fractional values.
- Student PDF access uses Flask login and a temporary signed URL; Supabase Auth is not the website's user authentication system.

These decisions extend or refine the original workbook. In particular, WBS 1.7 mentions author metadata; requiring a material uploader/author account would conflict with the later decision to remove it. Original PDF source/authorship can still be collected separately, but is not currently a dedicated database field.

### Not established as requirements

Payments, course enrollment restrictions, email verification, password recovery, an LLM chatbot, generated questions and AI grading of written answers are not committed by this workbook. Do not mark their absence as an acceptance failure without an approved scope change. Adaptive practice and rule-based recommendations are required; a specific AI/LLM provider is not.

## Business rules

| ID | Rule | Basis |
|---|---|---|
| BR-01 | Public registration creates a student; users cannot grant themselves staff privileges. | Role model and WBS 0.1, 1.6, 1.8 |
| BR-02 | Staff write APIs require administrator or teacher permission. Hiding a UI button is insufficient. | WBS 1.8 |
| BR-03 | Students may access only their own attempt results, saved work and recommendations. | WBS 2.3, 2.5, 3.4 |
| BR-04 | A usable multiple-choice question has four nonempty options and exactly one correct option. | Current accepted question format; WBS 2.6 |
| BR-05 | Difficulty must be finite and within 1–10. | Current accepted scale |
| BR-06 | A lesson-content link must use the same subject on both sides. | Current schema constraints |
| BR-07 | Final scores are calculated on the server from accepted answers and assessment points, not from a submitted score field. | WBS 2.4 |
| BR-08 | Reloading or closing a browser must not extend an attempt deadline. Finalizing an attempt repeatedly must not create duplicate results. | WBS 2.3–2.4 |
| BR-09 | Past results must remain interpretable when content is edited. Versioning/snapshot policy needs approval. | Proposed integrity safeguard supporting WBS 2.5; see D-04 |
| BR-10 | A material needs a valid legacy URL or a complete bucket/path pair. Never store an expiring signed URL as the permanent file location. | Accepted storage integration |
| BR-11 | Learner-facing file access must reject inactive materials and inactive subjects. | Accepted file-access implementation; catalogue consistency still needs testing |
| BR-12 | Disabling content hides it from new learner use without deleting learning history. | WBS 1.8, 2.5; historical behavior needs D-04 |
| BR-13 | Adaptive selection must not repeat a question within one attempt and must handle an exhausted pool. | WBS 3.2 |
| BR-14 | Recommendation output must state why content is suggested and handle no-needed-review/no-content states. | WBS 3.4 |

## Decisions needed before final acceptance

| ID | Decision | Suggested owner | Acceptance consequence |
|---|---|---|---|
| D-01 | Define proficiency update, starting level, difficulty bands and selection fallback with worked examples. | Algorithm lead + BA + QA | Blocks precise expected outputs for US-21 and US-22 |
| D-02 | Define maximum open attempts, retake policy and treatment of zero-question assessments. | BA + teacher representative | Blocks policy-specific attempt tests |
| D-03 | Define analytics population, date handling, abandoned/in-progress attempts and omitted-answer treatment. | BA + analytics developer | Blocks final analytics reconciliation |
| D-04 | Define published-content versioning, historical review and removal behavior. | Tech Lead + BA | Blocks historical-integrity acceptance |
| D-05 | Confirm draft lesson visibility and whether all signed-in students may access all active subjects. | BA/PO | Current lesson endpoint exposes drafts; no enrollment model exists |
| D-06 | Define recommendation conditions, thresholds, tie-breaking and available target content. | Algorithm lead + BA | A free-text LearningRule row is not an executable specification |
| D-07 | Agree performance, accessibility and supported-browser targets. | QA + PO | Do not invent numeric nonfunctional targets |

## Delivery acceptance

Treat a story as accepted only when its acceptance criteria have evidence from the exact commit and environment under review. A database table, workbook task status, UI screenshot or successful deployment by itself is insufficient.

The implementation review found working candidates for authentication, catalogue browsing, staff content management, fixed-test grading/review and PDF delivery. Core attempt reliability and the adaptive/reporting scope remain incomplete in the inspected code. See the traceability and test documents for the precise distinctions; no new acceptance test execution is claimed by these documents.
