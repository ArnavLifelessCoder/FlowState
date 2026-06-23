# FlowState

> **Real-Time Emotionally Adaptive AI Platform** — a full-stack system that monitors cognitive load, attention, and stress in real time, then adapts digital experiences accordingly.

FlowState consists of a **FastAPI backend** (Python) and a **Next.js 16 dashboard** (TypeScript) that together provide behavior tracking, emotion inference, adaptive UI recommendations, notification gating, team analytics, and GDPR-compliant privacy controls.

## What is implemented

### Backend (FastAPI + SQLite)
- Behavior event ingestion with rolling window feature extraction.
- Heuristic metrics for cognitive load, frustration, attention, and recommended adaptation.
- Q-learning adaptation policy with stored decision history and feedback.
- Analytics endpoints for history and aggregate insights.
- WebSocket streams for realtime emotion + adaptation config updates.
- **JWT Auth** — user registration, login, access/refresh tokens, bcrypt password hashing.
- **Behavioral Memory** — long-term per-user profiling with pattern detection and proactive suggestions.
- **Session Management** — user-session lifecycle (create, end, list) with auto-triggered daily summaries.
- **Notification Gating** — cognitive-state-aware notification filtering (deliver/queue/suppress).
- **Enterprise Team Analytics** — anonymized aggregate metrics, burnout risk detection, stress hotspots.
- **GDPR Privacy** — full data export, cascading deletion, and sensing pause/resume controls.
- **Schema Migrations** — versioned migration tracking for forward-compatible DB evolution.
- **Multimodal Emotion Pipeline** — orchestrates vision (camera), audio (microphone), and behavior modalities with weighted late fusion.
- **Vision Service** — decodes JPEG frames and derives **real** image features (brightness, contrast, Laplacian sharpness, brightness centroid) into fatigue, gaze direction, and face presence. An optional ONNX facial-emotion model (config-gated) layers a trained emotion label on top. Falls back to a deterministic heuristic only when the scientific stack or a decodable frame is unavailable.
- **Audio Service** — decodes 16-bit PCM WAV chunks and computes **real** DSP features (RMS loudness, zero-crossing rate, energy-envelope variability, onset rate) into vocal stress, emotion, speaking tempo, and pitch variance. Falls back to a deterministic heuristic only when a chunk is not parseable PCM WAV.
- **Fusion Service** — combines vision, audio, and behavior signals with configurable weights and automatic weight redistribution for missing modalities.
- **Emotion Smoother** — temporal stabilization of the per-frame fusion stream: exponential moving average on continuous metrics, hysteresis on the discrete emotion label, plus derived stress `trend` (rising/falling/steady) and a `stability` score. Eliminates the per-frame flicker that made the raw mood signal read as random, and keeps the recommended adaptation aligned with the smoothed metrics.
- **Emotion Snapshots** — persistent storage for fused multimodal emotion states with paginated history.
- **Psychometric Assessments** — 5 validated instruments (NASA-TLX, PSS-4, Flow Short Scale, Burnout Micro, Mood Check) with scoring, trend analysis, and composite wellbeing snapshots.
- **Sensor Calibration** — compares real-time sensor estimates with self-reported ground truth to compute calibration deltas.

### Frontend (Next.js 16 + TypeScript)
- **Auth pages** — register/login with JWT token management and auto-refresh.
- **Dashboard** — real-time circular gauges for cognitive load, frustration, and attention.
- **Measurement guide** — explains what each metric estimates, which behavior signals feed it, and what the score means.
- **Behavior tracking** — automatic keypress and mouse event capture sent to backend.
- **Metric cards** — live-updating statistics with gradient progress bars.
- **Adaptation display** — shows current recommended adaptation action.
- **Adaptive UI shell** — applies backend adaptation config as sparse/normal/dense, slow/normal/fast, and minimal/normal/advanced interface states.
- **Stress timeline** — session-level SVG chart for frustration, cognitive load, attention, summary metrics, and intervention playback.
- **Attention heatmap overlay** — session-scoped pointer/click concentration map with primary zone, confidence, and latest-position stats.
- **Notification tester** — interactive form to test notification gating decisions.
- **Team analytics** — create teams and view anonymized aggregate insights.
- **Session history** — table with status badges, timestamps, and platform info.
- **Activity feed** — real-time log of user actions.
- **Design system** — dark glassmorphism theme with Inter font, gradient accents, and micro-animations.
- **Camera Capture** — webcam access with frame capture every 500ms, sent as base64 JPEG for vision inference.
- **Audio Capture** — microphone access via WebAudio, capturing real 16-bit PCM and encoding 2s WAV chunks client-side so the backend DSP pipeline analyzes the actual signal (not an opaque compressed blob).
- **Emotion Radar** — SVG pentagon chart visualizing stress, cognitive load, distraction, burnout risk, and uncertainty in real-time.
- **Modality Controls** — toggle buttons for enabling/disabling vision (camera), audio (mic), and behavior (keyboard/mouse) sensing.
- **Floating Mood Indicator** — glassmorphism floating indicator showing the smoothed emotion label, confidence, stress trend (directional arrow), and a signal-stability readout (stable/settling/volatile), color-coded by stress tone. Driven by the backend Emotion Smoother so it stays calm instead of flickering.
- **Line-icon design system** — a single stroke-based SVG icon set replaces emoji throughout the UI for consistent cross-platform rendering.
- **Assessment Page** — full interactive assessment-taking flow with question stepper, animated scale buttons, result display with score circle, subscale breakdowns, assessment history, and composite wellbeing dashboard.
- **Wellbeing Calibration** — shows delta between sensor estimates and self-report to validate sensing accuracy over time.

