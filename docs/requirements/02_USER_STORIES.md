# User stories and acceptance criteria

Baseline: `main` at `3d04e11f0450894bd403e64aeb7e548b19180c1f` · 17 November 2026.

Source: workbook **Agile Project Plan**, using WBS IDs and row references. The stories are derived from the plan plus explicitly identified later design decisions. They describe intended behavior, not a claim that the current code already passes. See [Traceability](03_TRACEABILITY.md) for code coverage and [Tests](04_ACCEPTANCE_TESTS.md) for executable checks.

Priority **Core** identifies a dependency for the learning flow; **Planned** identifies later committed WBS scope; neither silently changes the team's Must/Should/Could decision. AC identifiers are local to each story: `US-01.AC1`, for example.

## Accounts and access

### US-01 Register a student account

As a prospective student, I want to register so that I can use the learning website with my own account.

Source: WBS 1.6, row 17 · Priority: Core.

1. Given a valid unused email, name and acceptable password, registration creates one student account and confirms success.
2. Email matching ignores surrounding spaces and letter case; a duplicate normalized email is rejected.
3. Invalid email, missing name or a password shorter than the current six-character minimum is rejected without a partial account. A stronger password policy requires agreement.
4. The stored password is hashed, and role fields supplied by the caller cannot create an administrator or teacher.

Tests: TC-01–TC-03.

### US-02 Log in and retain my session

As a registered user, I want to log in and remain recognized so that I can continue to the appropriate workspace.

Source: WBS 1.6, row 17 · Priority: Core.

1. Correct credentials establish a session identifying the actual database user.
2. Students are directed to the learner workspace; teachers and administrators to the staff workspace.
3. Wrong credentials return an error without an authenticated session or password disclosure.
4. A subsequent authenticated request recognizes the same user; malformed or forged session identity does not grant access.

Tests: TC-04–TC-05.

### US-03 Log out

As a signed-in user, I want to log out so that the browser no longer acts as my account.

Source: WBS 1.6, row 17; supporting account behavior · Priority: Core.

1. Logout clears the authenticated session.
2. Subsequent private requests require login again.
3. State-changing requests require valid CSRF protection; signing in/out does not leave the browser with an unusable token flow.

Tests: TC-06.

### US-04 Enforce role and result ownership

As a student, I want staff actions and other students' private results to remain protected so that access follows the account's actual permissions.

Source: WBS 0.1, 1.8, 2.5 · Priority: Core.

1. Anonymous callers cannot execute staff writes; a signed-in student receives a denial for those APIs.
2. Changing a client-supplied role cannot grant staff permissions.
3. A student cannot read another student's result by changing its attempt ID.
4. Teachers and administrators can manage shared content under the current policy; per-author ownership is not required.

Tests: TC-07, TC-08, TC-35.

## Content discovery and documents

### US-05 Browse subjects and lessons

As a student, I want to navigate a subject's lessons so that I can choose the topic I need.

Source: WBS 1.7, 3.3; accepted Subject → Lesson design · Priority: Core.

1. Subject results identify the subject and show consistent active material/assessment counts.
2. Filtering lessons by a valid subject returns only that subject's lessons, in defined order.
3. Invalid filter values report a validation error rather than silently showing unrelated lessons.
4. An empty subject has an understandable empty state. Draft lesson visibility must follow D-05; the default proposed learner policy is published-only.

Tests: TC-09, TC-10, TC-11.

### US-06 Find learning materials

As a student, I want to search and filter materials so that I can find a suitable document without opening every file.

Source: WBS 1.7, row 18; accepted lesson links · Priority: Core.

1. Search, subject, lesson and supported difficulty filters combine correctly.
2. Cards show a usable title, subject, relevant lesson information and difficulty where available.
3. Pagination totals and records agree; a document linked to multiple lessons appears once per result set.
4. Missing matches show an empty state. Disabled content is unavailable to learners; parent-subject visibility must be consistent.

