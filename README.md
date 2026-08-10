# Assessments — Digital Assessment & Declaration Workflow for Frappe LMS

A Frappe app that adds a multi-stage, timed digital assessment workflow to LMS: a Digital Declaration
(with a captured signature) followed by any number of configurable stages (MCQ/quiz, review, etc.), with
per-stage timers, auto-submit, and refresh-safe progress recovery — built on top of LMS's own Course,
Enrollment, Quiz and Question doctypes rather than reinventing them.

---

## Time Tracking (Mandatory)

| | |
|---|---|
| **Start Time** | 2026-08-10, 1:15 PM IST |
| **End Time** | 2026-08-10, 3:45 PM IST |
| **Total Duration** | ~2 hours 30 minutes |

---

## Setup Instructions

**Prerequisite:** an existing bench with `frappe` and `lms` (tested against LMS v2.61.0) already installed on
your site.

1. Get and install the backend app:

   ```bash
   cd $PATH_TO_YOUR_BENCH
   bench get-app assessments $URL_OF_THIS_REPO --branch main
   bench --site $SITE install-app assessments
   bench --site $SITE migrate
   ```

   `migrate` also syncs the doctype-level role permissions (System Manager / Course Creator / Moderator /
   Batch Evaluator / LMS Student) that ship in each doctype's JSON — no manual permission setup needed.

2. Wire up the frontend — see [`frontend-integration/README.md`](frontend-integration/README.md) for the
   two-step copy + patch process, then:

   ```bash
   cd apps/lms/frontend
   yarn build
   ```

3. (Optional) seed a working demo — a course, a student, a quiz, and a 3-stage assessment
   (Declaration → MCQ Assessment → Final Review):

   ```bash
   bench --site $SITE execute assessments.setup_test_data.run
   ```

   You can also dry-run the entire student flow end-to-end from the console:

   ```bash
   bench --site $SITE execute assessments.dev_test_flow.run
   ```

---

## Architecture Overview

### Doctypes (`assessments/assessments/doctype/`)

- **Assessment** — `title`, `course` (Link to `LMS Course`), `assessment_type`, `is_published`,
  `instructions`, and a child table `stages` (`Assessment Stage`). An assessment belongs to exactly one
  course; only students enrolled in that course (via `LMS Enrollment`) can access it.
- **Assessment Stage** (child table) — `stage_type` (`Declaration` / `Quiz` / `Review`), `title`, `quiz`
  (Link to `LMS Quiz`, used when `stage_type = Quiz`), `duration_minutes`. Stage order is just the table's
  row order — draggable in the desk form, no separate sequencing field needed.
- **Assessment Attempt** — one per (assessment, student). Tracks `status`
  (Not Started / In Progress / Submitted), `current_stage_idx`, `started_at` / `submitted_at`, the
  declaration fields (`candidate_name`, `declaration_datetime`, `signature`, `declaration_accepted`), and a
  child table `stage_progress` (`Assessment Stage Progress`) recording each stage's status/timestamps and,
  for quiz stages, a link to the resulting `LMS Quiz Submission`.
- **Assessment Answer** — one row per (attempt, stage, question), autosaved as the student answers; kept
  separate from the attempt so answers can be saved incrementally without re-saving the whole attempt
  document on every keystroke.

### Backend API (`assessments/assessments/api.py`)

- `get_dashboard_assessments` — assessments for the student's enrolled, published courses, with status and
  live stage-deadline for in-progress attempts (dashboard's "Time Remaining").
- `start_assessment` — enrollment check, then creates the attempt (or returns the existing one — this is
  what makes refresh/resume work).
- `submit_declaration` — validates the current stage really is a Declaration stage, then records name,
  signature and acceptance and advances to the next stage.
- `save_answer` — autosaves one answer at a time for the current stage only.
- `submit_stage` — grades a Quiz stage (via LMS's own `verify_answer` / `check_input_answers`, writing an
  `LMS Quiz Submission`) and advances to the next stage, or marks the attempt `Submitted` if it was the last
  one.
- `get_attempt_state` — the single call the exam-taking page polls on load/reload: it first checks whether
  the current stage's timer has expired (server clock, not the client's) and auto-submits/advances if so,
  then returns the attempt, saved answers, the live deadline, and the current stage's questions. This is
  what makes "resume after refresh" and "auto-submit on timeout even if the student never comes back" both
  work off one code path.

