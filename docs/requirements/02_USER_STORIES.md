# User stories organized by function and use case

Structure updated: 20 November 2026. Requirement content and implementation assessment retain the 17 November baseline at `3d04e11f0450894bd403e64aeb7e548b19180c1f`; this restructuring is not a new runtime review.

Read [Function and use-case catalogue](05_FUNCTIONS_AND_USE_CASES.md) first. Each story has one primary function/use case; cross-cutting permissions may support many flows. Existing `US-xx` and `TC-xx` IDs are preserved. Each criterion now has an explicit globally identifiable `US-xx.ACn` ID.

Navigation: [Business problem](01_BUSINESS_PROBLEM.md) · [Code assessment](03_TRACEABILITY.md) · [Test cases](04_ACCEPTANCE_TESTS.md) · [AC and reverse test index](06_AC_TEST_TRACEABILITY.md).

Core/Planned priorities retain their previous meaning and do not replace PO approval. Acceptance statements describe intended behavior, not passing implementation.

## F-01 Accounts and access
WBS scope: 1.6, 1.8, 2.5.

### UC-01 Register an account

<a id="us-01"></a>
#### US-01 Register a student account
**Parent:** F-01 → UC-01.

As a prospective student, I want to register so that I can use the learning website with my own account.

Source: WBS 1.6, row 17 · Priority: Core.

1. <a id="us-01-ac1"></a>**US-01.AC1** — Given a valid unused email, name and acceptable password, registration creates one student account and confirms success.
2. <a id="us-01-ac2"></a>**US-01.AC2** — Email matching ignores surrounding spaces and letter case; a duplicate normalized email is rejected.
3. <a id="us-01-ac3"></a>**US-01.AC3** — Invalid email, missing name or a password shorter than the current six-character minimum is rejected without a partial account. A stronger password policy requires agreement.
4. <a id="us-01-ac4"></a>**US-01.AC4** — The stored password is hashed, and role fields supplied by the caller cannot create an administrator or teacher.

Tests: TC-01, TC-02, TC-03. See the AC index for the exact criterion mapping.

### UC-02 Sign in and sign out

<a id="us-02"></a>
#### US-02 Log in and retain my session
**Parent:** F-01 → UC-02.

As a registered user, I want to log in and remain recognized so that I can continue to the appropriate workspace.

Source: WBS 1.6, row 17 · Priority: Core.

1. <a id="us-02-ac1"></a>**US-02.AC1** — Correct credentials establish a session identifying the actual database user.
2. <a id="us-02-ac2"></a>**US-02.AC2** — Students are directed to the learner workspace; teachers and administrators to the staff workspace.
3. <a id="us-02-ac3"></a>**US-02.AC3** — Wrong credentials return an error without an authenticated session or password disclosure.
4. <a id="us-02-ac4"></a>**US-02.AC4** — A subsequent authenticated request recognizes the same user; malformed or forged session identity does not grant access.

Tests: TC-04, TC-05. See the AC index for the exact criterion mapping.

<a id="us-03"></a>
#### US-03 Log out
**Parent:** F-01 → UC-02.

As a signed-in user, I want to log out so that the browser no longer acts as my account.

Source: WBS 1.6, row 17; supporting account behavior · Priority: Core.

1. <a id="us-03-ac1"></a>**US-03.AC1** — Logout clears the authenticated session.
2. <a id="us-03-ac2"></a>**US-03.AC2** — Subsequent private requests require login again.
3. <a id="us-03-ac3"></a>**US-03.AC3** — State-changing requests require valid CSRF protection; signing in/out does not leave the browser with an unusable token flow.

Tests: TC-06. See the AC index for the exact criterion mapping.

### UC-03 Enforce permissions and ownership

<a id="us-04"></a>
#### US-04 Enforce role and result ownership
**Parent:** F-01 → UC-03.

As a student, I want staff actions and other students' private results to remain protected so that access follows the account's actual permissions.

Source: WBS 0.1, 1.8, 2.5 · Priority: Core.

1. <a id="us-04-ac1"></a>**US-04.AC1** — Anonymous callers cannot execute staff writes; a signed-in student receives a denial for those APIs.
2. <a id="us-04-ac2"></a>**US-04.AC2** — Changing a client-supplied role cannot grant staff permissions.
3. <a id="us-04-ac3"></a>**US-04.AC3** — A student cannot read another student's result by changing its attempt ID.
4. <a id="us-04-ac4"></a>**US-04.AC4** — Teachers and administrators can manage shared content under the current policy; per-author ownership is not required.