Tests: TC-12–TC-14.

### US-07 Open an authorized PDF

As a signed-in student, I want to read a selected PDF in the website so that I can study the material I found.

Source: WBS 1.7, 1.9; accepted Supabase integration · Priority: Core.

1. A selected material opens the PDF identified by its actual bucket/path, not another document with a similar name.
2. The file endpoint checks login and active material/subject status before signing.
3. Private storage produces a temporary URL; neither the backend secret nor a permanent signed URL is stored in material records or delivered in page source.
4. Missing configuration, missing files and upstream errors produce controlled errors without leaking credentials.
5. Existing supported PDF URLs still work. An already issued signed URL remains usable until its expiry; logout does not revoke that bearer URL immediately.

Tests: TC-15–TC-19.

### US-08 Find an assessment

As a student, I want to browse assessment details so that I can choose an appropriate test or practice set.

Source: WBS 1.7, 2.6 · Priority: Core.

1. Search and supported subject/lesson/type filters return the correct active assessments.
2. Cards/detail show subject, title, type, question count and duration, as applicable.
3. Public catalogue/detail responses do not include correct answers or explanations that reveal the test answers.
4. Invalid filters and nonexistent/inactive assessment IDs return controlled responses.

Tests: TC-20, TC-21.

## Staff content management

### US-09 Manage material records

As a teacher or administrator, I want to create, update and disable material records so that students see the correct documents.

Source: WBS 1.8, row 19; accepted Supabase integration · Priority: Core.

1. Staff can register an existing uploaded PDF using subject, title, bucket/path and metadata, or use a supported legacy URL.
2. Exactly one source is selected by the management API; incomplete pairs, invalid paths and unapproved buckets are rejected.
3. Editing metadata alone retains the source; replacing the source updates the correct record.
4. Disabling hides the material from normal learner access without deleting its record. Changes appear consistently after refresh.
5. This story registers an already-uploaded PDF. Direct browser-to-storage uploading and automatic Supabase inventory synchronization are separate enhancements.

Tests: TC-22–TC-24.

### US-10 Manage questions

As a teacher or administrator, I want to maintain classified questions so that assessments use correct, reviewable content.

Source: WBS 1.8, 2.6 · Priority: Core.

1. Staff can create/edit/disable a question with subject, topic, difficulty, four options, one correct answer and an explanation.
2. Empty options, multiple/no correct options and nonfinite/out-of-range difficulty are rejected for usable content.
3. Staff question reads support the documented filters and pagination; students cannot use these endpoints to obtain answer keys.
4. Disabled questions are not newly offered to students. Their effect on an existing or historical attempt follows D-04.

Tests: TC-25–TC-27, TC-38.

### US-11 Manage assessments

As a teacher or administrator, I want to choose questions and assessment settings so that students receive a coherent test.

Source: WBS 1.8, 2.6 · Priority: Core.

1. Staff can create/edit a title, subject, type, positive duration, pass threshold and ordered question list.
2. Duplicate question IDs and invalid references are rejected atomically; a failed operation leaves no partial assessment.
3. Included questions belong to the selected subject unless a cross-subject policy is explicitly approved.
4. Staff can disable/reactivate assessments. Zero-question publication follows D-02 rather than an invented default.

Tests: TC-28–TC-30.

### US-12 Maintain correct lesson-content links

As a content manager, I want to associate documents and questions with the correct lessons so that topic navigation is meaningful.

Source: WBS 3.3; accepted lesson design · Priority: Core dependency.

1. A material/question may link to multiple lessons of the same subject without duplicating the original content record.
2. Duplicate link pairs and cross-subject links are rejected.
3. A lesson filter returns its linked documents/questions/assessments as specified; it must not break SQL or duplicate cards.
4. Unlinked records remain identifiable; assigning a similar title alone never establishes a link.
5. A supported manager workflow must exist for maintaining links. Current import support alone does not establish that an admin UI can do it.

Tests: TC-11, TC-14, TC-31.

