# Project Workflow

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md`
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation
3. **Test-Driven Development:** Write unit tests before implementing functionality
4. **High Code Coverage:** Aim for >80% code coverage for all modules
5. **User Experience First:** Every decision should prioritize user experience
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use `CI=true` for watch-mode tools (tests, linters) to ensure single execution.

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1. **Select Task:** Choose the next available task from `plan.md` in sequential order

2. **Mark In Progress:** Before beginning work, edit `plan.md` and change the task from `[ ]` to `[~]`

3. **Write Failing Tests (Red Phase):**
   - Create a new test file for the feature or bug fix.
   - Write one or more unit tests that clearly define the expected behavior and acceptance criteria for the task.
   - **CRITICAL:** Run the tests and confirm that they fail as expected. This is the "Red" phase of TDD. Do not proceed until you have failing tests.

4. **Implement to Pass Tests (Green Phase):**
   - Write the minimum amount of application code necessary to make the failing tests pass.
   - Run the test suite again and confirm that all tests now pass. This is the "Green" phase.

5. **Refactor (Optional but Recommended):**
   - With the safety of passing tests, refactor the implementation code and the test code to improve clarity, remove duplication, and enhance performance without changing the external behavior.
   - Rerun tests to ensure they still pass after refactoring.

6. **Verify Coverage:** Run coverage reports using the project's chosen tools (e.g., `pytest --cov=app`). Target: >80% coverage for new code.

7. **Document Deviations:** If implementation differs from tech stack:
   - **STOP** implementation
   - Update `tech-stack.md` with new design
   - Add dated note explaining the change
   - Resume implementation

8. **Record Completion in Plan:** Update `plan.md`, find the line for the completed task, and update its status from `[~]` to `[x]`. 
   *Note: Committing code and plan updates is deferred until the entire phase is complete.*

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `plan.md`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**
    -   **Step 2.1: Determine Phase Scope:** Identify files changed since the last phase checkpoint.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only <previous_checkpoint_sha> HEAD` (or since first commit if no previous checkpoint).
    -   **Step 2.3: Verify and Create Tests:** Ensure all new code has corresponding tests following project conventions.

3.  **Execute Automated Tests with Proactive Debugging:**
    -   Announce and run the automated test suite (e.g., `pytest` and `playwright test`).
    -   If tests fail, debug and fix (maximum two attempts before seeking guidance).

4.  **Propose a Detailed, Actionable Manual Verification Plan:**
    -   Analyze `product.md`, `product-guidelines.md`, and `plan.md` to define user-facing goals.
    -   Present a step-by-step verification plan with expected outcomes.

5.  **Await Explicit User Feedback:**
    -   Pause for the user to confirm: "Does this meet your expectations?"

6.  **Create Phase Checkpoint Commit:**
    -   Stage all code changes and the updated `plan.md`.
    -   Perform a single commit for the entire phase with a message like `feat(phase): Complete <Phase Name>`.

7.  **Attach Consolidated Task Summary using Git Notes:**
    -   **Step 7.1: Draft Note Content:** Create a detailed summary for *all* tasks completed in this phase, including verification results.
    -   **Step 7.2: Attach Note:** Use `git notes add -m "<summary>" <checkpoint_commit_hash>`.

8.  **Get and Record Phase Checkpoint SHA:**
    -   Obtain the hash of the checkpoint commit and update the phase heading in `plan.md` with `[checkpoint: <sha>]`.

9. **Commit Plan Update:**
    - Stage `plan.md` and commit with `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

10. **Announce Completion:** Inform the user that the phase is complete and the checkpoint has been created.

## Quality Gates

Before marking any task complete, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80%)
- [ ] Code follows project's code style guidelines
- [ ] All public functions/methods are documented
- [ ] Type safety is enforced (Pydantic models, type hints)
- [ ] No linting or static analysis errors
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced

## Development Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm install
```

### Daily Development
```bash
# Start FastAPI server
uvicorn main:app --reload

# Run Backend Tests
pytest

# Run E2E Tests
npx playwright test
```

### Before Committing
```bash
# Run all checks
pytest && npx playwright test
```

## Testing Requirements

### Unit Testing
- Every module must have corresponding tests in `tests/`.
- Use `pytest` fixtures for database and app setup.
- Mock external APIs (Open Food Facts, OpenAI).

### Integration Testing
- Test complete API flows using `httpx`.
- Verify database state after operations.

### E2E Testing
- Use Playwright to test critical user journeys (Creating Plans, Adding Foods).

## Commit Guidelines

### Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Maintenance tasks

## Definition of Done

A task is complete when:

1. All code implemented to specification
2. Unit tests written and passing
3. Code coverage meets project requirements
4. Documentation complete (if applicable)
5. Code passes all configured linting and static analysis checks
6. Implementation notes recorded for the phase summary
7. Phase changes committed and summarized with Git Notes