## Architecture flow

Behavior events (keypress, mouse, focus) ->
BehaviorService computes features ->
BehaviorSnapshot persisted in SQLite ->
RealtimeHub publishes updates ->
Adaptation policy returns UI configuration ->
Analytics reads history and aggregates insights ->
MemoryService builds long-term behavioral profiles and generates proactive suggestions

Multimodal pipeline (Phase 2):
Camera frame / Audio chunk -> VisionService / AudioService inference ->
FusionService combines with BehaviorSnapshot ->
EmotionState temporally smoothed (EmotionSmoother) ->
EmotionState persisted in emotion_snapshots table ->
Frontend displays on EmotionRadar + floating Mood Indicator

Frontend behavior tracking samples mouse movement before sending it to the backend, records bounded client-side attention points for the heatmap, and polls current snapshots without injecting synthetic behavior into the model.

The dashboard also reads `/adaptation/config/{session_id}` and applies the returned UI config through root data attributes, so high-load states can simplify the interface while low-load states can expose denser analytics.

## API overview

Base path: /api/v1

Auth
- POST /auth/register: register a new user (bcrypt hashed password).
- POST /auth/login: authenticate and receive JWT access + refresh tokens.
- POST /auth/refresh: exchange refresh token for new token pair.
- GET /auth/me: get current user info from JWT access token.

Session
- POST /session: create a new session for a user (returns session_id).
- GET /session/{session_id}: get session details.
- POST /session/{session_id}/end: end a session (auto-generates daily summary).
- GET /session/user/{user_id}: list sessions for a user (supports active_only filter).

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

Behavioral Memory
- GET /memory/profile/{user_id}: fetch behavioral profile, proactive suggestions, and daily trend.
- POST /memory/profile/{user_id}/build: trigger profile rebuild from session history (auto-discovers user sessions).
- POST /memory/summary: record a daily session summary from snapshot data.
- GET /memory/suggestions/{user_id}: get proactive suggestions only.
- DELETE /memory/profile/{user_id}: delete all behavioral memory for a user (GDPR).

Notifications
- POST /notifications/evaluate: evaluate a notification against cognitive state (returns deliver/queue/suppress).
- GET /notifications/queue/{session_id}: get queued notifications for a session.
- POST /notifications/queue/{session_id}/flush: deliver all queued notifications.
- GET /notifications/stats/{session_id}: get per-session gating statistics.
- GET /notifications/policy: get current gating policy thresholds.
- PUT /notifications/policy: update gating policy thresholds.

Privacy & GDPR
- GET /privacy/export/{user_id}: export all user data as JSON (GDPR data portability).
- DELETE /privacy/data/{user_id}: cascade-delete all user data (GDPR right to erasure).
- GET /privacy/sensing/{session_id}: get current sensing modality state.
- PUT /privacy/sensing: update sensing modality toggles (pause/resume vision, audio, behavior).

Team Analytics
- POST /teams: create a team with user_ids.
- GET /teams: list all teams.
- GET /teams/{team_id}: get anonymized aggregate analytics for a team.
- DELETE /teams/{team_id}: delete a team.

Emotion (Multimodal)
- POST /emotion/infer-frame: process a camera frame (base64 JPEG) and return fused EmotionState.
- POST /emotion/infer-audio: process an audio chunk (base64 WAV) and return fused EmotionState.
- GET /emotion/current/{session_id}: get the latest fused emotion state for a session.
- GET /emotion/history/{session_id}: get paginated multimodal emotion history.