## Assessment lifecycle

### US-13 Start and resume my attempt

As a student, I want to start or resume my own attempt so that my work has a stable identity and survives interruption.

Source: WBS 2.3, row 24 · Priority: Core.

1. Starting a test creates or retrieves an owned in-progress attempt before submission, with its start time and deadline.
2. Resuming restores accepted answers, question order and remaining time for that attempt.
3. A student cannot resume another user's attempt or change its assessment identity.
4. Retakes and multiple-open-attempt behavior follow D-02.

Tests: TC-32, TC-33.

### US-14 Save work as I answer

As a student, I want my answers saved while working so that a reload or temporary network problem does not silently erase accepted work.

Source: WBS 2.1, 2.3, 2.7 · Priority: Core.

1. Changing an answer sends an owned-attempt save request and indicates saving/saved/error state.
2. Reload restores the last acknowledged answer, including a supported change back to unanswered.
3. A failed save is not displayed as successful; reconnect/retry behavior preserves the distinction between unsaved and server-accepted work.
4. Saves are rejected after finalization or the server deadline and cannot change another user's answers.

Tests: TC-33, TC-34, TC-39.

### US-15 Respect a server-controlled deadline

As a student, I want the displayed remaining time to reflect the server deadline so that all attempts follow the same time limit.

Source: WBS 2.3–2.4 · Priority: Core.

1. Remaining time derives from an immutable server-controlled deadline established at start.
2. Reloading, changing browser time or restarting browser JavaScript does not extend it.
3. Expiry finalizes the attempt from valid saved answers even if the page is closed; late saves/submissions cannot add accepted answers.
4. Boundary/race behavior between save and finalization has a documented, deterministic rule.

Tests: TC-36, TC-37, TC-39.

### US-16 Submit and receive a server-calculated score

As a student, I want to submit my attempt and receive a reliable score so that the result reflects my accepted answers.

Source: WBS 2.4, row 25 · Priority: Core.

1. The server derives correctness from the assessment's valid options and points, ignoring client-supplied scores/correctness flags.
2. A selected option must belong to its question; only questions served for the attempt may be answered.
3. Omitted questions receive no earned points. Percentage equals earned points divided by available points times 100; current display rounds to one decimal.
4. Finalization records completion time, answers and aggregate totals consistently in a transaction.
5. Threshold equality passes when score equals `pass_score`; zero available points follows D-02.

Tests: TC-40–TC-42.

### US-17 Finalize only once

As a student, I want repeated clicks or network retries to return the same final result so that one attempt does not become duplicate submissions.

Source: WBS 2.4, 2.7 · Priority: Core.

1. Sequential or concurrent finalization requests for the same attempt yield one authoritative result.
2. Duplicate requests do not create additional attempt/answer rows or re-award completion.
3. After completion, answer changes are rejected and the stored result remains unchanged.

Tests: TC-43, TC-39.

### US-18 Review my result and explanations

As a student, I want a private result page with explanations so that I can understand errors and omissions.

Source: WBS 2.5, row 26 · Priority: Core.

1. Completed results show score, correct/incorrect/omitted counts and ratios with clear denominators.
2. Review shows the selected answer, correct answer and available explanation for each served question.
3. Duration reflects the actual attempt interval rather than the time taken to process a POST request.
4. Another student cannot open the result. Unsubmitted attempts do not expose completed-test answers.
5. Historical review remains consistent under the approved D-04 content-edit policy.

Tests: TC-35, TC-44, TC-38.

### US-19 Browse my attempt history

As a student, I want to reopen my previous attempts so that I can track and review my practice.

Source: WBS 2.5, 2.7 · Priority: Core.

1. History lists only the signed-in user's attempts with assessment, date, status and result where final.
2. Entries open the corresponding authorized result or owned resume flow.
3. Multiple attempts remain distinct; empty history and unavailable content have understandable states.
4. Ordering and pagination are stable and do not leak another user's records.

