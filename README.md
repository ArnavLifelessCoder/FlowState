# FlowState Backend

FlowState currently contains a FastAPI backend that tracks user behavior events, computes lightweight cognitive metrics, recommends UI adaptations, and exposes analytics and realtime updates. The implementation is intentionally minimal and uses SQLite for storage.

## What is implemented

- Behavior event ingestion with rolling window feature extraction.
- Heuristic metrics for cognitive load, frustration, attention, and a recommended adaptation action.
- Q-learning style adaptation policy with stored decision history and feedback.
- Analytics endpoints for history and aggregate insights.
- WebSocket stream for realtime emotion updates per session.
- Token-based API auth (optional via settings) and request logging.

## Architecture flow

Behavior events (keypress, mouse, focus) ->
BehaviorService computes features ->
BehaviorSnapshot persisted in SQLite ->
RealtimeHub publishes updates ->
Adaptation policy returns UI configuration ->
Analytics reads history and aggregates insights

## API overview

Base path: /api/v1

Behavior
- POST /behavior/event: ingest a behavior event and return the latest snapshot.
- GET /behavior/current/{session_id}: fetch the latest snapshot for a session.

Adaptation
- GET /adaptation/config/{session_id}: return UI config based on current snapshot and policy.
- GET /adaptation/policy/{session_id}: return the selected action and Q-values.
- POST /adaptation/feedback: submit reward feedback for a decision.
- GET /adaptation/feedback/{session_id}: list feedback records.
- GET /adaptation/interventions/{session_id}: timeline of decisions and feedback.

Analytics
- GET /analytics/emotion-history/{session_id}: snapshot history with pagination.
- GET /analytics/insights/{session_id}: aggregate metrics over recent snapshots.

Other
- GET /health: service status and SQLite connectivity.
- WS /ws/emotion/{session_id}?token=...: realtime snapshot stream.

## Auth

When enable_auth is true, all HTTP requests require an Authorization header:

Authorization: Bearer <api_token>

WebSocket connections require a token query parameter.

## Data model quick reference

BehaviorEvent
- type: keypress | mouse_move | scroll | click | focus_change
- timestamp: float seconds
- metadata: event-specific fields (for keypress, Backspace can be indicated)

BehaviorSnapshot (computed)
- typing_wpm
- error_rate
- hesitation_index
- task_switches_per_minute
- cognitive_load
- frustration_score
- attention_level
- recommended_adaptation

Adaptation actions
- reduce_ui_complexity
- enable_focus_mode
- pause_notifications
- slow_content_pacing
- increase_ui_complexity
- enable_power_features
- resume_normal
- suggest_break

## Setup

Prerequisites
- Python 3.x

Install dependencies
- python -m pip install -r apps/backend/requirements.txt

Run the API
- cd apps/backend
- python -m uvicorn main:app --reload

The default SQLite database file is created at ./flowstate.db relative to the backend working directory.

## Configuration

All settings are loaded from environment variables:

- app_name (default: FlowState API)
- environment (default: development)
- log_level (default: INFO)
- api_token (default: change-me)
- enable_auth (default: true)
- database_url (default: sqlite:///./flowstate.db)
- behavior_window_size (default: 500)
- rl_alpha (default: 0.1)
- rl_gamma (default: 0.9)
- rl_epsilon (default: 0.1)

## Storage

SQLite tables:
- behavior_sessions
- behavior_snapshots
- adaptation_feedback
- adaptation_q_values
- adaptation_decisions

## Notes

The behavior metrics and adaptation policy are heuristic and intended as a baseline. The RL service updates Q-values based on feedback rewards stored in SQLite.