Tests: TC-05, TC-07, TC-08, TC-35. See the AC index for the exact criterion mapping.

## F-02 Learning library and PDF reading
WBS scope: 1.7, 1.9, 3.3.

### UC-04 Discover lessons and materials

<a id="us-05"></a>
#### US-05 Browse subjects and lessons
**Parent:** F-02 → UC-04.

As a student, I want to navigate a subject's lessons so that I can choose the topic I need.

Source: WBS 1.7, 3.3; accepted Subject → Lesson design · Priority: Core.

1. <a id="us-05-ac1"></a>**US-05.AC1** — Subject results identify the subject and show consistent active material/assessment counts.
2. <a id="us-05-ac2"></a>**US-05.AC2** — Filtering lessons by a valid subject returns only that subject's lessons, in defined order.
3. <a id="us-05-ac3"></a>**US-05.AC3** — Invalid filter values report a validation error rather than silently showing unrelated lessons.
4. <a id="us-05-ac4"></a>**US-05.AC4** — An empty subject has an understandable empty state. Draft lesson visibility must follow D-05; the default proposed learner policy is published-only.

Tests: TC-09, TC-10, TC-11, TC-13. See the AC index for the exact criterion mapping.

<a id="us-06"></a>
#### US-06 Find learning materials
**Parent:** F-02 → UC-04.

As a student, I want to search and filter materials so that I can find a suitable document without opening every file.

Source: WBS 1.7, row 18; accepted lesson links · Priority: Core.

1. <a id="us-06-ac1"></a>**US-06.AC1** — Search, subject, lesson and supported difficulty filters combine correctly.
2. <a id="us-06-ac2"></a>**US-06.AC2** — Cards show a usable title, subject, relevant lesson information and difficulty where available.
3. <a id="us-06-ac3"></a>**US-06.AC3** — Pagination totals and records agree; a document linked to multiple lessons appears once per result set.
4. <a id="us-06-ac4"></a>**US-06.AC4** — Missing matches show an empty state. Disabled content is unavailable to learners; parent-subject visibility must be consistent.

Tests: TC-12, TC-13, TC-14, TC-24. See the AC index for the exact criterion mapping.

### UC-05 Read a PDF

<a id="us-07"></a>
#### US-07 Open an authorized PDF
**Parent:** F-02 → UC-05.

As a signed-in student, I want to read a selected PDF in the website so that I can study the material I found.

Source: WBS 1.7, 1.9; accepted Supabase integration · Priority: Core.

1. <a id="us-07-ac1"></a>**US-07.AC1** — A selected material opens the PDF identified by its actual bucket/path, not another document with a similar name.
2. <a id="us-07-ac2"></a>**US-07.AC2** — The file endpoint checks login and active material/subject status before signing.
3. <a id="us-07-ac3"></a>**US-07.AC3** — Private storage produces a temporary URL; neither the backend secret nor a permanent signed URL is stored in material records or delivered in page source.
4. <a id="us-07-ac4"></a>**US-07.AC4** — Missing configuration, missing files and upstream errors produce controlled errors without leaking credentials.
5. <a id="us-07-ac5"></a>**US-07.AC5** — Existing supported PDF URLs still work. An already issued signed URL remains usable until its expiry; logout does not revoke that bearer URL immediately.

Tests: TC-15, TC-16, TC-17, TC-18, TC-19. See the AC index for the exact criterion mapping.

### UC-06 Discover an assessment

<a id="us-08"></a>
#### US-08 Find an assessment
**Parent:** F-02 → UC-06.

As a student, I want to browse assessment details so that I can choose an appropriate test or practice set.

Source: WBS 1.7, 2.6 · Priority: Core.

1. <a id="us-08-ac1"></a>**US-08.AC1** — Search and supported subject/lesson/type filters return the correct active assessments.
2. <a id="us-08-ac2"></a>**US-08.AC2** — Cards/detail show subject, title, type, question count and duration, as applicable.
3. <a id="us-08-ac3"></a>**US-08.AC3** — Public catalogue/detail responses do not include correct answers or explanations that reveal the test answers.
4. <a id="us-08-ac4"></a>**US-08.AC4** — Invalid filters and nonexistent/inactive assessment IDs return controlled responses.

Tests: TC-20, TC-21. See the AC index for the exact criterion mapping.

## F-03 Content administration and quality
WBS scope: 0.4, 1.8, 2.6, 3.3.

### UC-07 Maintain material records

