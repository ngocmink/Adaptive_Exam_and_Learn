# Function and use-case catalogue

Adaptive Exam and Learn · Team 18 · Structure version 1.0 · 20 November 2026

This catalogue organizes the existing WBS-derived requirements. It does not add runtime features or mark any tests passed. Read the [stories](02_USER_STORIES.md) for acceptance criteria and the [traceability index](06_AC_TEST_TRACEABILITY.md) for both lookup directions.

## Meaning of each level

| Level | Meaning in this project | Example |
|---|---|---|
| Function | A coherent product capability, not a database table or sprint task | F-02 Learning library and PDF reading |
| Use case | Actor/system interaction that reaches a goal, including failure paths | UC-05 Read a PDF |
| User story | A smaller user-valued requirement inside the interaction | US-07 Open an authorized PDF |
| Acceptance criterion | A uniquely identified, observable condition for acceptance | US-07.AC2 checks login and active content before signing |
| Test case | Setup, action and expected evidence that verifies one or more criteria | [TC-16](04_ACCEPTANCE_TESTS.md#tc-16) checks anonymous/inactive/missing access |

A WBS item tracks delivery work. It may support multiple functions/use cases; it is not automatically a user story. The hierarchy is a reporting convention for this project. One test may verify several ACs, and one AC may require several positive/negative tests.

## Function index

| Function | Capability | Use cases | WBS |
|---|---|---|---|
| F-01 | Accounts and access | [UC-01](#uc-01), [UC-02](#uc-02), [UC-03](#uc-03) | 1.6, 1.8, 2.5 |
| F-02 | Learning library and PDF reading | [UC-04](#uc-04), [UC-05](#uc-05), [UC-06](#uc-06) | 1.7, 1.9, 3.3 |
| F-03 | Content administration and quality | [UC-07](#uc-07), [UC-08](#uc-08), [UC-09](#uc-09), [UC-10](#uc-10), [UC-11](#uc-11) | 0.4, 1.8, 2.6, 3.3 |
| F-04 | Assessment attempt lifecycle | [UC-12](#uc-12), [UC-13](#uc-13), [UC-14](#uc-14), [UC-15](#uc-15) | 2.1, 2.3, 2.4, 2.7 |
| F-05 | Results and personal history | [UC-16](#uc-16), [UC-17](#uc-17) | 2.5, 2.7 |
| F-06 | Proficiency and adaptive practice | [UC-18](#uc-18), [UC-19](#uc-19) | 3.1, 3.2 |
| F-07 | Supporting content and recommendations | [UC-20](#uc-20), [UC-21](#uc-21) | 3.3, 3.4 |
| F-08 | Learning analytics | [UC-22](#uc-22) | 3.5 |

## Use-case specifications

Preconditions and outcomes below are required behavior. Missing/dependent features stay marked in the earlier code assessment; their inclusion here does not assert implementation.

<a id="uc-01"></a>
### UC-01 Register an account
- **Function:** F-01 Accounts and access.
- **Primary actor:** Visitor.
- **Trigger and preconditions:** Visitor opens registration with an unused email.
- **Main flow:** Enter details → validate and normalize → create a student account with a password hash.
- **Alternative and error flows:** Reject duplicates/invalid inputs; ignore requested staff privileges.
- **Postcondition:** One valid student account or no account on failure.
- **Stories:** [US-01](02_USER_STORIES.md#us-01).

<a id="uc-02"></a>
### UC-02 Sign in and sign out
- **Function:** F-01 Accounts and access.
- **Primary actor:** Registered user.
- **Trigger and preconditions:** User has an account; logout requires a signed-in session.
- **Main flow:** Submit credentials → establish session and role navigation → use private pages → log out.
- **Alternative and error flows:** Reject invalid credentials and invalid CSRF; protected access after logout requires login.
- **Postcondition:** Session belongs to the correct user or is cleared.
- **Stories:** [US-02](02_USER_STORIES.md#us-02), [US-03](02_USER_STORIES.md#us-03).

<a id="uc-03"></a>
### UC-03 Enforce permissions and ownership
- **Function:** F-01 Accounts and access.
- **Primary actor:** Student, teacher, administrator.
- **Trigger and preconditions:** A caller requests a protected operation or private result.
- **Main flow:** Identify database user → check required role/ownership → allow only authorized operation.
- **Alternative and error flows:** Deny anonymous/forged-role/non-owner calls without data leakage.
- **Postcondition:** Protected data and writes remain within the approved role policy.
- **Stories:** [US-04](02_USER_STORIES.md#us-04).

<a id="uc-04"></a>
### UC-04 Discover lessons and materials
- **Function:** F-02 Learning library and PDF reading.
- **Primary actor:** Student.
- **Trigger and preconditions:** A subject catalogue and material records exist.
- **Main flow:** Choose subject/lesson → enter search and filters → inspect paginated material cards.
- **Alternative and error flows:** Handle invalid filters, empty sets, inactive content and multiply-linked documents.
- **Postcondition:** The student identifies the intended material without duplicate cards.
- **Stories:** [US-05](02_USER_STORIES.md#us-05), [US-06](02_USER_STORIES.md#us-06).

<a id="uc-05"></a>
### UC-05 Read a PDF
- **Function:** F-02 Learning library and PDF reading.
- **Primary actor:** Signed-in student.
- **Trigger and preconditions:** An accessible material has a supported URL or private storage location.
- **Main flow:** Select material → check user/content access → obtain file URL → display the correct PDF.
- **Alternative and error flows:** Deny anonymous/inactive/missing content; handle storage failures and expired links.
- **Postcondition:** The correct PDF opens; no backend secret is disclosed.
- **Stories:** [US-07](02_USER_STORIES.md#us-07).

<a id="uc-06"></a>
### UC-06 Discover an assessment
- **Function:** F-02 Learning library and PDF reading.
- **Primary actor:** Student.
- **Trigger and preconditions:** Assessment catalogue contains active tests.
- **Main flow:** Search/filter → inspect subject, type, question count and duration → select assessment.
- **Alternative and error flows:** Handle invalid filters and unavailable records without exposing answer keys.
- **Postcondition:** Student selects an appropriate active assessment.
- **Stories:** [US-08](02_USER_STORIES.md#us-08).

<a id="uc-07"></a>
### UC-07 Maintain material records
- **Function:** F-03 Content administration and quality.
- **Primary actor:** Teacher or administrator.
- **Trigger and preconditions:** Staff is authenticated; storage files may already have been uploaded.
- **Main flow:** Create URL/path-based record → edit metadata or replace source → disable when needed.
- **Alternative and error flows:** Reject incomplete/ambiguous/unsafe locations and unauthorized writes.
- **Postcondition:** Catalogue reflects the authorized update; PDF bytes remain in storage.
- **Stories:** [US-09](02_USER_STORIES.md#us-09).

<a id="uc-08"></a>
### UC-08 Maintain question bank
- **Function:** F-03 Content administration and quality.
- **Primary actor:** Teacher or administrator.
- **Trigger and preconditions:** Staff has classified question content to maintain.
- **Main flow:** Enter question/topic/difficulty/options/explanation → validate → save/edit/disable.
- **Alternative and error flows:** Reject invalid options/difficulty; protect answer-key reads and prior attempts.
- **Postcondition:** Usable question records satisfy the accepted question format.
- **Stories:** [US-10](02_USER_STORIES.md#us-10).

<a id="uc-09"></a>
### UC-09 Maintain assessments
- **Function:** F-03 Content administration and quality.
- **Primary actor:** Teacher or administrator.
- **Trigger and preconditions:** Staff can select reviewed questions for the intended subject.
- **Main flow:** Set assessment metadata and ordered membership → validate → save or toggle activation.
- **Alternative and error flows:** Reject duplicates/invalid references/subject mismatch; apply approved empty-test policy.
- **Postcondition:** A coherent assessment is available or a failed write leaves no partial change.
- **Stories:** [US-11](02_USER_STORIES.md#us-11).

<a id="uc-10"></a>
### UC-10 Maintain lesson-content associations
- **Function:** F-03 Content administration and quality.
- **Primary actor:** Content manager acting as authorized staff.
- **Trigger and preconditions:** Lessons and content exist under known subjects.
- **Main flow:** Choose lesson/content → add or remove association → verify discovery and exact file mapping.
- **Alternative and error flows:** Reject duplicate/cross-subject links; distinguish a title similarity from a real link.
- **Postcondition:** Explicit reusable associations drive the expected lesson results.
- **Stories:** [US-12](02_USER_STORIES.md#us-12).

<a id="uc-11"></a>
### UC-11 Review and import content
- **Function:** F-03 Content administration and quality.
- **Primary actor:** Content reviewer and data maintainer.
- **Trigger and preconditions:** Source content and import fixtures are available.
- **Main flow:** Review sources/answers/classification → validate workbook and files → import → reconcile.
- **Alternative and error flows:** Report invalid/skipped rows, unavailable files, unclear usage rights and import conflicts.
- **Postcondition:** Reviewed content is identifiable and repeat imports do not silently duplicate it.
- **Stories:** [US-25](02_USER_STORIES.md#us-25).

<a id="uc-12"></a>
### UC-12 Start or resume an attempt
- **Function:** F-04 Assessment attempt lifecycle.
- **Primary actor:** Student.
- **Trigger and preconditions:** Student selects an accessible assessment.
- **Main flow:** Start owned attempt → establish identity/start/deadline → resume accepted work if interrupted.
- **Alternative and error flows:** Deny another user's attempt; apply approved retake/open-attempt policy.
- **Postcondition:** One identifiable owned attempt is ready for work.
- **Stories:** [US-13](02_USER_STORIES.md#us-13).

<a id="uc-13"></a>
### UC-13 Save answers while working
- **Function:** F-04 Assessment attempt lifecycle.
- **Primary actor:** Student.
- **Trigger and preconditions:** An owned, unexpired in-progress attempt exists.
- **Main flow:** Change answer → save to server → show acknowledgement → restore accepted state on reload.
- **Alternative and error flows:** Show save failure/offline state; deny late or non-owner changes.
- **Postcondition:** Server-accepted work survives interruption without false saved indicators.
- **Stories:** [US-14](02_USER_STORIES.md#us-14).

<a id="uc-14"></a>
### UC-14 Enforce attempt expiry
- **Function:** F-04 Assessment attempt lifecycle.
- **Primary actor:** System on behalf of the student.
- **Trigger and preconditions:** A server deadline exists for an owned attempt.
- **Main flow:** Display remaining time → enforce deadline on saves/submission → finalize accepted work at expiry.
- **Alternative and error flows:** Handle closed pages, changed client clock and save/finalization races.
- **Postcondition:** Browser behavior cannot extend the server-defined time limit.
- **Stories:** [US-15](02_USER_STORIES.md#us-15).

<a id="uc-15"></a>
### UC-15 Submit and grade once
- **Function:** F-04 Assessment attempt lifecycle.
- **Primary actor:** Student or expiry process.
- **Trigger and preconditions:** An attempt and its accepted answers are available for finalization.
- **Main flow:** Validate served questions/options → calculate score on server → finalize once → return result.
- **Alternative and error flows:** Ignore forged score values; handle blanks, invalid choices, duplicate requests and races.
- **Postcondition:** One authoritative final result with consistent totals and immutable accepted answers.
- **Stories:** [US-16](02_USER_STORIES.md#us-16), [US-17](02_USER_STORIES.md#us-17).

<a id="uc-16"></a>
### UC-16 Review a completed result
- **Function:** F-05 Results and personal history.
- **Primary actor:** Student.
- **Trigger and preconditions:** Student owns the requested completed attempt.
- **Main flow:** Open result → view score/counts/duration → inspect answers and explanations.
- **Alternative and error flows:** Deny non-owner/incomplete result disclosure; apply historical content policy.
- **Postcondition:** Student can understand the original result without exposing another user's data.
- **Stories:** [US-18](02_USER_STORIES.md#us-18).

<a id="uc-17"></a>
### UC-17 Browse personal history
- **Function:** F-05 Results and personal history.
- **Primary actor:** Student.
- **Trigger and preconditions:** Student is authenticated; zero or more past attempts may exist.
- **Main flow:** Open history → browse ordered/paginated own attempts → reopen result or resume valid work.
- **Alternative and error flows:** Handle empty history, unavailable content and tampered IDs.
- **Postcondition:** Only the student's distinct attempts are discoverable.
- **Stories:** [US-19](02_USER_STORIES.md#us-19).

<a id="uc-18"></a>
### UC-18 Calculate learner proficiency
- **Function:** F-06 Proficiency and adaptive practice.
- **Primary actor:** Student and proficiency service.
- **Trigger and preconditions:** Approved D-01 algorithm examples define inputs and expected outputs.
- **Main flow:** Read accepted evidence → initialize/update proficiency → display its topic/subject and explanation.
- **Alternative and error flows:** Handle no history, boundaries and unauthorized access.
- **Postcondition:** An explainable approved proficiency estimate is available.
- **Stories:** [US-21](02_USER_STORIES.md#us-21).

<a id="uc-19"></a>
### UC-19 Select adaptive practice questions
- **Function:** F-06 Proficiency and adaptive practice.
- **Primary actor:** Student.
- **Trigger and preconditions:** An approved selection policy and classified question pool exist.
- **Main flow:** Select topic → serve suitable question → evaluate response → adjust next selection.
- **Alternative and error flows:** Do not repeat; handle sparse/exhausted pools and retain fixed-test behavior.
- **Postcondition:** Practice selection follows approved response-dependent examples.
- **Stories:** [US-22](02_USER_STORIES.md#us-22).

<a id="uc-20"></a>
### UC-20 Discover supporting and related content
- **Function:** F-07 Supporting content and recommendations.
- **Primary actor:** Teacher/administrator and student.
- **Trigger and preconditions:** Assessment/topic relationships and eligible materials exist.
- **Main flow:** Staff attaches/classifies content → student views assessment support → opens authorized targets.
- **Alternative and error flows:** Hide removed/inactive targets and avoid arbitrary unrelated-topic suggestions.
- **Postcondition:** Explicit supporting documents and relevant topics are accessible.
- **Stories:** [US-20](02_USER_STORIES.md#us-20).

<a id="uc-21"></a>
### UC-21 Recommend targeted review
- **Function:** F-07 Supporting content and recommendations.
- **Primary actor:** Student and recommendation service.
- **Trigger and preconditions:** An owned completed attempt and approved D-06 rules are available.
- **Main flow:** Find weak topics → evaluate rules → deduplicate eligible targets → explain recommendations.
- **Alternative and error flows:** Distinguish no review needed, no content and insufficient evidence; deny non-owner access.
- **Postcondition:** Student receives appropriate actionable review suggestions or a clear empty state.
- **Stories:** [US-23](02_USER_STORIES.md#us-23).

<a id="uc-22"></a>
### UC-22 Inspect learning statistics
- **Function:** F-08 Learning analytics.
- **Primary actor:** Teacher or administrator.
- **Trigger and preconditions:** Staff is authenticated and D-03 metric definitions are approved.
- **Main flow:** Choose defined reporting population → aggregate attempts/answers → display reconciled metrics.
- **Alternative and error flows:** Handle no data/zero denominators and deny anonymous/student access.
- **Postcondition:** Learning metrics and weak-topic counts match the agreed definitions.
- **Stories:** [US-24](02_USER_STORIES.md#us-24).

## Trace an actual group feature

```text
F-02 Learning library and PDF reading
  └── UC-05 Read a PDF
       └── US-07 Open an authorized PDF
            ├── US-07.AC1 Correct document → TC-15
            ├── US-07.AC2 Access checks → TC-16
            ├── US-07.AC3 Temporary URL and secrets → TC-17
            ├── US-07.AC4 Storage errors → TC-18
            └── US-07.AC5 Legacy support and expiry behavior → TC-17, TC-19
```

For a defect in [TC-16](04_ACCEPTANCE_TESTS.md#tc-16), reverse lookup identifies US-07.AC2, its story, UC-05 and F-02, then WBS 1.7/1.9 and the accepted storage decision. The code location is `app/library/routes.py::material_file`; signing logic is in `app/common/material_storage.py`.

## ID and change rules

1. Function, UC, US, AC and TC IDs are unique and remain stable after approval; names may change without reusing old IDs.
2. Every story has exactly one primary UC and function in this catalogue. Cross-cutting rules can be referenced elsewhere without copying/redefining the story.
3. AC text lives in the story document; setup/steps/expected results live in the test document; the index records relationships.
4. A new or changed AC must have a planned test or an explicit review/blocking decision. Mapping is planned coverage, not evidence of a Pass.
5. [TC-52](04_ACCEPTANCE_TESTS.md#tc-52)–[TC-54](04_ACCEPTANCE_TESTS.md#tc-54) are engineering/integration checks and are labelled separately rather than assigned fabricated functional requirements.
6. Keep the source WBS, code baseline, implementation assessment and test execution status distinct.
