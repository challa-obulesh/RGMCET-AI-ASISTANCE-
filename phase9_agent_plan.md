# Phase 9 Agent Plan: Advanced AI Agent + Tool Calling + Multi-Step Workflows

## 1. Existing Architecture & Flow
- **Current Flow**: The system currently uses `detect_web_intent` (a regex/keyword-based parser combined with a basic LLM classifier) to determine user intent. Then, inside `services.answer_chat`, a giant python `if/elif` block hardcodes the logic for every possible intent.
- **RAG System**: Already implemented in Phase 7 (`knowledge.py` and `vector_store.py`).
- **Services**: Backend services exist for creating, rescheduling, cancelling, and fetching professor availability. Google Calendar integration sits within the appointment service logic.
- **Context/Memory**: Currently managed via a hardcoded `_conversation_contexts` dictionary storing explicit fields (professor, date, time).

## 2. What Phase 9 Will Add
We will replace the hardcoded `if/elif` state machine with a dynamic, LLM-driven orchestration loop. The LLM will act as a true **Agent**, deciding when to use tools, how to combine their results, and when to ask the user for missing information.

### Orchestration Pipeline:
1. **Context Resolution & Intent**: LLM reviews the conversation history and the latest user message.
2. **Tool Selection (Agent Decision)**: LLM decides whether it needs to query the backend (via tools) or if it can formulate a final answer or ask a clarifying question.
3. **Tool Execution**: The backend executes the requested tool (using authenticated user scope) and returns the structured result.
4. **Result Validation / Loop**: The LLM reviews the tool result. It may call another tool (e.g. search professor -> check availability) or generate a final grounded response.

### Tool Registry
We will introduce `app/web_mvp/agent/tools.py` (or similar) to register the following capabilities:
- **TOOL 1**: `search_knowledge` - Queries RGMCET facts using existing RAG.
- **TOOL 2**: `search_professor` - Looks up professor details.
- **TOOL 3**: `check_availability` - Checks schedule service for a professor on a specific date.
- **TOOL 4**: `search_appointments` - Fetches user's own appointments.
- **TOOL 5**: `create_appointment` - Drafts an appointment (requires explicit confirmation).
- **TOOL 6**: `reschedule_appointment` - Updates appointment time.
- **TOOL 7**: `cancel_appointment` - Cancels an appointment.
- **TOOL 8**: Google Calendar sync is intrinsically handled by the appointment service when tools 5, 6, or 7 are executed.

### Workflow States
The agent will track a `workflow_state` (e.g., `IDLE`, `COLLECTING_INFORMATION`, `AWAITING_CONFIRMATION`, `COMPLETED`) in its context to safely pause and ask the user for confirmation before executing mutating tools (create, reschedule, cancel).

## 3. Files That Will Change
- **`app/web_mvp/llm.py`**: Upgrade to support JSON tool-calling loops or a structured schema output.
- **`app/web_mvp/services.py`**: Refactor `answer_chat` to delegate to the new agent orchestrator instead of hardcoded if/elif blocks. Keep backend actions (like `create_appointment`) authoritative and strictly authorized.
- **`app/web_mvp/agent.py`** (NEW): The core agent loop and context manager.
- **`app/web_mvp/tools.py`** (NEW): The tool registry and execution definitions.
- **`app/web_mvp/api/appointments.py`**: Minor updates to pass full user context into the agent.
- **`tests/test_agent.py`** (NEW/UPDATED): Specific tests for tool validation, multi-step workflow logic, and hallucination prevention.

## 4. Tests That Will Be Added
- **Tool Registry Tests**: Validate that each tool correctly parses input and returns structured success/error JSON.
- **Orchestration Tests**: Verify the LLM selects multiple tools in sequence (e.g., `search_professor` -> `check_availability`).
- **Confirmation Tests**: Ensure the LLM does not execute mutating tools without `workflow_state == AWAITING_CONFIRMATION` or similar guards.
- **Authorization Tests**: Ensure the agent passes the authenticated `student_id` to tools, and that tools enforce isolation (e.g. `search_appointments` only returns the student's own records).

## 5. Browser Scenarios (R01 - R25)
We will leverage `scripts/run_portable_verification.py` (updated to `headless=False`) to perform the full UI end-to-end verification. It will validate the conversational flow (missing info, scheduling, rescheduling, cancellation, multilingual) against the new agent architecture.

## 6. Rollback Risks & Mitigations
- **Risk**: The LLM hallucinates tool inputs or bypasses authorization.
  - **Mitigation**: Tools are just wrappers around existing backend services. The tools will enforce authorization using the `student_id` passed from the API layer, ignoring any ID the LLM might try to inject.
- **Risk**: The LLM gets stuck in an infinite tool-calling loop.
  - **Mitigation**: The agent loop will have a strict `MAX_STEPS` (e.g., 3 or 4) per user message.
- **Risk**: Existing Phase 1-8 logic breaks.
  - **Mitigation**: We will run the entire 144+ test suite continuously. Deterministic fallback will be maintained if the LLM completely fails.

## 7. Acceptance Criteria
1. LLM orchestrates tool selection and combinations dynamically.
2. The user can request multi-step workflows (e.g. "Who is the HOD and when can I meet him?").
3. Tool inputs and outputs are strictly typed/structured.
4. Backend completely guards all database mutations; LLM only drafts requests.
5. All 144+ legacy backend tests pass. New agent tests pass.
6. Visible Google Chrome test (R01-R25) passes end-to-end.