<a id="us-09"></a>
#### US-09 Manage material records
**Parent:** F-03 → UC-07.

As a teacher or administrator, I want to create, update and disable material records so that students see the correct documents.

Source: WBS 1.8, row 19; accepted Supabase integration · Priority: Core.

1. <a id="us-09-ac1"></a>**US-09.AC1** — Staff can register an existing uploaded PDF using subject, title, bucket/path and metadata, or use a supported legacy URL.
2. <a id="us-09-ac2"></a>**US-09.AC2** — Exactly one source is selected by the management API; incomplete pairs, invalid paths and unapproved buckets are rejected.
3. <a id="us-09-ac3"></a>**US-09.AC3** — Editing metadata alone retains the source; replacing the source updates the correct record.
4. <a id="us-09-ac4"></a>**US-09.AC4** — Disabling hides the material from normal learner access without deleting its record. Changes appear consistently after refresh.
5. <a id="us-09-ac5"></a>**US-09.AC5** — This story registers an already-uploaded PDF. Direct browser-to-storage uploading and automatic Supabase inventory synchronization are separate enhancements.

Tests: TC-22, TC-23, TC-24, TC-54. See the AC index for the exact criterion mapping.

### UC-08 Maintain question bank

<a id="us-10"></a>
#### US-10 Manage questions
**Parent:** F-03 → UC-08.

As a teacher or administrator, I want to maintain classified questions so that assessments use correct, reviewable content.

Source: WBS 1.8, 2.6 · Priority: Core.

1. <a id="us-10-ac1"></a>**US-10.AC1** — Staff can create/edit/disable a question with subject, topic, difficulty, four options, one correct answer and an explanation.
2. <a id="us-10-ac2"></a>**US-10.AC2** — Empty options, multiple/no correct options and nonfinite/out-of-range difficulty are rejected for usable content.
3. <a id="us-10-ac3"></a>**US-10.AC3** — Staff question reads support the documented filters and pagination; students cannot use these endpoints to obtain answer keys.
4. <a id="us-10-ac4"></a>**US-10.AC4** — Disabled questions are not newly offered to students. Their effect on an existing or historical attempt follows D-04.

Tests: TC-25, TC-26, TC-27, TC-38. See the AC index for the exact criterion mapping.

### UC-09 Maintain assessments

<a id="us-11"></a>
#### US-11 Manage assessments
**Parent:** F-03 → UC-09.

As a teacher or administrator, I want to choose questions and assessment settings so that students receive a coherent test.

Source: WBS 1.8, 2.6 · Priority: Core.

1. <a id="us-11-ac1"></a>**US-11.AC1** — Staff can create/edit a title, subject, type, positive duration, pass threshold and ordered question list.
2. <a id="us-11-ac2"></a>**US-11.AC2** — Duplicate question IDs and invalid references are rejected atomically; a failed operation leaves no partial assessment.
3. <a id="us-11-ac3"></a>**US-11.AC3** — Included questions belong to the selected subject unless a cross-subject policy is explicitly approved.
4. <a id="us-11-ac4"></a>**US-11.AC4** — Staff can disable/reactivate assessments. Zero-question publication follows D-02 rather than an invented default.

Tests: TC-28, TC-29, TC-30. See the AC index for the exact criterion mapping.

### UC-10 Maintain lesson-content associations

<a id="us-12"></a>
#### US-12 Maintain correct lesson-content links
**Parent:** F-03 → UC-10.

As a content manager, I want to associate documents and questions with the correct lessons so that topic navigation is meaningful.

Source: WBS 3.3; accepted lesson design · Priority: Core dependency.

1. <a id="us-12-ac1"></a>**US-12.AC1** — A material/question may link to multiple lessons of the same subject without duplicating the original content record.
2. <a id="us-12-ac2"></a>**US-12.AC2** — Duplicate link pairs and cross-subject links are rejected.
3. <a id="us-12-ac3"></a>**US-12.AC3** — A lesson filter returns its linked documents/questions/assessments as specified; it must not break SQL or duplicate cards.
4. <a id="us-12-ac4"></a>**US-12.AC4** — Unlinked records remain identifiable; assigning a similar title alone never establishes a link.
5. <a id="us-12-ac5"></a>**US-12.AC5** — A supported manager workflow must exist for maintaining links. Current import support alone does not establish that an admin UI can do it.

Tests: TC-11, TC-14, TC-31. See the AC index for the exact criterion mapping.

### UC-11 Review and import content

<a id="us-25"></a>
#### US-25 Prepare usable learning content
**Parent:** F-03 → UC-11.