Every one of these is a `frappe.whitelist()`-decorated function that re-checks `attempt.member == frappe.session.user`
and the attempt's current stage/status before doing anything — the doctype-level permissions (below) are a
second, independent layer, not the only one.

### Frontend (`frontend-integration/lms/frontend/src/`, lives inside `apps/lms/frontend`)

- `pages/Assessments/AssessmentDashboard.vue` — the student's assessment list (title, type, status, time
  remaining, resume/start/view-result action).
- `pages/Assessments/AssessmentTaking.vue` — starts/resumes an attempt and renders whichever stage
  component matches the current stage type.
- `components/Assessments/DeclarationStage.vue` — candidate name, live date/time, `SignaturePad.vue`
  (canvas-based signature capture), acceptance checkbox.
- `components/Assessments/QuizStage.vue` — renders MCQ/short-answer questions, autosaves answers
  (debounced) via `save_answer`.
- `components/Assessments/ReviewSummary.vue` — final review before submission *and* the read-only summary
  shown afterward (score, candidate signature, submission time, final status) — one component, two modes.
- `components/Assessments/StageStepper.vue` — the stage progress indicator.
- `components/AssessmentTimer.vue` — countdown + progress bar driven by the server-provided deadline;
  emits `expired`, which triggers a state reload (so the server-side expiry check is what actually acts).
- Wired into the LMS router at `/assessments` and `/assessments/:assessmentID`, and into LMS's sidebar
  (`utils/index.js`) as an "Assessments" nav item visible to any logged-in user.

---

## Assumptions

- One `Assessment` maps to one `LMS Course`; enrollment in that course (`LMS Enrollment`) is the sole access
  gate — no separate "Exam Enrollment" concept was introduced.
- A `Quiz` stage reuses one existing `LMS Quiz` (built with LMS's own quiz builder) rather than a
  parallel question bank; short-answer/MCQ question types are exactly LMS's own (`Choices`, `User Input`,
  `Open Ended`).
- `Open Ended` questions have no stored correct answer in LMS, so they're auto-scored 0 pending manual
  grading — this mirrors how LMS itself treats them elsewhere, not a gap introduced here.
- Timer authority is the server: `stage_progress.started_at` + the stage's `duration_minutes` (falling back
  to the linked quiz's own `duration` if the stage doesn't override it). A page reload recomputes remaining
  seconds from that deadline rather than resetting any client-held timer.
- Sections/stages are strictly sequential and one-way — once `submit_stage`/`submit_declaration` advances
  `current_stage_idx`, the API refuses to accept further writes for a lower stage index.

## Design Decisions

- **Reuse over reinvention**: `LMS Course`, `LMS Enrollment`, `LMS Quiz`, `LMS Question`, and
  `LMS Quiz Submission` are used as-is. Only what LMS doesn't already have — multi-stage sequencing, the
  declaration/signature step, and per-stage timing — is new. This was the main reason a second, from-scratch
  exam app (also evaluated, see note below) was set aside in favor of this design.
- **No custom "assessment builder" UI**: creating an `Assessment` and its `Assessment Stage` rows is done
  through the standard Frappe Desk form (System Manager / Course Creator / Moderator / Batch Evaluator
  roles). Frappe's generic desk form already gives drag-to-reorder table rows, link-field validation, and
  permissions for free — building a bespoke admin UI for this would have been pure duplication of that,
  not better UX. The *student-facing* pages are the ones that needed custom frontend, and that's where the
  Vue work went.