Assessments (Psychometric)
- GET /assessments/instruments: list all available psychometric instruments.
- GET /assessments/instruments/{instrument_type}: get full instrument definition with all questions.
- POST /assessments/submit: submit assessment responses and receive scored result with severity classification.
- GET /assessments/history/{user_id}: get assessment history, optionally filtered by instrument.
- GET /assessments/trend/{user_id}/{instrument_type}: get trend analysis for a specific instrument.
- GET /assessments/wellbeing/{user_id}: get composite wellbeing snapshot combining sensors + self-report.

Other
- GET /health: service status and SQLite connectivity.
- WS /ws/emotion/{session_id}?token=...: realtime emotion snapshot stream.
- WS /ws/adaptation/{session_id}?token=...: realtime adaptation config stream.

## Behavioral Memory

The behavioral memory system learns long-term patterns from accumulated session data.

### What it detects

- **Peak focus hours**: hours of the day where cognitive load is consistently lowest.
- **Stress triggers**: temporal and behavioral patterns correlated with high frustration (evening sessions, high task switching, high error rate).
- **Preferred pace**: whether the user tends toward reduced or increased UI complexity.

### Proactive suggestions

The system generates contextual recommendations based on daily trends:

- **streak_stress**: "You've had elevated stress for N consecutive days."
- **burnout_risk**: "Your cognitive load has been increasing over recent sessions."
- **optimal_time**: "Your peak focus hours are typically around 9:00, 10:00."
- **stress_trigger**: "Evening sessions is a recurring stress trigger."

### Data model

UserBehavioralProfile
- user_id: unique user identifier
- peak_focus_hours: list of integers (0-23)
- stress_triggers: dict mapping trigger name to average frustration score
- preferred_pace: slow | normal | fast
- avg_cognitive_load: float
- total_sessions: int

DailySummary
- user_id, session_id, date (YYYY-MM-DD)
- avg_cognitive_load, avg_frustration, avg_attention
- snapshot_count, peak_hour, dominant_adaptation

## Stress Timeline

The frontend Timeline view uses the existing analytics and adaptation playback APIs to visualize a session over time.

- Chart lines show frustration, cognitive load, and attention from `/analytics/emotion-history/{session_id}`.
- Window summary cards show aggregate metrics from `/analytics/insights/{session_id}`.
- Intervention playback lists policy decisions and feedback from `/adaptation/interventions/{session_id}`.
- The active session's latest snapshot is merged into the chart so live tracking updates without waiting for a manual refresh.

## Attention Heatmap

The dashboard includes an attention heatmap overlay for active sessions.

- Mouse movement is sampled client-side to avoid flooding `/behavior/event`.
- Clicks are rendered with higher intensity than movement points.
- The heatmap keeps only the latest bounded point window in memory, so it does not grow unbounded during long sessions.
- Snapshot polling uses `/behavior/current/{session_id}` instead of fake behavior events, preserving cleaner cognitive-load and task-switch metrics.

## Adaptive UI

The frontend applies the backend adaptation policy to the dashboard layout.

- `minimal` complexity hides secondary panels and advanced visualizations.
- `normal` complexity keeps the standard dashboard.
- `advanced` complexity keeps richer panels visible and supports denser layout settings.
- `sparse`, `normal`, and `dense` density states adjust spacing and card density.
- `slow`, `normal`, and `fast` pace states adjust UI transition timing.

## Measurement Model

The dashboard is explicit that FlowState is estimating behavior patterns, not reading thoughts or making clinical claims.

- Cognitive load uses typing pace, hesitation variance, correction rate, and focus switches.
- Frustration uses correction/error signals combined with current load.
- Attention is treated as steadier interaction with lower load and fewer correction-heavy patterns.
- Research links in the UI point to affective computing, NASA-TLX workload research, mouse trajectory workload work, and keystroke stress-detection studies.

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

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend
```bash
cd apps/backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload    # runs on localhost:8000
```

### Frontend
```bash
cd apps/frontend
npm install
npm run dev                             # runs on localhost:3000
```

### Open the app
Once both are running, open **http://localhost:3000** in your browser and
register an account (the first screen). The frontend talks to the backend via
`apps/frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

If port 8000 is already in use, start the backend on another port
(`uvicorn main:app --port 8001`) and change both URLs above to match, then
restart `npm run dev`. The backend's interactive API docs are at
`http://localhost:8000/docs`.

