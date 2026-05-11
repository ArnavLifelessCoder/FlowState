# 🧠 FlowState

> **Real-Time Emotionally Adaptive AI Platform**
> A production-grade multimodal AI platform that dynamically adapts digital experiences based on emotional state, cognitive load, and behavioral signals — built entirely on free-tier infrastructure.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com/)

---

## 📋 Table of Contents

- [What Is FlowState](#what-is-flowstate)
- [How It Works](#how-it-works)
- [Zero-Cost Stack](#zero-cost-stack)
- [Project Structure](#project-structure)
- [AI/ML Architecture](#aiml-architecture)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Environment Setup](#environment-setup)
- [Development Roadmap](#development-roadmap)
- [Contributing](#contributing)

---

## What Is FlowState

FlowState is not a chatbot. It is **adaptive human-computer intelligence infrastructure**.

Traditional software is static — it responds only to commands. FlowState continuously reads the human behind the screen and adapts the interface, content pacing, and AI assistant behavior in real time.

### What It Detects

| Signal Category | Signals |
|---|---|
| Visual | Facial expressions, blink rate, eye movement, head pose, microexpressions |
| Audio | Pitch variation, speech speed, vocal stress markers, pauses |
| Behavioral | Typing cadence, cursor movement, typo frequency, hesitation patterns |
| Cognitive | Task switching frequency, interaction latency, workflow abandonment rate |

### What It Estimates

```
frustration · stress · confusion · engagement · burnout · confidence · cognitive overload
```

### What It Adapts

UI complexity, assistant tone, notification density, recommendation pacing, educational difficulty, interaction flow — all updated in real time without user intervention.

---

## How It Works

```
User Inputs (camera, mic, keyboard, mouse)
        ↓
Multimodal Processing Engine
  ├── Vision Model (facial/gaze/fatigue)
  ├── Audio Model (stress/tone/rhythm)
  └── Behavior Model (typing/cursor/latency)
        ↓
Emotion + Cognitive Load Estimation
        ↓
Reinforcement Learning Adaptation Engine
        ↓
UI & Assistant Adaptation Layer
        ↓
Frontend Experience (Next.js)
```

All inference runs in under **100ms**. All UI adaptation fires in under **200ms**.

---

## Zero-Cost Stack

Every component below has a **permanently free tier** sufficient for development and early production.

### Compute & Hosting

| Service | What It Runs | Free Tier |
|---|---|---|
| [Render](https://render.com) | FastAPI backend | 750 hrs/month, 512MB RAM |
| [Vercel](https://vercel.com) | Next.js frontend | Unlimited personal projects |
| [Railway](https://railway.app) | Background workers | $5 credit/month (enough for dev) |
| [Hugging Face Spaces](https://huggingface.co/spaces) | ML model serving | Free CPU/GPU inference (ZeroGPU) |
| [Google Colab](https://colab.research.google.com) | Model training | Free T4 GPU |

### Databases & Storage

| Service | Use Case | Free Tier |
|---|---|---|
| [Supabase](https://supabase.com) | PostgreSQL + Realtime | 500MB DB, 2GB storage |
| [Redis Cloud](https://redis.com/try-free/) | Session state, event queue | 30MB, no expiry |
| [Upstash](https://upstash.com) | Serverless Kafka alternative | 10K messages/day |
| [Cloudflare R2](https://cloudflare.com/r2) | Model artifacts, media | 10GB/month free |

### AI/ML (Free Models)

| Model | Task | Source |
|---|---|---|
| `openai/whisper-base` | Audio emotion features | Hugging Face |
| `facebook/wav2vec2-base` | Speech emotion recognition | Hugging Face |
| `google/mediapipe` | Gaze tracking, face mesh | Google |
| `dima806/facial_emotions_image_detection` | Facial emotion classification | Hugging Face |
| `microsoft/DialoGPT-medium` | Emotionally adaptive assistant | Hugging Face |
| `sentence-transformers/all-MiniLM-L6-v2` | Behavioral embeddings | Hugging Face |

### DevOps (Free)

| Service | Use Case |
|---|---|
| GitHub Actions | CI/CD (2000 min/month free) |
| Docker Hub | Container registry (1 private repo free) |
| Grafana Cloud | Monitoring + alerting (10K metrics free) |
| Sentry | Error tracking (5K events/month free) |

---

## Project Structure

```
flowstate/
│
├── README.md
├── .env.example
├── docker-compose.yml              # Local dev stack
├── docker-compose.prod.yml         # Production overrides
│
├── apps/
│   ├── frontend/                   # Next.js 16 App Router
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Landing / auth gate
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx        # Main adaptive dashboard
│   │   │   │   ├── emotion/
│   │   │   │   │   └── page.tsx    # Real-time emotion view
│   │   │   │   ├── timeline/
│   │   │   │   │   └── page.tsx    # Productivity timeline
│   │   │   │   └── interventions/
│   │   │   │       └── page.tsx    # Intervention playback
│   │   │   └── demo/
│   │   │       └── page.tsx        # Public demo (no auth)
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui base components
│   │   │   ├── emotion/
│   │   │   │   ├── EmotionRadar.tsx
│   │   │   │   ├── StressCurve.tsx
│   │   │   │   ├── AttentionHeatmap.tsx
│   │   │   │   └── CognitiveBadge.tsx
│   │   │   ├── adaptive/
│   │   │   │   ├── AdaptiveShell.tsx       # Root adaptive wrapper
│   │   │   │   ├── UIComplexityManager.tsx
│   │   │   │   └── NotificationGate.tsx
│   │   │   └── assistant/
│   │   │       ├── AssistantPanel.tsx
│   │   │       └── EmotionalToneAdapter.tsx
│   │   ├── hooks/
│   │   │   ├── useEmotionStream.ts         # WebSocket emotion feed
│   │   │   ├── useCameraCapture.ts         # Camera frame capture
│   │   │   ├── useMicCapture.ts            # Audio stream capture
│   │   │   ├── useBehaviorTracker.ts       # Keyboard/cursor signals
│   │   │   └── useAdaptiveUI.ts            # UI state from emotion
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── websocket.ts
│   │   │   └── emotion-utils.ts
│   │   ├── stores/
│   │   │   ├── emotionStore.ts             # Zustand emotion state
│   │   │   ├── adaptiveStore.ts            # UI adaptation state
│   │   │   └── sessionStore.ts             # User session
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   └── backend/                    # FastAPI Python backend
│       ├── main.py                 # App entry point
│       ├── config.py               # Settings (pydantic-settings)
│       ├── dependencies.py         # Shared DI (DB, Redis, auth)
│       │
│       ├── api/
│       │   ├── v1/
│       │   │   ├── router.py       # Aggregate all route modules
│       │   │   ├── auth.py         # JWT auth routes
│       │   │   ├── emotion.py      # POST /emotion/infer
│       │   │   ├── session.py      # Session management
│       │   │   ├── adaptation.py   # GET/POST adaptation rules
│       │   │   └── analytics.py    # Emotion history + insights
│       │   └── websockets/
│       │       ├── emotion_ws.py   # ws://... emotion stream
│       │       └── adaptation_ws.py
│       │
│       ├── services/
│       │   ├── emotion_pipeline.py     # Orchestrates all modalities
│       │   ├── vision_service.py       # Camera frame → face emotion
│       │   ├── audio_service.py        # Audio chunk → vocal emotion
│       │   ├── behavior_service.py     # UI events → behavior state
│       │   ├── fusion_service.py       # Combines all modalities
│       │   ├── adaptation_engine.py    # RL-based adaptation decisions
│       │   ├── assistant_service.py    # LLM tone + response shaping
│       │   └── memory_service.py       # Long-term behavioral memory
│       │
│       ├── models/
│       │   ├── emotion.py          # Pydantic models: EmotionState, etc.
│       │   ├── adaptation.py       # AdaptationAction, UIConfig
│       │   ├── session.py          # UserSession, BehaviorEvent
│       │   └── user.py             # User, Profile
│       │
│       ├── ml/
│       │   ├── vision/
│       │   │   ├── face_detector.py        # YOLOv8 / MediaPipe face
│       │   │   ├── emotion_classifier.py   # ViT emotion from face
│       │   │   └── gaze_tracker.py         # MediaPipe gaze
│       │   ├── audio/
│       │   │   ├── feature_extractor.py    # MFCCs, pitch, tempo
│       │   │   └── emotion_classifier.py   # Wav2Vec2 stress/emotion
│       │   ├── behavior/
│       │   │   ├── keystroke_model.py      # LSTM keystroke patterns
│       │   │   └── cursor_model.py         # Cursor trajectory analysis
│       │   ├── fusion/
│       │   │   └── multimodal_fusion.py    # Cross-attention fusion
│       │   └── rl/
│       │       ├── adaptation_agent.py     # Ray RLlib or simple Q-learning
│       │       └── reward_calculator.py    # Reward from user outcomes
│       │
│       ├── db/
│       │   ├── database.py         # SQLAlchemy async engine
│       │   ├── migrations/         # Alembic migrations
│       │   └── repositories/
│       │       ├── user_repo.py
│       │       ├── session_repo.py
│       │       └── emotion_repo.py
│       │
│       ├── core/
│       │   ├── auth.py             # JWT utilities
│       │   ├── cache.py            # Redis client wrapper
│       │   ├── events.py           # App startup/shutdown
│       │   └── logging.py
│       │
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── fixtures/
│       │
│       ├── Dockerfile
│       ├── requirements.txt
│       └── pyproject.toml
│
├── ml/                             # Standalone ML experiments & training
│   ├── notebooks/
│   │   ├── 01_face_emotion_baseline.ipynb
│   │   ├── 02_audio_stress_detection.ipynb
│   │   ├── 03_keystroke_dynamics.ipynb
│   │   ├── 04_multimodal_fusion.ipynb
│   │   └── 05_rl_adaptation_sim.ipynb
│   ├── training/
│   │   ├── train_fusion_model.py
│   │   └── train_rl_agent.py
│   ├── evaluation/
│   │   └── benchmark.py
│   └── models/                     # Saved model weights (gitignored)
│
├── infra/
│   ├── terraform/                  # IaC (only if you go paid)
│   ├── k8s/                        # Kubernetes manifests
│   └── render/
│       └── render.yaml             # Render.com deployment config
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── ml-models.md
│   ├── privacy-ethics.md
│   └── contributing.md
│
└── scripts/
    ├── setup.sh                    # One-command local setup
    ├── seed_db.py                  # Seed test data
    └── load_models.py              # Download/cache HF models
```

---

## AI/ML Architecture

### 1. Vision Pipeline

**Input:** JPEG frame from browser webcam (captured every 500ms)  
**Output:** `{ emotion, confidence, fatigue_score, gaze_direction }`

```python
# apps/backend/ml/vision/emotion_classifier.py

from transformers import pipeline
import cv2
import mediapipe as mp

class VisionEmotionClassifier:
    def __init__(self):
        # Free Hugging Face model — runs on CPU
        self.emotion_pipe = pipeline(
            "image-classification",
            model="dima806/facial_emotions_image_detection",
            device=-1  # CPU; switch to 0 for GPU
        )
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True
        )

    def infer(self, frame_bytes: bytes) -> dict:
        img = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
        results = self.face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        emotion_result = self.emotion_pipe(Image.fromarray(img))
        return {
            "emotion": emotion_result[0]["label"],
            "confidence": emotion_result[0]["score"],
            "landmarks_detected": results.multi_face_landmarks is not None
        }
```

### 2. Audio Pipeline

**Input:** 2-second audio chunk (PCM float32, 16kHz)  
**Output:** `{ stress_level, vocal_emotion, speaking_tempo }`

```python
# apps/backend/ml/audio/emotion_classifier.py

import librosa
import numpy as np
from transformers import pipeline

class AudioEmotionClassifier:
    def __init__(self):
        self.ser_pipe = pipeline(
            "audio-classification",
            model="facebook/wav2vec2-base",
            device=-1
        )

    def extract_features(self, audio: np.ndarray, sr: int = 16000) -> dict:
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
        tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
        return {
            "mfcc_mean": mfccs.mean(axis=1).tolist(),
            "pitch_variance": float(pitches[pitches > 0].var()) if pitches.any() else 0.0,
            "tempo": float(tempo),
        }
```

### 3. Behavior Pipeline

**Input:** Stream of `BehaviorEvent` objects from frontend  
**Output:** `{ cognitive_load, frustration_score, attention_level }`

```python
# BehaviorEvent schema (Pydantic)
class BehaviorEvent(BaseModel):
    type: Literal["keypress", "mouse_move", "scroll", "click", "focus_change"]
    timestamp: float
    metadata: dict  # type-specific: key, position, delta, target, etc.

# Features derived:
# - typing_wpm: words per minute from keypress intervals
# - error_rate: backspace_count / total_keypresses
# - hesitation_index: variance in keypress inter-arrival time
# - cursor_jitter: mean deviation from linear cursor path
# - task_switches: focus_change events per minute
```

### 4. Multimodal Fusion

All three pipelines output normalized embeddings. The fusion layer combines them:

```python
# apps/backend/ml/fusion/multimodal_fusion.py

class MultimodalFusion:
    """
    Late fusion with learned attention weights.
    Vision, audio, and behavior embeddings are projected
    to a shared 128-dim space, then combined via weighted sum.
    Weights are learned per-user via the RL agent's feedback.
    """

    def fuse(
        self,
        vision_embedding: np.ndarray,   # shape: (32,)
        audio_embedding: np.ndarray,    # shape: (32,)
        behavior_embedding: np.ndarray, # shape: (64,)
        weights: dict = None
    ) -> EmotionState:
        w = weights or {"vision": 0.4, "audio": 0.3, "behavior": 0.3}
        # Weighted combination → final emotion vector
        # Outputs: frustration, stress, cognitive_load, attention, burnout_risk
        ...
```

**Final output schema:**

```json
{
  "emotion": "frustration",
  "confidence": 0.87,
  "stress_level": 0.74,
  "cognitive_load": 0.68,
  "attention_level": 0.52,
  "burnout_risk": 0.41,
  "recommended_adaptation": "reduce_complexity",
  "timestamp": "2024-01-15T14:32:00Z"
}
```

### 5. Reinforcement Learning Adaptation

For the MVP, we use **tabular Q-learning** (no Ray RLlib dependency — zero cost, pure Python):

```python
# apps/backend/ml/rl/adaptation_agent.py

class AdaptationAgent:
    """
    State: discretized (stress_bucket, cognitive_load_bucket, attention_bucket)
    Actions: 8 adaptation types (reduce_ui, focus_mode, pause_notifs, etc.)
    Reward: derived from next-interval task completion rate + emotional stability
    """

    ACTIONS = [
        "reduce_ui_complexity",
        "enable_focus_mode",
        "pause_notifications",
        "slow_content_pacing",
        "increase_ui_complexity",
        "enable_power_features",
        "resume_normal",
        "suggest_break",
    ]

    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.q_table = defaultdict(lambda: np.zeros(len(self.ACTIONS)))
        self.alpha = alpha    # learning rate
        self.gamma = gamma    # discount factor
        self.epsilon = epsilon  # exploration rate

    def select_action(self, state: tuple) -> str:
        if random.random() < self.epsilon:
            return random.choice(self.ACTIONS)
        return self.ACTIONS[np.argmax(self.q_table[state])]

    def update(self, state, action_idx, reward, next_state):
        best_next = np.max(self.q_table[next_state])
        self.q_table[state][action_idx] += self.alpha * (
            reward + self.gamma * best_next - self.q_table[state][action_idx]
        )
```

---

## Backend Architecture

### FastAPI App Structure

```python
# apps/backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load ML models, connect DB, warm Redis
    await load_ml_models()
    await init_db()
    await connect_redis()
    yield
    # Shutdown: flush buffers, close connections
    await shutdown_cleanup()

app = FastAPI(title="FlowState API", lifespan=lifespan)
app.include_router(api_v1_router, prefix="/api/v1")
```

### Core API Endpoints

```
POST   /api/v1/emotion/infer-frame       # Vision inference (base64 JPEG)
POST   /api/v1/emotion/infer-audio       # Audio inference (base64 WAV chunk)
POST   /api/v1/behavior/event            # Behavior event ingestion
GET    /api/v1/emotion/current/{user_id} # Current emotional state
GET    /api/v1/adaptation/config         # Current UI adaptation config
POST   /api/v1/adaptation/feedback       # RL reward signal from UI
GET    /api/v1/analytics/emotion-history/{session_id}  # Session emotion timeline (cursor-based)
GET    /api/v1/analytics/insights/{session_id}         # Aggregate session insights

WS     /ws/emotion/{user_id}             # Real-time emotion stream
WS     /ws/adaptation/{user_id}          # Real-time adaptation commands
```

### WebSocket Protocol

```typescript
// Frontend sends behavior events:
{
  "type": "behavior_event",
  "payload": { "event_type": "keypress", "timestamp": 1705324320.123, "metadata": { "key": "a" } }
}

// Backend streams emotion updates:
{
  "type": "emotion_update",
  "payload": {
    "stress_level": 0.72,
    "cognitive_load": 0.65,
    "recommended_adaptation": "reduce_ui_complexity"
  }
}
```

---

## Frontend Architecture

### Adaptive Shell

The `AdaptiveShell` component wraps the entire app and responds to the emotion stream:

```typescript
// apps/frontend/components/adaptive/AdaptiveShell.tsx

export function AdaptiveShell({ children }: { children: React.ReactNode }) {
  const { emotionState } = useEmotionStream();
  const { uiConfig, applyAdaptation } = useAdaptiveUI();

  useEffect(() => {
    if (emotionState?.recommended_adaptation) {
      applyAdaptation(emotionState.recommended_adaptation);
    }
  }, [emotionState?.recommended_adaptation]);

  return (
    <div
      data-complexity={uiConfig.complexity}   // "minimal" | "normal" | "advanced"
      data-density={uiConfig.density}          // "sparse" | "normal" | "dense"
      data-pace={uiConfig.pace}                // "slow" | "normal" | "fast"
      className={cn("app-shell", uiConfig.theme)}
    >
      {children}
    </div>
  );
}
```

### Behavior Tracking Hook

```typescript
// apps/frontend/hooks/useBehaviorTracker.ts

export function useBehaviorTracker() {
  const { sendEvent } = useEmotionStream();

  useEffect(() => {
    const handleKeydown = throttle((e: KeyboardEvent) => {
      sendEvent({
        type: "keypress",
        timestamp: performance.now(),
        metadata: { key: e.key, is_backspace: e.key === "Backspace" }
      });
    }, 50);

    const handleMouseMove = throttle((e: MouseEvent) => {
      sendEvent({
        type: "mouse_move",
        timestamp: performance.now(),
        metadata: { x: e.clientX, y: e.clientY }
      });
    }, 100);

    document.addEventListener("keydown", handleKeydown);
    document.addEventListener("mousemove", handleMouseMove);
    return () => {
      document.removeEventListener("keydown", handleKeydown);
      document.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);
}
```

### State Management (Zustand)

```typescript
// apps/frontend/stores/emotionStore.ts

interface EmotionStore {
  current: EmotionState | null;
  history: EmotionState[];
  isStreaming: boolean;
  setEmotion: (state: EmotionState) => void;
}

export const useEmotionStore = create<EmotionStore>((set) => ({
  current: null,
  history: [],
  isStreaming: false,
  setEmotion: (state) =>
    set((prev) => ({
      current: state,
      history: [...prev.history.slice(-99), state], // keep last 100
    })),
}));
```

---

## Database Schema

```sql
-- Users
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Sessions (one per user browser session)
CREATE TABLE sessions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id),
  started_at  TIMESTAMPTZ DEFAULT now(),
  ended_at    TIMESTAMPTZ,
  platform    TEXT  -- 'web', 'mobile', 'desktop'
);

-- Emotion snapshots (written every ~2s while session active)
CREATE TABLE emotion_snapshots (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id        UUID REFERENCES sessions(id),
  timestamp         TIMESTAMPTZ DEFAULT now(),
  emotion           TEXT,
  confidence        FLOAT,
  stress_level      FLOAT,
  cognitive_load    FLOAT,
  attention_level   FLOAT,
  burnout_risk      FLOAT,
  modalities_used   TEXT[]  -- ['vision','audio','behavior']
);

-- Adaptation events
CREATE TABLE adaptation_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID REFERENCES sessions(id),
  timestamp       TIMESTAMPTZ DEFAULT now(),
  action          TEXT,           -- 'reduce_ui_complexity', etc.
  trigger_emotion TEXT,
  trigger_stress  FLOAT,
  outcome_score   FLOAT           -- filled in after ~30s observation
);

-- Behavioral memory (long-term per-user patterns)
CREATE TABLE user_behavioral_profiles (
  user_id             UUID PRIMARY KEY REFERENCES users(id),
  peak_focus_hours    INT[],          -- e.g. [9, 10, 11, 14, 15]
  stress_triggers     JSONB,          -- { "after_2h_work": 0.8, "evening": 0.6 }
  preferred_pace      TEXT,           -- 'slow' | 'normal' | 'fast'
  avg_cognitive_load  FLOAT,
  updated_at          TIMESTAMPTZ DEFAULT now()
);
```

---

## Environment Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- Git

### One-Command Setup (Local)

```bash
git clone https://github.com/yourname/flowstate.git
cd flowstate
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script handles:
1. Creates Python virtualenv, installs requirements
2. Installs Node deps for frontend
3. Spins up Postgres + Redis via Docker Compose
4. Runs DB migrations via Alembic
5. Downloads required HuggingFace models (~1.5GB)
6. Seeds test user + demo data

### Manual Setup

```bash
# Backend
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Frontend
cd apps/frontend
npm install
npm run dev     # runs on localhost:3000

# Local services (Postgres + Redis)
docker-compose up -d postgres redis
```

### Environment Variables

```bash
# apps/backend/.env (copy from .env.example)

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flowstate
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-here-min-32-chars
HUGGINGFACE_TOKEN=hf_...           # Optional — needed for gated models only
SENTRY_DSN=                        # Optional — error tracking

# apps/frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=          # If using Supabase Auth
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

---

## Development Roadmap

### Phase 0 — Foundations (Week 1–2)

- [ ] Project scaffold (monorepo, Docker, CI)
- [x] Auth flow (JWT + Supabase) *(JWT auth with bcrypt, access/refresh tokens, /me endpoint)*
- [x] Database schema + Alembic migrations *(SQLite schema with versioned migration tracking)*
- [x] WebSocket skeleton (frontend ↔ backend) *(session-scoped backend stream at `/ws/emotion/{session_id}`)*
- [x] Basic behavior tracker (keystroke + mouse) *(backend ingestion + feature extraction MVP)*

### Phase 1 — First Working Signal (Week 3–4)

- [ ] Behavior-only emotion inference (no camera/mic yet)
- [ ] Frontend emotion badge (shows stress/cognitive load)
- [x] First adaptive UI response (reduce complexity on high stress) *(backend policy + `/api/v1/adaptation/config/{session_id}`)*
- [ ] Emotion history stored to Postgres

### Phase 2 — Vision + Audio (Week 5–7)

- [ ] Camera capture hook + frame sender
- [ ] Vision pipeline (MediaPipe + face emotion classifier)
- [ ] Audio capture + chunked sender
- [ ] Audio pipeline (MFCC features + Wav2Vec2)
- [ ] Fusion of all three modalities

### Phase 3 — Adaptive Dashboard (Week 8–10)

- [x] Real-time emotion radar visualization *(Next.js circular gauges + metric cards)*
- [x] Measurement guide + research references *(behavior signal definitions with affective computing, workload, mouse, and keystroke literature links)*
- [x] Stress curve + timeline chart *(Next.js SVG chart + analytics/intervention playback APIs)*
- [x] Attention heatmap overlay *(client-side bounded pointer/click map with primary zone and confidence stats)*
- [x] UI complexity adapts (sparse/normal/advanced) *(frontend applies `/adaptation/config/{session_id}` as data-driven layout states)*
- [x] Notification gating system *(deliver/queue/suppress with configurable policy)*

### Phase 4 — RL Agent (Week 11–13)

- [x] Q-learning adaptation agent *(epsilon-greedy policy + online updates from feedback)*
- [x] Reward signal from task completion events *(API + SQLite persistence at `/api/v1/adaptation/feedback`)*
- [x] Per-user Q-table persistence (Redis) *(SQLite zero-cost baseline; Redis-ready interface)*
- [x] Intervention playback screen *(backend timeline API ready: `/api/v1/adaptation/interventions/{session_id}`)*

### Phase 5 — Behavioral Memory (Week 14–16)

- [x] Long-term behavioral profile per user *(peak focus hours, stress triggers, preferred pace)*
- [x] Pattern detection (peak focus hours, stress triggers) *(automated from session history)*
- [x] Proactive suggestions ("You've been stressed 3 days in a row") *(streak_stress, burnout_risk, optimal_time, stress_trigger)*
- [x] Enterprise team analytics (aggregate, anonymized) *(SHA-256 hashed IDs, burnout risk, stress hotspots)*

### Phase 6 — Production Hardening

- [ ] Edge inference option (TFLite in browser via WASM)
- [ ] Federated learning support
- [x] GDPR-compliant data deletion *(cascade delete + data export + sensing controls)*
- [ ] Render + Vercel production deploy
- [ ] Grafana Cloud monitoring dashboard

---

## Privacy & Ethics

FlowState processes deeply personal data. The following constraints are non-negotiable:

**What the system will never do:**
- Store raw video or audio — only derived embeddings
- Share emotional data with third parties
- Use emotional signals to manipulate purchasing or engagement
- Exploit detected vulnerability states

**What the system does:**
- Processes camera/mic data locally in browser where possible
- Encrypts all embeddings at rest (AES-256)
- Provides a one-click "pause all sensing" toggle
- Exposes a full data export + deletion API
- Anonymizes all team analytics before storage

**User controls (always visible in UI):**
- Pause/resume sensing
- View what's currently being inferred
- Delete all historical data
- Opt out of behavioral memory
- Disable any individual modality (vision/audio/behavior independently)

---

## API Reference

Full API docs auto-generated at `http://localhost:8000/docs` (Swagger) and `/redoc` once the backend is running.

Key request/response examples:

```bash
# Infer emotion from camera frame
curl -X POST http://localhost:8000/api/v1/emotion/infer-frame \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{ "frame_b64": "<base64-encoded-jpeg>", "session_id": "uuid" }'

# Response
{
  "emotion": "frustration",
  "confidence": 0.87,
  "stress_level": 0.74,
  "cognitive_load": 0.61,
  "attention_level": 0.55,
  "burnout_risk": 0.38,
  "recommended_adaptation": "reduce_ui_complexity",
  "timestamp": "2024-01-15T14:32:00Z"
}
```

---

## Contributing

1. Fork the repo
2. Create your feature branch: `git checkout -b feat/my-feature`
3. Commit changes: `git commit -m 'feat: add burnout prediction model'`
4. Push to branch: `git push origin feat/my-feature`
5. Open a Pull Request

Commit message convention: `type(scope): description`  
Types: `feat` `fix` `docs` `chore` `refactor` `test`

---

## License

MIT — see [LICENSE](./LICENSE) for details.

---

> Built to demonstrate: multimodal AI · production MLOps · RL in production · real-time streaming · adaptive interfaces · behavioral AI · edge inference · systems architecture mastery.