As a content reviewer, I want validated questions, assessments and PDF references so that student workflows use coherent, correctly linked data.

Source: WBS 0.4, 2.6; accepted collection workflow · Priority: Core dependency.

1. <a id="us-25-ac1"></a>**US-25.AC1** — Questions have reviewed answers, explanations, topic and 1–10 difficulty before acceptance as demo content.
2. <a id="us-25-ac2"></a>**US-25.AC2** — Each assessment contains the intended questions, valid duration and activation state.
3. <a id="us-25-ac3"></a>**US-25.AC3** — Each material's actual file opens, belongs to the intended subject and has the intended lesson links when provided.
4. <a id="us-25-ac4"></a>**US-25.AC4** — An import can be repeated without silently duplicating or moving existing content; rejected/skipped rows are accounted for.
5. <a id="us-25-ac5"></a>**US-25.AC5** — Source rights are checked by the team; current code does not implement a content-approval workflow.

Tests: TC-15, TC-25, TC-28, TC-31, TC-51, TC-55. See the AC index for the exact criterion mapping.

## F-04 Assessment attempt lifecycle
WBS scope: 2.1, 2.3, 2.4, 2.7.

### UC-12 Start or resume an attempt

<a id="us-13"></a>
#### US-13 Start and resume my attempt
**Parent:** F-04 → UC-12.

As a student, I want to start or resume my own attempt so that my work has a stable identity and survives interruption.

Source: WBS 2.3, row 24 · Priority: Core.

1. <a id="us-13-ac1"></a>**US-13.AC1** — Starting a test creates or retrieves an owned in-progress attempt before submission, with its start time and deadline.
2. <a id="us-13-ac2"></a>**US-13.AC2** — Resuming restores accepted answers, question order and remaining time for that attempt.
3. <a id="us-13-ac3"></a>**US-13.AC3** — A student cannot resume another user's attempt or change its assessment identity.
4. <a id="us-13-ac4"></a>**US-13.AC4** — Retakes and multiple-open-attempt behavior follow D-02.

Tests: TC-32, TC-33, TC-35, TC-42. See the AC index for the exact criterion mapping.

### UC-13 Save answers while working

<a id="us-14"></a>
#### US-14 Save work as I answer
**Parent:** F-04 → UC-13.

As a student, I want my answers saved while working so that a reload or temporary network problem does not silently erase accepted work.

Source: WBS 2.1, 2.3, 2.7 · Priority: Core.

1. <a id="us-14-ac1"></a>**US-14.AC1** — Changing an answer sends an owned-attempt save request and indicates saving/saved/error state.
2. <a id="us-14-ac2"></a>**US-14.AC2** — Reload restores the last acknowledged answer, including a supported change back to unanswered.
3. <a id="us-14-ac3"></a>**US-14.AC3** — A failed save is not displayed as successful; reconnect/retry behavior preserves the distinction between unsaved and server-accepted work.
4. <a id="us-14-ac4"></a>**US-14.AC4** — Saves are rejected after finalization or the server deadline and cannot change another user's answers.

Tests: TC-33, TC-34, TC-35, TC-39. See the AC index for the exact criterion mapping.

### UC-14 Enforce attempt expiry

<a id="us-15"></a>
#### US-15 Respect a server-controlled deadline
**Parent:** F-04 → UC-14.

As a student, I want the displayed remaining time to reflect the server deadline so that all attempts follow the same time limit.

Source: WBS 2.3–2.4 · Priority: Core.

1. <a id="us-15-ac1"></a>**US-15.AC1** — Remaining time derives from an immutable server-controlled deadline established at start.
2. <a id="us-15-ac2"></a>**US-15.AC2** — Reloading, changing browser time or restarting browser JavaScript does not extend it.
3. <a id="us-15-ac3"></a>**US-15.AC3** — Expiry finalizes the attempt from valid saved answers even if the page is closed; late saves/submissions cannot add accepted answers.
4. <a id="us-15-ac4"></a>**US-15.AC4** — Boundary/race behavior between save and finalization has a documented, deterministic rule.

Tests: TC-32, TC-36, TC-37, TC-39. See the AC index for the exact criterion mapping.

### UC-15 Submit and grade once

<a id="us-16"></a>
#### US-16 Submit and receive a server-calculated score
**Parent:** F-04 → UC-15.

As a student, I want to submit my attempt and receive a reliable score so that the result reflects my accepted answers.

Source: WBS 2.4, row 25 · Priority: Core.