Tests: TC-45.

## Adaptive learning and reporting

### US-20 Discover assessment supporting materials

As a student, I want supporting PDFs and related topics beside an assessment so that I know what to study before or after practice.

Source: WBS 3.3, row 33 · Priority: Planned.

1. Staff can classify an assessment by subject/topic and add/remove its supporting materials through a supported workflow.
2. Students can view and open the linked active materials with the same access checks as the main library.
3. Related topics come from approved subject/content relationships, not arbitrary unrelated suggestions.
4. A lesson-based assessment filter alone does not satisfy explicit assessment-material attachments or related-topic presentation.

Tests: TC-46.

### US-21 Understand my current proficiency

As a student, I want an explainable proficiency estimate for a topic/subject so that I can select appropriate practice.

Source: WBS 3.1–3.2, rows 31–32 · Priority: Planned.

1. The agreed D-01 algorithm defines the initial state and uses accepted results to update proficiency.
2. Worked input/output examples, including no-history and boundary cases, match the implementation.
3. The displayed estimate identifies its subject/topic and is not simply a question difficulty value.
4. Only authorized users access personal proficiency; a dedicated persistence table is a design option, not an assumed requirement.

Tests: TC-47.

### US-22 Practise adaptively

As a student, I want the next practice question to respond to my performance so that practice stays appropriate to my current ability.

Source: WBS 3.2, row 32 · Priority: Planned.

1. Initial selection uses the chosen topic and current proficiency under D-01.
2. Correct and incorrect responses produce the expected next-question changes in approved examples.
3. A question is not repeated within the same practice attempt.
4. Exhausted/sparse pools use the agreed fallback or a clear completion state; fixed assessments still work.

Tests: TC-48.

### US-23 Receive targeted review suggestions

As a student, I want suggestions based on my completed mistakes so that I can focus on topics that need review.

Source: WBS 3.4, row 34 · Priority: Planned.

1. Only a completed owned attempt produces personal suggestions under approved D-06 rules.
2. Recommendations match weak topics and appropriate difficulty and reference active, accessible materials/practice.
3. Each suggestion explains its reason; duplicate target content is not repeated.
4. Distinct messages cover no review needed, no matching content and insufficient evidence.
5. Other students cannot access or influence my recommendation output.

Tests: TC-49.

### US-24 Inspect learning analytics

As an administrator or teacher, I want accurate learning statistics so that I can identify weak topics and assess content usage.

Source: WBS 3.5, row 35 · Priority: Planned.

1. Authorized staff see started/completed counts, completion rate, average score and score distribution for a defined population.
2. They see highest-error questions/topics with answer counts, using the agreed D-03 omitted-answer rule.
3. Figures reconcile with the known fixture; no-data and zero-denominator states are explicit.
4. Anonymous callers and students cannot access the analytics API or dashboard.

Tests: TC-50.

### US-25 Prepare usable learning content

As a content reviewer, I want validated questions, assessments and PDF references so that student workflows use coherent, correctly linked data.

Source: WBS 0.4, 2.6; accepted collection workflow · Priority: Core dependency.

1. Questions have reviewed answers, explanations, topic and 1–10 difficulty before acceptance as demo content.
2. Each assessment contains the intended questions, valid duration and activation state.
3. Each material's actual file opens, belongs to the intended subject and has the intended lesson links when provided.
4. An import can be repeated without silently duplicating or moving existing content; rejected/skipped rows are accounted for.
5. Source rights are checked by the team; current code does not implement a content-approval workflow.

Tests: TC-31, TC-51.

## Engineering enablers are tracked separately

WBS 0.1–0.4, 1.1–1.5, 1.9, 2.1–2.2, 2.7–2.8, 3.1, 3.6–3.8 and milestone 4 also require planning, UX, architecture, migrations, CI, testing and handover evidence. They are not all end-user features and are mapped separately in [Traceability](03_TRACEABILITY.md). Security/setup verification appears in TC-52–TC-54.