### Run tests (237 passing)
```bash
cd apps/backend
python -m pytest tests/ -v
```

### Frontend verification
```bash
cd apps/frontend
npm run lint
npm run build
```

Latest local verification:
- `python -m pytest tests/ -q`: 237 passed
- `npm run lint`: passed
- `npm run build`: passed
- Playwright smoke check: auth page, mocked heatmap, measurement guide, and minimal/advanced adaptive UI modes rendered without page errors

The default SQLite database file is created at `./flowstate.db` relative to the backend working directory.

## Configuration

All settings are loaded from environment variables:

- app_name (default: FlowState API)
- environment (default: development)
- log_level (default: INFO)
- api_token (default: change-me)
- jwt_secret (min 32 chars, used for JWT signing)
- enable_auth (default: true)
- database_url (default: sqlite:///./flowstate.db)
- behavior_window_size (default: 500)
- rl_alpha (default: 0.1)
- rl_gamma (default: 0.9)
- rl_epsilon (default: 0.1)
- vision_onnx_model_path (default: "" — set to an exported `.onnx` facial-emotion model to enable the ONNX backend; requires `onnxruntime`)

## Storage

SQLite tables:
- sessions
- behavior_sessions
- behavior_snapshots
- adaptation_feedback
- adaptation_q_values
- adaptation_decisions
- user_behavioral_profiles
- session_daily_summaries
- sensing_states
- emotion_snapshots
- assessments
- users
- schema_migrations

## Session Lifecycle

1. Create a session: POST /api/v1/session with user_id and platform.
2. Ingest behavior events referencing the session_id.
3. End the session: POST /api/v1/session/{session_id}/end.
4. On end, a daily summary is auto-generated for the behavioral memory system.
5. Build profile: POST /api/v1/memory/profile/{user_id}/build auto-discovers all sessions for the user.

## Privacy & GDPR

FlowState treats privacy as non-negotiable:

- **Data Export** (GET /privacy/export/{user_id}): Downloads all user data as structured JSON including sessions, behavior snapshots, adaptation decisions/feedback, behavioral profile, daily summaries, and sensing states.
- **Data Deletion** (DELETE /privacy/data/{user_id}): Cascade-deletes ALL records across every table for a user. Returns per-table deletion counts.
- **Sensing Controls** (PUT /privacy/sensing): Per-session toggle for vision, audio, and behavior sensing modalities. Setting all_paused=true disables all sensing. Auto-detects when all modalities are individually disabled.

## Notification Gating

The notification gating system controls notification delivery based on the user's current cognitive and emotional state.

### Gate Decisions

- **DELIVER**: User is in a calm state, send the notification immediately.
- **QUEUE**: User is in moderate cognitive load or deep focus, hold the notification for later.
- **SUPPRESS**: User is highly stressed or overloaded, drop the notification entirely.

### Priority Levels

- **critical**: Always bypasses the gate (configurable via policy).
- **high**: Delivered even at moderate cognitive load.
- **normal**: Subject to standard gating rules.
- **low**: Queued at moderate cognitive load.

### Configurable Policy

Default thresholds (adjustable via PUT /notifications/policy):
- suppress_cognitive_load: 0.75
- suppress_frustration: 0.70
- queue_cognitive_load: 0.55
- queue_attention: 0.80 (deep focus detection)

## Enterprise Team Analytics

The team analytics system provides aggregate, anonymized insights across groups of users.

### What it provides

- **Anonymized member metrics**: User IDs are hashed (SHA-256) before exposure — no raw identifiers leave the system.
- **Team aggregates**: Average cognitive load, frustration, and attention across all members.
- **Burnout risk count**: Number of team members with sustained high cognitive load + high frustration.
- **Stress hotspots**: Recurring stress triggers aggregated from individual behavioral profiles.
- **Team peak hours**: Most productive hours across all team members.

### Anonymization

All user_ids are one-way hashed before being returned in API responses. The team analytics API never exposes raw user identifiers, ensuring privacy even for team administrators.

## JWT Authentication

FlowState supports two auth modes (both work simultaneously when `enable_auth=true`):

1. **Legacy static token**: Pass `Authorization: Bearer <api_token>` header.
2. **JWT auth** (recommended):
   - Register: `POST /api/v1/auth/register` → creates user with bcrypt-hashed password.
   - Login: `POST /api/v1/auth/login` → returns access token (30m) + refresh token (7d).
   - Refresh: `POST /api/v1/auth/refresh` → exchanges refresh token for new pair.
   - Use: `Authorization: Bearer <access_token>` on all protected endpoints.

Passwords are hashed with bcrypt. JWT tokens are signed with HS256 using the `jwt_secret` config.

## Schema Migrations

The `schema_migrations` table tracks applied migration versions. `BehaviorRepository.get_schema_version()` and `record_migration(version)` provide the foundation for forward-compatible schema evolution.

## Project Structure

```
apps/
├── backend/              # FastAPI + SQLite
│   ├── api/v1/           # REST endpoints (auth, session, behavior, emotion, etc.)
│   ├── core/             # Auth middleware, request logging
│   ├── db/               # BehaviorRepository (SQLite)
│   ├── models/           # Pydantic models (behavior, emotion, memory, etc.)
│   ├── services/         # Business logic
│   │   ├── vision_service.py     # Camera frame → face emotion + gaze
│   │   ├── audio_service.py      # Audio chunk → vocal stress + emotion
│   │   ├── fusion_service.py     # Weighted multimodal late fusion
│   │   └── emotion_pipeline.py   # Orchestrator for all modalities
│   └── tests/            # 237 unit + integration tests
└── frontend/             # Next.js 16 (TypeScript)
    └── src/
        ├── app/          # App Router pages + globals.css
        └── lib/          # API client with JWT management
```

## Notes

The behavioral memory system builds long-term profiles from accumulated snapshot history and generates proactive suggestions based on detected patterns.

### Emotion inference: accuracy and how to upgrade it

The pipeline is layered so the signal is honest at every tier:

- **Signal classifiers (default, always on).** `services/vision_signal.py` and
  `services/audio_signal.py` compute real features from the actual frame/audio
  (image brightness/contrast/Laplacian-sharpness/centroid; audio RMS/ZCR/energy-
  envelope/onsets). These drive fatigue, gaze, vocal stress, tempo, and pitch
  variance — values that genuinely move with the input. The vision signal
  classifier intentionally does **not** invent a facial *emotion* label from raw
  pixels (that requires a trained model); it reports `neutral` with honest,
  exposure-based confidence rather than guessing.
- **ONNX facial-emotion model (optional, real ML).** A trained model supplies
  the facial *emotion* label/confidence, layered over the signal classifier's
  fatigue/gaze (see `services/onnx_emotion.py`). It runs locally via ONNX
  Runtime — no API key, no hosted inference, no per-call cost.

  Quickest setup (FER+, a ready-made `.onnx`, no training/export):
  ```bash
  pip install onnxruntime
  mkdir -p apps/backend/ml_models
  curl -L -o apps/backend/ml_models/emotion-ferplus-8.onnx \
    https://media.githubusercontent.com/media/onnx/models/main/validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx
  # then in apps/backend/.env:
  #   VISION_ONNX_MODEL_PATH=ml_models/emotion-ferplus-8.onnx
  ```
  The classifier auto-detects the model: an 8-class output is treated as FER+
  (FER+ label order, raw 0–255 input); other models default to FER-2013 order
  with `[0,1]`-scaled input. To use a HuggingFace model instead, export it with
  `optimum-cli export onnx --model dima806/facial_emotions_image_detection
  fer_onnx/` and point the path at `fer_onnx/model.onnx` (override labels via the
  `OnnxVisionClassifier(labels=...)` constructor if its order differs). The audio
  path can be extended the same way with a Wav2Vec2-style speech-emotion model.
- **Heuristic fallback.** The legacy content-hash classifier is retained only as
  a last resort when the scientific stack is missing or a chunk can't be decoded,
  so the service never hard-fails.

**Volatility / accuracy.** Per-frame inference is noisy by nature, so the
`EmotionSmoother` applies an EMA low-pass filter to the continuous metrics and
hysteresis to the discrete label, and the recommended adaptation is recomputed
from the smoothed values. `tests/test_signal_classifiers.py` asserts both that
the classifiers respond correctly to controlled inputs (louder/harsher audio →
more stress; blurrier/dimmer frames → more fatigue; bright-region position →
gaze) **and** that the end-to-end smoothed stress stream stays low-jitter
(frame-to-frame change bounded) with rare label switches even under a fully
random frame stream.

The behavior metrics and adaptation policy remain heuristic baselines; the RL
service updates Q-values from feedback rewards stored in SQLite. The fusion
service supports configurable per-modality weights and automatically
redistributes weights when modalities are missing. CORS is pre-configured for
localhost:3000 (Next.js dev server).