1. <a id="us-16-ac1"></a>**US-16.AC1** — The server derives correctness from the assessment's valid options and points, ignoring client-supplied scores/correctness flags.
2. <a id="us-16-ac2"></a>**US-16.AC2** — A selected option must belong to its question; only questions served for the attempt may be answered.
3. <a id="us-16-ac3"></a>**US-16.AC3** — Omitted questions receive no earned points. Percentage equals earned points divided by available points times 100; current display rounds to one decimal.
4. <a id="us-16-ac4"></a>**US-16.AC4** — Finalization records completion time, answers and aggregate totals consistently in a transaction.
5. <a id="us-16-ac5"></a>**US-16.AC5** — Threshold equality passes when score equals `pass_score`; zero available points follows D-02.

Tests: TC-30, TC-40, TC-41, TC-42, TC-43. See the AC index for the exact criterion mapping.

<a id="us-17"></a>
#### US-17 Finalize only once
**Parent:** F-04 → UC-15.

As a student, I want repeated clicks or network retries to return the same final result so that one attempt does not become duplicate submissions.

Source: WBS 2.4, 2.7 · Priority: Core.

1. <a id="us-17-ac1"></a>**US-17.AC1** — Sequential or concurrent finalization requests for the same attempt yield one authoritative result.
2. <a id="us-17-ac2"></a>**US-17.AC2** — Duplicate requests do not create additional attempt/answer rows or re-award completion.
3. <a id="us-17-ac3"></a>**US-17.AC3** — After completion, answer changes are rejected and the stored result remains unchanged.

Tests: TC-39, TC-43. See the AC index for the exact criterion mapping.

## F-05 Results and personal history
WBS scope: 2.5, 2.7.

### UC-16 Review a completed result

<a id="us-18"></a>
#### US-18 Review my result and explanations
**Parent:** F-05 → UC-16.

As a student, I want a private result page with explanations so that I can understand errors and omissions.

Source: WBS 2.5, row 26 · Priority: Core.

1. <a id="us-18-ac1"></a>**US-18.AC1** — Completed results show score, correct/incorrect/omitted counts and ratios with clear denominators.
2. <a id="us-18-ac2"></a>**US-18.AC2** — Review shows the selected answer, correct answer and available explanation for each served question.
3. <a id="us-18-ac3"></a>**US-18.AC3** — Duration reflects the actual attempt interval rather than the time taken to process a POST request.
4. <a id="us-18-ac4"></a>**US-18.AC4** — Another student cannot open the result. Unsubmitted attempts do not expose completed-test answers.
5. <a id="us-18-ac5"></a>**US-18.AC5** — Historical review remains consistent under the approved D-04 content-edit policy.

Tests: TC-32, TC-35, TC-38, TC-40, TC-44. See the AC index for the exact criterion mapping.

### UC-17 Browse personal history

<a id="us-19"></a>
#### US-19 Browse my attempt history
**Parent:** F-05 → UC-17.

As a student, I want to reopen my previous attempts so that I can track and review my practice.

Source: WBS 2.5, 2.7 · Priority: Core.

1. <a id="us-19-ac1"></a>**US-19.AC1** — History lists only the signed-in user's attempts with assessment, date, status and result where final.
2. <a id="us-19-ac2"></a>**US-19.AC2** — Entries open the corresponding authorized result or owned resume flow.
3. <a id="us-19-ac3"></a>**US-19.AC3** — Multiple attempts remain distinct; empty history and unavailable content have understandable states.
4. <a id="us-19-ac4"></a>**US-19.AC4** — Ordering and pagination are stable and do not leak another user's records.

Tests: TC-45. See the AC index for the exact criterion mapping.

## F-06 Proficiency and adaptive practice
WBS scope: 3.1, 3.2.

### UC-18 Calculate learner proficiency

<a id="us-21"></a>
#### US-21 Understand my current proficiency
**Parent:** F-06 → UC-18.

As a student, I want an explainable proficiency estimate for a topic/subject so that I can select appropriate practice.

Source: WBS 3.1–3.2, rows 31–32 · Priority: Planned.

1. <a id="us-21-ac1"></a>**US-21.AC1** — The agreed D-01 algorithm defines the initial state and uses accepted results to update proficiency.
2. <a id="us-21-ac2"></a>**US-21.AC2** — Worked input/output examples, including no-history and boundary cases, match the implementation.
3. <a id="us-21-ac3"></a>**US-21.AC3** — The displayed estimate identifies its subject/topic and is not simply a question difficulty value.
4. <a id="us-21-ac4"></a>**US-21.AC4** — Only authorized users access personal proficiency; a dedicated persistence table is a design option, not an assumed requirement.

