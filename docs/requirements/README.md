# Requirements navigation

Use the hierarchy **Function → Use case → User story → Acceptance criterion → Test case**.

| File | Purpose |
|---|---|
| [01 Business problem](01_BUSINESS_PROBLEM.md) | Why the system exists, scope, users, business rules and unresolved decisions |
| [05 Functions and use cases](05_FUNCTIONS_AND_USE_CASES.md) | Start here for the 8 functional areas and 22 actor/system flows |
| [02 User stories](02_USER_STORIES.md) | 25 stories organized under their function and UC, with explicit AC IDs |
| [06 AC and test index](06_AC_TEST_TRACEABILITY.md) | Forward and reverse lookup across the hierarchy |
| [04 Acceptance tests](04_ACCEPTANCE_TESTS.md) | 55 planned test cases with fixtures, actions, expectations and AC references |
| [03 Code comparison](03_TRACEABILITY.md) | Existing WBS-to-code assessment and implementation gaps |

Example: **F-02 → UC-05 → US-07 → US-07.AC2 → TC-16** verifies that reading a PDF checks login and content access before generating a signed URL.

Structure updated 20 November 2026. The earlier code-review baseline remains 17 November 2026 at `3d04e11f0450894bd403e64aeb7e548b19180c1f`. This update reorganizes requirements and planned tests; it does not re-evaluate current code or execute tests. Existing IDs were retained. New TC-55 covers source-rights review previously stated without an explicit test.
