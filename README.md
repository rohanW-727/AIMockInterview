# AI Mock Interview Project Documentation

# Tech stack
# Backend:
1. LiveKit Agents (core “agent runtime” + real-time interaction layer)

2. LangGraph (complementary workflow/state machine for deterministic stage control)

3. FastAPI (Python) or Node/Express (API + optional WS for UI updates)

4. If you use WebSocket in the frontend, hardcode: ws://127.0.0.1:8000/ws
# Frontend
1. React.js + CSS (simple dashboard UI to make stage logic + fallbacks visible)
2. Optional: lightweight auth gate (dummy username/password)
3. Storage (for “persistent memory”)
4. Optional upgrade: Postgres keyed by session_id + stage (Pinecone not needed unless you’re doing semantic search/RAG)





# Brief workflow logic
# Stages (finite state machine)
INTRO → EXPERIENCE → DONE
What runs where:
LiveKit: handles user interaction (voice/text), streaming responses, session events.

LangGraph: enforces deterministic stage transitions + “no conflict” rules.

Transition rules (hard-coded in logic, not prompt-only)

Each stage transitions when any of the following is true and the agent is not currently speaking/streaming:

Completion criteria met (e.g., intro collected)

Turn limit reached (turn_count >= max_turns)

Time-based fallback (elapsed_stage_time >= stage_timeout)

Idle fallback (time_since_last_user_activity >= idle_timeout) → nudge first; if still idle and stage timeout reached, transition.

Anti-conflict guarantees

Only one stage active at a time.

Block transitions while is_agent_speaking == true (prevents interruptions/overlap).

Debounce transitions so they can only fire once per stage.


# Scenarios & Edge Cases:

1) User takes too long to complete a turn
Track last_user_activity_time
If idle_timeout exceeded: supportive nudge
If stage_timeout exceeded: force stage transition (time-based fallback)
2) User goes off-topic
Detect off-topic (simple heuristic or LLM boolean classifier)
First time: redirect + restate question
Repeated off-topic: count strikes; still obey turn/time limits to avoid loops
If overall stage exceeds time: transition regardless

3) Persistent memory without leakage
You’ll implement two memory layers, both sandboxed and sanitized:
Outer memory: Session-level (very basic)
Keyed by session_id
Stores only minimal session metadata + sanitized transcript summary (not raw)
Purpose: prevent cross-session bleed, enable basic observability
Inner memory: Stage-level (INTRO/EXPERIENCE sandboxes)
Keyed by (session_id, stage)
Each stage stores only its own state:
turn_count, timers, transition reasons, stage-specific summary
No raw transcript is shared across stages
Only a sanitized handoff summary is passed from INTRO → EXPERIENCE

# Sanitization/anonymity rules (applies before persisting anything)
Data minimization
Default: do not persist raw transcripts

Persist only:
allowlisted fields (e.g., role, top skills, general background)
sanitized summaries
metrics (turns, durations, transition reason)
PII redaction (best-effort)
Emails → [REDACTED_EMAIL]
Phone numbers → [REDACTED_PHONE]
Addresses/IDs → [REDACTED]

Optionally: keep only first name or redact names entirely
Stage handoff
INTRO produces handoff_summary_safe
EXPERIENCE receives only handoff_summary_safe + allowlisted fields
EXPERIENCE never reads INTRO raw content

# Demo UI features (React)
Core panels:
Stage badge (INTRO / EXPERIENCE / DONE)
Transcript viewer (what user sees; can be non-persisted)
Timers
elapsed stage time
idle time
“next fallback” (time remaining until stage_timeout)
Diagnostics
turn count (e.g., 2/3)
last transition reason (criteria_met | timeout | turn_limit | idle_timeout)
agent speaking status (true/false)
Controls:
Start / Stop session
Optional debug toggle (force transition button hidden behind toggle)