Tests: TC-47. See the AC index for the exact criterion mapping.

### UC-19 Select adaptive practice questions

<a id="us-22"></a>
#### US-22 Practise adaptively
**Parent:** F-06 → UC-19.

As a student, I want the next practice question to respond to my performance so that practice stays appropriate to my current ability.

Source: WBS 3.2, row 32 · Priority: Planned.

1. <a id="us-22-ac1"></a>**US-22.AC1** — Initial selection uses the chosen topic and current proficiency under D-01.
2. <a id="us-22-ac2"></a>**US-22.AC2** — Correct and incorrect responses produce the expected next-question changes in approved examples.
3. <a id="us-22-ac3"></a>**US-22.AC3** — A question is not repeated within the same practice attempt.
4. <a id="us-22-ac4"></a>**US-22.AC4** — Exhausted/sparse pools use the agreed fallback or a clear completion state; fixed assessments still work.

Tests: TC-48. See the AC index for the exact criterion mapping.

## F-07 Supporting content and recommendations
WBS scope: 3.3, 3.4.

### UC-20 Discover supporting and related content

<a id="us-20"></a>
#### US-20 Discover assessment supporting materials
**Parent:** F-07 → UC-20.

As a student, I want supporting PDFs and related topics beside an assessment so that I know what to study before or after practice.

Source: WBS 3.3, row 33 · Priority: Planned.

1. <a id="us-20-ac1"></a>**US-20.AC1** — Staff can classify an assessment by subject/topic and add/remove its supporting materials through a supported workflow.
2. <a id="us-20-ac2"></a>**US-20.AC2** — Students can view and open the linked active materials with the same access checks as the main library.
3. <a id="us-20-ac3"></a>**US-20.AC3** — Related topics come from approved subject/content relationships, not arbitrary unrelated suggestions.
4. <a id="us-20-ac4"></a>**US-20.AC4** — A lesson-based assessment filter alone does not satisfy explicit assessment-material attachments or related-topic presentation.

Tests: TC-46. See the AC index for the exact criterion mapping.

### UC-21 Recommend targeted review

<a id="us-23"></a>
#### US-23 Receive targeted review suggestions
**Parent:** F-07 → UC-21.

As a student, I want suggestions based on my completed mistakes so that I can focus on topics that need review.

Source: WBS 3.4, row 34 · Priority: Planned.

1. <a id="us-23-ac1"></a>**US-23.AC1** — Only a completed owned attempt produces personal suggestions under approved D-06 rules.
2. <a id="us-23-ac2"></a>**US-23.AC2** — Recommendations match weak topics and appropriate difficulty and reference active, accessible materials/practice.
3. <a id="us-23-ac3"></a>**US-23.AC3** — Each suggestion explains its reason; duplicate target content is not repeated.
4. <a id="us-23-ac4"></a>**US-23.AC4** — Distinct messages cover no review needed, no matching content and insufficient evidence.
5. <a id="us-23-ac5"></a>**US-23.AC5** — Other students cannot access or influence my recommendation output.

Tests: TC-49. See the AC index for the exact criterion mapping.

## F-08 Learning analytics
WBS scope: 3.5.

### UC-22 Inspect learning statistics

<a id="us-24"></a>
#### US-24 Inspect learning analytics
**Parent:** F-08 → UC-22.

As an administrator or teacher, I want accurate learning statistics so that I can identify weak topics and assess content usage.

Source: WBS 3.5, row 35 · Priority: Planned.

1. <a id="us-24-ac1"></a>**US-24.AC1** — Authorized staff see started/completed counts, completion rate, average score and score distribution for a defined population.
2. <a id="us-24-ac2"></a>**US-24.AC2** — They see highest-error questions/topics with answer counts, using the agreed D-03 omitted-answer rule.
3. <a id="us-24-ac3"></a>**US-24.AC3** — Figures reconcile with the known fixture; no-data and zero-denominator states are explicit.
4. <a id="us-24-ac4"></a>**US-24.AC4** — Anonymous callers and students cannot access the analytics API or dashboard.

Tests: TC-50. See the AC index for the exact criterion mapping.

## Engineering enablers

WBS planning, UX, architecture, CI, migrations and handover remain in the engineering section of [Code traceability](03_TRACEABILITY.md). They are not forced into student-facing functions. TC-52–TC-54 retain explicit enabler links.