- **Doctype-level permissions, not blanket `ignore_permissions`**: each doctype's JSON grants `LMS Student`
  row-scoped access (`if_owner=1` read/write/create on `Assessment Attempt` and `Assessment Answer`, `member`
  is only ever set to `frappe.session.user`) so Frappe's own permission engine is a real second line of
  defense, not just the manual checks inside the whitelisted API functions. `Moderator`/`Batch Evaluator`
  (LMS's existing grading roles) get read access to attempts/answers for review, matching how those roles
  are already used elsewhere in LMS.
- **Read-only after submission is enforced server-side, not just hidden in the UI**: `Assessment Attempt`
  and `Assessment Answer` controllers `validate()` and reject any write once the attempt's status is
  `Submitted` — even a direct `frappe.client.save` call against a student's own (permission-wise writable)
  attempt is blocked, not just the custom API.
- **Answers are a separate doctype, not a child table of the attempt**: this lets `save_answer` autosave a
  single answer without re-writing (and re-validating) the whole attempt document on every keystroke/change.
- **Server clock is the only clock that matters**: the frontend timer is purely a display; every stage
  transition and the auto-submit-on-expiry check is re-derived from `stage_progress.started_at` on the
  server, so a fast/slow/paused client clock can't extend or shorten anyone's time.

## Limitations

- No background job forcibly closes an attempt the instant its timer expires — expiry is checked (against
  the real server deadline, so it can't be gamed) whenever the student's dashboard or attempt state is next
  read. An attempt whose student never returns stays `In Progress` in the database until then, though its
  timer has already visibly expired and no further answers can be saved once the deadline passes.
- No dedicated grading screen for `Open Ended` (long-form) answers — they're stored in `Assessment Answer`
  and visible to Moderators/Batch Evaluators via the desk list view, but there's no purpose-built review UI
  to read them alongside the question and enter a manual mark.
- The admin side (creating assessments/stages, enrolling via course, reviewing attempts) is desk-only by
  design (see Design Decisions) — there is no portal-side admin UI.
- Single question type per stage's UI treatment: `Choices` questions render as radio/checkbox groups and
  everything else as free text — matches LMS's own three quiz question types, but wouldn't extend to a
  fourth question type without frontend changes.

---

## AI Usage

**Tool used:** Claude Code (Anthropic), across two sessions on the same machine/bench.

**What AI generated:**
- The backend: all five doctypes, `api.py` (stage-sequencing, timer/auto-submit logic, LMS Quiz grading
  integration, dashboard aggregation).
- The frontend: the dashboard, exam-taking shell, declaration/signature/quiz/review-summary components, the
  canvas-based signature pad, and the countdown timer component.
- The doctype-level role permissions (`Assessment`, `Assessment Attempt`, `Assessment Answer`), ported from
  a working configuration that had been set up live via the Desk Role Permission Manager into each
  doctype's JSON so it ships with the app instead of only existing in one site's database.
- The `validate()` read-only-after-submission guards on `Assessment Attempt`/`Assessment Answer`.
- The dashboard's "Time Remaining" column and the sidebar/router integration.

**What was found and fixed by AI, not by manual review:** the permission model looked complete on disk but
had only ever been granted at the database level (via Custom DocPerm records added through the desk UI in
the earlier session) — a fresh install from this repo would have shipped with only System Manager access
and silently broken for every student. This was caught by actually running the student flow end-to-end
(`bench execute assessments.dev_test_flow.run`) as the real student user rather than trusting that the
doctype JSON matched what had been tested live, then confirmed by inspecting `Custom DocPerm` directly and
diffing it against the JSON.

**What was modified manually:** none of this code was hand-written outside of Claude Code; changes were
reviewed and directed conversationally (e.g. correcting an accidental `if_owner=1` on the System Manager
permission row, found by inspection, which would have wrongly scoped admins to only their own attempts —
fixed before it was committed).

*(A second, independent implementation — a from-scratch multi-section exam app with its own MCQ/SAQ
doctypes instead of reusing LMS's Quiz — was also produced during exploration and set aside in favor of
this one; see Design Decisions above for why.)*
