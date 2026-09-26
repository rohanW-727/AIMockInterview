# AI Mock Interview

A real-time mock interview application that combines conversational AI with structured interview stages, session-isolated memory, and a React dashboard.

LiveKit Agents handles voice and text interaction, while LangGraph controls stage progression through explicit application logic. Turn limits, timeouts, and inactivity handling keep the interview moving.

## Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Agent runtime | LiveKit Agents | Real-time interaction, streaming responses, and session events |
| Workflow control | LangGraph | Interview state management and deterministic stage transitions |
| Backend | FastAPI (Python) or Node.js with Express | API endpoints and UI updates |
| Frontend | React.js and CSS | Interview interface and diagnostic dashboard |
| Storage — optional upgrade | PostgreSQL | Persistent memory keyed by session and stage |

Optional features include a lightweight authentication gate and WebSocket-based UI updates.


## Interview Workflow

The interview follows three stages:

**INTRO → EXPERIENCE → DONE**

- **INTRO:** Collect the participant’s role, skills, and general background.
- **EXPERIENCE:** Explore relevant experience using a sanitized introduction summary.
- **DONE:** End the interview session.

LiveKit manages the conversation and session events. LangGraph enforces stage transitions and prevents conflicting stage activity.

## Stage Transition Logic

A stage transitions when one of the following conditions is met and the agent is no longer speaking or streaming:

- **Completion:** The stage’s required information has been collected.
- **Turn limit:** `turn_count >= max_turns`
- **Timeout:** `elapsed_stage_time >= stage_timeout`

Inactivity triggers a nudge after the idle threshold. If inactivity continues until the stage timeout, the interview advances.

### Transition Safeguards

- Only one stage is active at a time.
- Transitions are blocked while the agent is speaking or streaming.
- Transition requests are debounced so each stage advances only once.

## Edge Case Handling

### Inactive Participants

The application tracks `last_user_activity_time`. When the idle threshold is exceeded, the agent delivers a supportive nudge. When the stage timeout is reached, the application advances once the agent finishes speaking.

### Off-Topic Responses

Off-topic detection uses a simple heuristic or an LLM-based boolean classifier.

The first off-topic response triggers a redirect and a restatement of the question. Repeated occurrences are tracked, while turn and time limits prevent the conversation from looping indefinitely.

## Memory Architecture

Memory is separated into session-level and stage-level state.

### Session Memory

Keyed by `session_id`, session memory stores:

- Minimal session metadata
- Sanitized conversation summaries
- Metrics for observability

Each session’s memory is isolated to prevent information from carrying over into unrelated interviews.

### Stage Memory

Keyed by `(session_id, stage)`, each stage maintains its own:

- Turn count
- Timers
- Transition reasons
- Stage-specific summary

Raw transcripts are not shared between stages. INTRO produces `handoff_summary_safe`, and EXPERIENCE receives only that sanitized summary and allowlisted fields.

## Data Handling

Raw transcripts are not persisted by default. Persistence is limited to:

- Allowlisted information, such as role, top skills, and general background
- Sanitized summaries
- Metrics, including turn counts, durations, and transition reasons

Best-effort redaction is applied before information is persisted or passed between stages.

| Information | Replacement |
|---|---|
| Email addresses | `[REDACTED_EMAIL]` |
| Phone numbers | `[REDACTED_PHONE]` |
| Addresses and identifying numbers | `[REDACTED]` |

Names can optionally be limited to a first name or redacted entirely.

## Dashboard

The React dashboard displays the conversation alongside the state and timing information that controls interview progression.

### Interview Interface

- Current stage badge: INTRO, EXPERIENCE, or DONE
- Transcript viewer, without requiring transcript persistence
- Start and stop session controls

### Timers

- Elapsed stage time
- Time since the participant’s last activity
- Time remaining before the stage timeout

### Diagnostics

- Current turn count and maximum turns
- Last transition reason
- Agent speaking status

An optional debug toggle exposes a manual stage-transition button for testing.
