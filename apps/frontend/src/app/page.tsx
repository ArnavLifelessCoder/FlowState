"use client";

import { useEffect, useState, useCallback, useMemo, useRef, type ReactNode } from "react";
import { api } from "@/lib/api";

// ── Icon system ──────────────────────────────────────────────────
// A single stroke-based line-icon set keeps the UI consistent and avoids
// emoji, which render inconsistently across platforms and read as noise.

type IconName =
  | "dashboard" | "sessions" | "timeline" | "notifications" | "team" | "assessments"
  | "logout" | "vision" | "audio" | "behavior" | "stop" | "play" | "check"
  | "chevron-down" | "break" | "focus" | "bell-off" | "inbox" | "warning"
  | "arrow-left" | "arrow-right" | "close" | "refresh" | "flame"
  | "trend-up" | "trend-down" | "trend-steady";

const ICON_PATHS: Record<IconName, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
  sessions: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>,
  timeline: <path d="M3 12h4l2.5 6 4-14 2.5 8H21" />,
  notifications: <><path d="M6 9a6 6 0 0 1 12 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6Z" /><path d="M10 20a2 2 0 0 0 4 0" /></>,
  team: <><circle cx="9" cy="8" r="3.2" /><path d="M3.5 19a5.5 5.5 0 0 1 11 0" /><path d="M16 5.4a3 3 0 0 1 0 5.9" /><path d="M17.2 14.8A5.5 5.5 0 0 1 20.5 19" /></>,
  assessments: <><rect x="6" y="4" width="12" height="17" rx="2" /><rect x="9" y="2.5" width="6" height="3" rx="1" /><path d="M9 11h6M9 15h4" /></>,
  logout: <><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /><path d="M9 12h11" /><path d="M13 8l4 4-4 4" /></>,
  vision: <><rect x="3" y="6" width="18" height="13" rx="2.5" /><circle cx="12" cy="12.5" r="3.3" /><path d="M8.5 6l1.3-2h4.4L15.5 6" /></>,
  audio: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0" /><path d="M12 18v3" /></>,
  behavior: <><rect x="3" y="7" width="18" height="11" rx="2" /><path d="M7 11h.01M11 11h.01M15 11h.01M7 14.5h10" /></>,
  stop: <rect x="6" y="6" width="12" height="12" rx="2.5" />,
  play: <path d="M8 5.5l11 6.5-11 6.5z" />,
  check: <path d="M5 12.5l4.5 4.5L19 6.5" />,
  "chevron-down": <path d="M6 9l6 6 6-6" />,
  break: <><path d="M5 9h12v5a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z" /><path d="M17 10h2a2 2 0 0 1 0 4h-2" /><path d="M8 2.5v2.5M12 2.5v2.5" /></>,
  focus: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.5" /></>,
  "bell-off": <><path d="M8.5 7.5A6 6 0 0 1 18 9c0 4 1.5 5.5 2 6h-7" /><path d="M6 9c0 4-1.5 5.5-2 6h6" /><path d="M10 20a2 2 0 0 0 4 0" /><path d="M3 3l18 18" /></>,
  inbox: <><path d="M4 13l2-8h12l2 8" /><path d="M4 13v5h16v-5" /><path d="M4 13h4l1.2 2h5.6l1.2-2H20" /></>,
  warning: <><path d="M12 4l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>,
  "arrow-left": <path d="M14 6l-6 6 6 6" />,
  "arrow-right": <path d="M10 6l6 6-6 6" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  refresh: <><path d="M20 11a8 8 0 0 0-14-4.5L4 8" /><path d="M4 4v4h4" /><path d="M4 13a8 8 0 0 0 14 4.5L20 16" /><path d="M20 20v-4h-4" /></>,
  flame: <path d="M12 3c3.2 3.8 4.5 6 4.5 9a4.5 4.5 0 0 1-9 0c0-1.3.6-2.4 1.4-3.4.6 1.2 1.3 1.4 2 1.4-.3-2.4-1.2-4.7 1.1-7z" />,
  "trend-up": <><path d="M4 16l5-5 4 3 7-8" /><path d="M16 6h4v4" /></>,
  "trend-down": <><path d="M4 8l5 5 4-3 7 8" /><path d="M16 18h4v-4" /></>,
  "trend-steady": <path d="M4 12h16" />,
};

function Icon({ name, size = 18, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {ICON_PATHS[name]}
    </svg>
  );
}

function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
      <rect x="2" y="2" width="20" height="20" rx="6" fill="url(#fs-brand)" />
      <path d="M6 15.5c2.2 0 2.2-7 4.5-7s2.3 7 4.5 7 2.2-3.5 3.5-3.5" stroke="white" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.95" />
      <defs>
        <linearGradient id="fs-brand" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--accent-primary)" />
          <stop offset="1" stopColor="var(--accent-secondary)" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// ── Types ────────────────────────────────────────────────────────

interface Snapshot {
  session_id: string;
  cognitive_load: number;
  frustration_score: number;
  attention_level: number;
  recommended_adaptation: string;
  sample_size: number;
  updated_at: string;
}

interface UIConfig {
  complexity: "minimal" | "normal" | "advanced";
  density: "sparse" | "normal" | "dense";
  pace: "slow" | "normal" | "fast";
  notifications_paused: boolean;
}

interface AdaptationConfigResponse {
  session_id: string;
  ui_config: UIConfig;
  recommended_adaptation: string;
  generated_at: string;
}

interface Session {
  session_id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
  platform: string;
}

interface ActivityItem {
  id: string;
  type: "session" | "behavior" | "notification" | "auth" | "assessment";
  text: string;
  time: Date;
}

interface AttentionPoint {
  id: string;
  x: number;
  y: number;
  intensity: number;
  kind: "move" | "click";
  captured_at: number;
}

interface BehaviorSnapshotRecord {
  id: number;
  session_id: string;
  snapshot: Snapshot;
}

interface BehaviorHistoryResponse {
  session_id: string;
  items: BehaviorSnapshotRecord[];
  has_more: boolean;
  next_cursor: string | null;
}

interface BehaviorInsightsResponse {
  session_id: string;
  sample_count: number;
  avg_cognitive_load: number;
  avg_frustration_score: number;
  avg_attention_level: number;
  latest_recommended_adaptation: string;
}

interface InterventionPlaybackItem {
  event_type: "decision" | "feedback" | string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

interface InterventionPlaybackResponse {
  session_id: string;
  total_items: number;
  has_more: boolean;
  next_cursor: string | null;
  items: InterventionPlaybackItem[];
}

interface MetricDefinition {
  label: string;
  value: string;
  signal: string;
  interpretation: string;
}

interface ResearchReference {
  title: string;
  authors: string;
  year: string;
  url: string;
  note: string;
}

// ── Auth Component ───────────────────────────────────────────────

function AuthPage({ onLogin }: { onLogin: (userId: string, name: string) => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegister) {
        const reg = await api.register(username, password, displayName);
        if (!reg.ok) {
          setError(reg.data.detail || "Registration failed");
          setLoading(false);
          return;
        }
      }
      const login = await api.login(username, password);
      if (!login.ok) {
        setError(login.data.detail || "Login failed");
        setLoading(false);
        return;
      }
      const me = await api.getMe();
      if (me) {
        onLogin(me.user_id, me.display_name || me.username);
      }
    } catch {
      setError("Cannot connect to backend. Is it running on :8000?");
    }
    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo"><BrandMark size={40} /></div>
          <h1>FlowState</h1>
          <p>{isRegister ? "Create your account" : "Sign in to your dashboard"}</p>
        </div>
        {error && <div className="auth-error">{error}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Username</label>
            <input className="input" type="text" placeholder="your_username" value={username}
              onChange={e => setUsername(e.target.value)} required minLength={3} />
          </div>
          {isRegister && (
            <div className="input-group">
              <label>Display Name</label>
              <input className="input" type="text" placeholder="Your Name" value={displayName}
                onChange={e => setDisplayName(e.target.value)} />
            </div>
          )}
          <div className="input-group">
            <label>Password</label>
            <input className="input" type="password" placeholder="••••••••" value={password}
              onChange={e => setPassword(e.target.value)} required minLength={8} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "..." : isRegister ? "Create Account" : "Sign In"}
          </button>
        </form>
        <div className="auth-toggle">
          {isRegister ? "Already have an account? " : "Don't have an account? "}
          <button onClick={() => { setIsRegister(!isRegister); setError(""); }}>
            {isRegister ? "Sign In" : "Register"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Gauge Component ──────────────────────────────────────────────

function Gauge({ value, label, color, size = 100 }: { value: number; label: string; color: string; size?: number }) {
  const r = (size - 16) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value * circ);

  return (
    <div className="gauge">
      <svg width={size} height={size}>
        <circle className="gauge-track" cx={size / 2} cy={size / 2} r={r} />
        <circle className="gauge-fill" cx={size / 2} cy={size / 2} r={r}
          stroke={color} strokeDasharray={circ} strokeDashoffset={offset} />
      </svg>
      <div className="gauge-center" style={{ color }}>{Math.round(value * 100)}%</div>
      <span className="gauge-label">{label}</span>
    </div>
  );
}

function clampMetric(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function formatPercent(value: number) {
  return `${Math.round(clampMetric(value) * 100)}%`;
}

function titleCaseAction(action: string | undefined) {
  if (!action) return "No Recommendation";
  return action.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function payloadText(value: unknown, fallback = "-") {
  if (typeof value === "string" && value.length > 0) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return fallback;
}

function metricPath(points: number[], width: number, height: number, padding: { top: number; right: number; bottom: number; left: number }) {
  if (points.length === 0) return "";
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  return points.map((point, index) => {
    const x = points.length === 1
      ? padding.left + innerWidth / 2
      : padding.left + (index / (points.length - 1)) * innerWidth;
    const y = padding.top + (1 - clampMetric(point)) * innerHeight;
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

// Encode Float32 mono PCM samples as a 16-bit PCM WAV blob. The backend audio
// DSP pipeline needs real PCM, so we capture via WebAudio rather than sending
// an opaque compressed (webm/opus) MediaRecorder blob it cannot decode.
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);       // PCM chunk size
  view.setUint16(20, 1, true);        // audio format = PCM
  view.setUint16(22, 1, true);        // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);        // block align
  view.setUint16(34, 16, true);       // bits per sample
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function titleCase(value: string | undefined) {
  if (!value) return "";
  return value.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function emotionTone(stress: number) {
  if (stress > 0.6) return "alert";
  if (stress > 0.35) return "watch";
  return "calm";
}

function actionTone(action: string | undefined) {
  if (!action) return "normal";
  if (["suggest_break", "pause_notifications", "reduce_ui_complexity"].includes(action)) return "high";
  if (["enable_focus_mode", "slow_content_pacing"].includes(action)) return "medium";
  return "normal";
}

// ── Multimodal Types ─────────────────────────────────────────────

interface EmotionStateData {
  session_id: string;
  emotion: string;
  confidence: number;
  stress_level: number;
  cognitive_load: number;
  attention_level: number;
  burnout_risk: number;
  recommended_adaptation: string;
  modalities_used: string[];
  timestamp: string;
  smoothed?: boolean;
  stability?: number;
  trend?: "rising" | "falling" | "steady";
  vision?: { emotion: string; confidence: number; fatigue_score: number; gaze_direction: string; landmarks_detected: boolean } | null;
  audio?: { stress_level: number; vocal_emotion: string; speaking_tempo: number; pitch_variance: number } | null;
}

interface ModalityState {
  vision: boolean;
  audio: boolean;
  behavior: boolean;
}

const CAMERA_CAPTURE_MS = 500;
const AUDIO_CHUNK_MS = 2000;

const MAX_ATTENTION_POINTS = 120;
const MOUSE_EVENT_SAMPLE_MS = 250;
const HEATMAP_SAMPLE_MS = 120;
const ADAPTATION_CONFIG_SAMPLE_MS = 1200;
const DEFAULT_UI_CONFIG: UIConfig = {
  complexity: "normal",
  density: "normal",
  pace: "normal",
  notifications_paused: false,
};

const RESEARCH_REFERENCES: ResearchReference[] = [
  {
    title: "Affective Computing for HCI",
    authors: "Picard",
    year: "1999",
    url: "https://www.media.mit.edu/publications/affective-computing-for-hci/",
    note: "Frames emotional-state-aware interfaces and user frustration reduction.",
  },
  {
    title: "NASA-TLX workload model",
    authors: "Hart & Staveland",
    year: "1988",
    url: "https://human-factors.arc.nasa.gov/awards_pubs/publication_view.php?publication_id=2553",
    note: "Grounding for multi-factor cognitive workload thinking.",
  },
  {
    title: "Mouse trajectories and workload",
    authors: "McIlroy et al.",
    year: "2022",
    url: "https://www.tandfonline.com/doi/full/10.1080/10447318.2021.2002054",
    note: "Mouse movement patterns can indicate cognitive workload changes.",
  },
  {
    title: "Keystroke dynamics and stress",
    authors: "Vizer et al.",
    year: "2009",
    url: "https://www.sciencedirect.com/science/article/pii/S1071581909000937",
    note: "Keyboard timing features have been studied as stress indicators.",
  },
];

function formatCoordinate(value: number) {
  return `${Math.round(clampMetric(value) * 100)}%`;
}

function attentionZone(points: AttentionPoint[]) {
  if (points.length === 0) {
    return { label: "No signal", confidence: 0 };
  }

  const totals = points.reduce(
    (acc, point, index) => {
      const recency = (index + 1) / points.length;
      const weight = point.intensity * (0.5 + recency);
      return {
        x: acc.x + point.x * weight,
        y: acc.y + point.y * weight,
        weight: acc.weight + weight,
      };
    },
    { x: 0, y: 0, weight: 0 },
  );

  const x = totals.weight > 0 ? totals.x / totals.weight : 0.5;
  const y = totals.weight > 0 ? totals.y / totals.weight : 0.5;
  const horizontal = x < 0.33 ? "Left" : x > 0.66 ? "Right" : "Center";
  const vertical = y < 0.33 ? "Upper" : y > 0.66 ? "Lower" : "Middle";
  const label = vertical === "Middle" && horizontal === "Center" ? "Center" : `${vertical} ${horizontal}`;

  return {
    label,
    confidence: Math.min(1, points.length / 45),
  };
}

function uiConfigFromAction(action: string | undefined): UIConfig {
  if (action === "pause_notifications") {
    return { complexity: "normal", density: "sparse", pace: "slow", notifications_paused: true };
  }
  if (action === "reduce_ui_complexity" || action === "enable_focus_mode") {
    return { complexity: "minimal", density: "sparse", pace: "slow", notifications_paused: false };
  }
  if (action === "increase_ui_complexity" || action === "enable_power_features") {
    return { complexity: "advanced", density: "dense", pace: "fast", notifications_paused: false };
  }
  return DEFAULT_UI_CONFIG;
}

function metricDefinitions(snapshot: Snapshot | null): MetricDefinition[] {
  return [
    {
      label: "Cognitive load",
      value: formatPercent(snapshot?.cognitive_load ?? 0),
      signal: "Typing pace, hesitation variance, correction rate, and focus switches.",
      interpretation: "Higher means interaction patterns look more mentally effortful.",
    },
    {
      label: "Frustration",
      value: formatPercent(snapshot?.frustration_score ?? 0),
      signal: "Backspace/error rate combined with the current load estimate.",
      interpretation: "Higher means the session shows more correction-heavy or strained input.",
    },
    {
      label: "Attention",
      value: formatPercent(snapshot?.attention_level ?? 0),
      signal: "Inverse of load and error signals, plus active interaction continuity.",
      interpretation: "Higher means interaction looks steadier and less disrupted.",
    },
  ];
}

// ── Main Dashboard ───────────────────────────────────────────────

export default function Home() {
  const [userId, setUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("User");
  const [page, setPage] = useState("dashboard");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [adaptationConfig, setAdaptationConfig] = useState<AdaptationConfigResponse | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [attentionPoints, setAttentionPoints] = useState<AttentionPoint[]>([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [emotionState, setEmotionState] = useState<EmotionStateData | null>(null);
  const [modalities, setModalities] = useState<ModalityState>({ vision: false, audio: false, behavior: true });
  const trackerRef = useRef<number | null>(null);
  const adaptationRequestRef = useRef(0);
  const adaptationFetchedAtRef = useRef(0);
  const cameraRef = useRef<{ stream: MediaStream; video: HTMLVideoElement; canvas: HTMLCanvasElement; timer: number } | null>(null);
  const audioRef = useRef<{ stream: MediaStream; ctx: AudioContext; source: MediaStreamAudioSourceNode; processor: ScriptProcessorNode; timer: number } | null>(null);

  // Check auth on mount
  useEffect(() => {
    (async () => {
      try {
        const health = await api.health();
        setBackendOnline(health?.status === "ok");
      } catch {
        setBackendOnline(false);
      }
      if (api.isAuthenticated) {
        const me = await api.getMe();
        if (me) {
          setUserId(me.user_id);
          setDisplayName(me.display_name || me.username);
        }
      }
    })();
  }, []);

  const addActivity = useCallback((type: ActivityItem["type"], text: string) => {
    setActivity(prev => [{ id: Date.now().toString(), type, text, time: new Date() }, ...prev].slice(0, 30));
  }, []);

  // Load sessions
  useEffect(() => {
    if (!userId) return;
    api.listSessions(userId).then((data: { sessions: Session[] }) => {
      if (data?.sessions) setSessions(data.sessions);
    });
  }, [userId]);

  useEffect(() => {
    if (!activeSession || snapshot?.session_id !== activeSession) return;
    const elapsed = Date.now() - adaptationFetchedAtRef.current;
    const delay = Math.max(0, ADAPTATION_CONFIG_SAMPLE_MS - elapsed);
    const requestId = adaptationRequestRef.current + 1;
    adaptationRequestRef.current = requestId;

    const timer = window.setTimeout(() => {
      adaptationFetchedAtRef.current = Date.now();
      api.getAdaptationConfig(activeSession)
        .then((data: AdaptationConfigResponse) => {
          if (adaptationRequestRef.current === requestId && data.session_id === activeSession) {
            setAdaptationConfig(data);
          }
        })
        .catch(() => {
          if (adaptationRequestRef.current === requestId) {
            setAdaptationConfig({
              session_id: activeSession,
              ui_config: uiConfigFromAction(snapshot.recommended_adaptation),
              recommended_adaptation: snapshot.recommended_adaptation,
              generated_at: new Date().toISOString(),
            });
          }
        });
    }, delay);

    return () => window.clearTimeout(timer);
  }, [activeSession, snapshot?.session_id, snapshot?.updated_at, snapshot?.recommended_adaptation]);

  // Camera capture — sends JPEG frames to /emotion/infer-frame
  useEffect(() => {
    if (!activeSession || !modalities.vision) {
      if (cameraRef.current) {
        clearInterval(cameraRef.current.timer);
        cameraRef.current.stream.getTracks().forEach(t => t.stop());
        cameraRef.current = null;
      }
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, facingMode: "user" } });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }

        const video = document.createElement("video");
        video.srcObject = stream;
        video.muted = true;
        await video.play();

        const canvas = document.createElement("canvas");
        canvas.width = 320;
        canvas.height = 240;
        const ctx = canvas.getContext("2d")!;

        const timer = window.setInterval(() => {
          if (!activeSession || cancelled) return;
          ctx.drawImage(video, 0, 0, 320, 240);
          const dataUrl = canvas.toDataURL("image/jpeg", 0.6);
          const b64 = dataUrl.split(",")[1];
          if (b64) {
            api.inferFrame(activeSession, b64)
              .then((data: EmotionStateData) => {
                if (data?.session_id === activeSession) setEmotionState(data);
              })
              .catch(() => {});
          }
        }, CAMERA_CAPTURE_MS);

        cameraRef.current = { stream, video, canvas, timer };
        addActivity("behavior", "Camera capture started");
      } catch {
        addActivity("behavior", "Camera access denied or unavailable");
      }
    })();

    return () => {
      cancelled = true;
      if (cameraRef.current) {
        clearInterval(cameraRef.current.timer);
        cameraRef.current.stream.getTracks().forEach(t => t.stop());
        cameraRef.current = null;
      }
    };
  }, [activeSession, modalities.vision, addActivity]);

  // Audio capture — captures real PCM via WebAudio and sends 16-bit WAV chunks
  // to /emotion/infer-audio so the backend DSP pipeline can analyze the signal.
  useEffect(() => {
    const teardown = () => {
      if (audioRef.current) {
        clearInterval(audioRef.current.timer);
        try { audioRef.current.processor.disconnect(); } catch {}
        try { audioRef.current.source.disconnect(); } catch {}
        if (audioRef.current.ctx.state !== "closed") audioRef.current.ctx.close().catch(() => {});
        audioRef.current.stream.getTracks().forEach(t => t.stop());
        audioRef.current = null;
      }
    };

    if (!activeSession || !modalities.audio) {
      teardown();
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }

        const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        const source = ctx.createMediaStreamSource(stream);
        const processor = ctx.createScriptProcessor(4096, 1, 1);
        let buffer: number[] = [];

        processor.onaudioprocess = (e) => {
          if (cancelled) return;
          const input = e.inputBuffer.getChannelData(0);
          for (let i = 0; i < input.length; i++) buffer.push(input[i]);
        };

        source.connect(processor);
        processor.connect(ctx.destination);

        const timer = window.setInterval(() => {
          if (cancelled || !activeSession || buffer.length === 0) return;
          const samples = new Float32Array(buffer);
          buffer = [];
          const blob = encodeWav(samples, ctx.sampleRate);
          const reader = new FileReader();
          reader.onloadend = () => {
            const b64 = (reader.result as string).split(",")[1];
            if (b64) {
              api.inferAudio(activeSession, b64)
                .then((data: EmotionStateData) => {
                  if (data?.session_id === activeSession) setEmotionState(data);
                })
                .catch(() => {});
            }
          };
          reader.readAsDataURL(blob);
        }, AUDIO_CHUNK_MS);

        audioRef.current = { stream, ctx, source, processor, timer };
        addActivity("behavior", "Audio capture started");
      } catch {
        addActivity("behavior", "Microphone access denied or unavailable");
      }
    })();

    return () => {
      cancelled = true;
      teardown();
    };
  }, [activeSession, modalities.audio, addActivity]);

  // Behavior tracker - sends keypress events while a session is active
  useEffect(() => {
    if (!activeSession) return;
    let lastMouseSentAt = 0;
    let lastHeatmapAt = 0;

    const recordAttentionPoint = (e: MouseEvent, kind: AttentionPoint["kind"]) => {
      const width = Math.max(window.innerWidth, 1);
      const height = Math.max(window.innerHeight, 1);
      const capturedAt = Date.now();
      const point: AttentionPoint = {
        id: `${capturedAt}-${kind}-${Math.round(e.clientX)}-${Math.round(e.clientY)}`,
        x: clampMetric(e.clientX / width),
        y: clampMetric(e.clientY / height),
        intensity: kind === "click" ? 1 : 0.58,
        kind,
        captured_at: capturedAt,
      };
      setAttentionPoints(prev => [...prev.slice(-(MAX_ATTENTION_POINTS - 1)), point]);
    };

    const sendBehavior = (event: { type: string; timestamp: number; metadata: Record<string, unknown> }) => {
      api.sendBehaviorEvent(activeSession, event)
        .then((data: Snapshot) => {
          if (data?.session_id === activeSession) setSnapshot(data);
          setBackendOnline(true);
        })
        .catch(() => {
          setBackendOnline(false);
        });
    };

    const handleKey = (e: KeyboardEvent) => {
      sendBehavior({
        type: "keypress",
        timestamp: performance.now() / 1000,
        metadata: { key: e.key, is_backspace: e.key === "Backspace" },
      });
    };

    const handleMouse = (e: MouseEvent) => {
      const now = performance.now();
      if (now - lastHeatmapAt >= HEATMAP_SAMPLE_MS) {
        lastHeatmapAt = now;
        recordAttentionPoint(e, "move");
      }
      if (now - lastMouseSentAt < MOUSE_EVENT_SAMPLE_MS) return;
      lastMouseSentAt = now;
      sendBehavior({
        type: "mouse_move",
        timestamp: performance.now() / 1000,
        metadata: { x: e.clientX, y: e.clientY },
      });
    };

    const handleClick = (e: MouseEvent) => {
      recordAttentionPoint(e, "click");
      sendBehavior({
        type: "click",
        timestamp: performance.now() / 1000,
        metadata: { x: e.clientX, y: e.clientY, button: e.button },
      });
    };

    const handleVisibilityChange = () => {
      sendBehavior({
        type: "focus_change",
        timestamp: performance.now() / 1000,
        metadata: { visibility: document.visibilityState },
      });
    };

    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousemove", handleMouse);
    document.addEventListener("click", handleClick);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Poll the latest snapshot without adding synthetic behavior to the model.
    trackerRef.current = window.setInterval(() => {
      api.getCurrentBehavior(activeSession)
        .then((data: Snapshot) => {
          if (data?.session_id === activeSession) setSnapshot(data);
          setBackendOnline(true);
        })
        .catch(() => setBackendOnline(false));
    }, 2000);

    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousemove", handleMouse);
      document.removeEventListener("click", handleClick);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (trackerRef.current) clearInterval(trackerRef.current);
    };
  }, [activeSession]);

  const handleLogin = (id: string, name: string) => {
    setUserId(id);
    setDisplayName(name);
    addActivity("auth", `Signed in as ${name}`);
  };

  const handleStartSession = async () => {
    if (!userId) return;
    const data = await api.createSession(userId);
    setActiveSession(data.session_id);
    setAdaptationConfig(null);
    setAttentionPoints([]);
    setSessions(prev => [data, ...prev]);
    addActivity("session", `Started session ${data.session_id.slice(0, 8)}...`);
  };

  const handleEndSession = async () => {
    if (!activeSession) return;
    await api.endSession(activeSession);
    addActivity("session", `Ended session ${activeSession.slice(0, 8)}...`);
    setActiveSession(null);
    setSnapshot(null);
    setAdaptationConfig(null);
    setAttentionPoints([]);
    if (userId) {
      const data = await api.listSessions(userId);
      if (data?.sessions) setSessions(data.sessions);
    }
  };

  const handleLogout = () => {
    api.clearTokens();
    setUserId(null);
    setActiveSession(null);
    setSnapshot(null);
    setAdaptationConfig(null);
    setAttentionPoints([]);
    setSessions([]);
  };

  // If not logged in
  if (!userId) {
    return <AuthPage onLogin={handleLogin} />;
  }

  const activeAdaptationConfig = adaptationConfig?.session_id === activeSession ? adaptationConfig : null;
  const activeUiConfig = activeAdaptationConfig?.ui_config ?? uiConfigFromAction(snapshot?.recommended_adaptation);
  const activeAdaptationAction = activeAdaptationConfig?.recommended_adaptation ?? snapshot?.recommended_adaptation ?? "";

  return (
    <div
      className="app-layout"
      data-complexity={activeUiConfig.complexity}
      data-density={activeUiConfig.density}
      data-pace={activeUiConfig.pace}
      data-notifications-paused={activeUiConfig.notifications_paused ? "true" : "false"}
    >
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon"><BrandMark size={26} /></div>
          <h1>FlowState</h1>
        </div>
        <nav className="sidebar-nav">
          <button className={`nav-item ${page === "dashboard" ? "active" : ""}`} onClick={() => setPage("dashboard")}>
            <span className="icon"><Icon name="dashboard" /></span> Dashboard
          </button>
          <button className={`nav-item ${page === "sessions" ? "active" : ""}`} onClick={() => setPage("sessions")}>
            <span className="icon"><Icon name="sessions" /></span> Sessions
          </button>
          <button className={`nav-item ${page === "timeline" ? "active" : ""}`} onClick={() => setPage("timeline")}>
            <span className="icon"><Icon name="timeline" /></span> Timeline
          </button>
          <button className={`nav-item ${page === "notifications" ? "active" : ""}`} onClick={() => setPage("notifications")}>
            <span className="icon"><Icon name="notifications" /></span> Notifications
          </button>
          <button className={`nav-item ${page === "teams" ? "active" : ""}`} onClick={() => setPage("teams")}>
            <span className="icon"><Icon name="team" /></span> Team Analytics
          </button>
          <button className={`nav-item ${page === "assessments" ? "active" : ""}`} onClick={() => setPage("assessments")}>
            <span className="icon"><Icon name="assessments" /></span> Assessments
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="user-badge">
            <div className="user-avatar">{displayName[0]?.toUpperCase()}</div>
            <div className="user-info">
              <div className="name">{displayName}</div>
              <div className="role">Developer</div>
            </div>
            <button className="btn-icon" onClick={handleLogout} title="Sign out" aria-label="Sign out"><Icon name="logout" size={16} /></button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        {page === "dashboard" && (
          <DashboardPage
            snapshot={snapshot} activeSession={activeSession} sessions={sessions}
            activity={activity} backendOnline={backendOnline} attentionPoints={attentionPoints}
            uiConfig={activeUiConfig} adaptationAction={activeAdaptationAction}
            emotionState={emotionState} modalities={modalities}
            onStartSession={handleStartSession} onEndSession={handleEndSession}
            onToggleModality={(key) => setModalities(prev => ({ ...prev, [key]: !prev[key] }))}
          />
        )}
        {page === "sessions" && <SessionsPage sessions={sessions} activeSession={activeSession} />}
        {page === "timeline" && <TimelinePage sessions={sessions} activeSession={activeSession} liveSnapshot={snapshot} />}
        {page === "notifications" && <NotificationsPage activeSession={activeSession} addActivity={addActivity} />}
        {page === "teams" && <TeamsPage userId={userId} />}
        {page === "assessments" && <AssessmentsPage userId={userId} activeSession={activeSession} addActivity={addActivity} />}
      </main>

      {/* Floating mood indicator — driven by the smoothed emotion stream */}
      {activeSession && emotionState && emotionState.modalities_used.length > 0 && (
        <div className={`emotion-badge tone-${emotionTone(emotionState.stress_level)}`} id="emotion-badge">
          <span className="badge-dot" />
          <div className="badge-body">
            <div className="badge-row">
              <span className="badge-label">{titleCase(emotionState.emotion)}</span>
              {emotionState.trend && emotionState.trend !== "steady" && (
                <Icon
                  name={emotionState.trend === "rising" ? "trend-up" : "trend-down"}
                  size={13}
                  className="badge-trend"
                />
              )}
            </div>
            <div className="badge-meta">
              <span>{(emotionState.confidence * 100).toFixed(0)}% confidence</span>
              {typeof emotionState.stability === "number" && (
                <span className="badge-stability" title="Signal stability">
                  {emotionState.stability >= 0.8 ? "stable" : emotionState.stability >= 0.5 ? "settling" : "volatile"}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Dashboard Page ───────────────────────────────────────────────

function DashboardPage({ snapshot, activeSession, sessions, activity, backendOnline, attentionPoints, uiConfig, adaptationAction, emotionState, modalities, onStartSession, onEndSession, onToggleModality }: {
  snapshot: Snapshot | null; activeSession: string | null; sessions: Session[];
  activity: ActivityItem[]; backendOnline: boolean; attentionPoints: AttentionPoint[];
  uiConfig: UIConfig; adaptationAction: string;
  emotionState: EmotionStateData | null; modalities: ModalityState;
  onStartSession: () => void; onEndSession: () => void;
  onToggleModality: (key: keyof ModalityState) => void;
}) {
  const cog = snapshot?.cognitive_load ?? 0;
  const frust = snapshot?.frustration_score ?? 0;
  const att = snapshot?.attention_level ?? 0;
  const definitions = useMemo(() => metricDefinitions(snapshot), [snapshot]);

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>Behavior-only estimates from keyboard, mouse, and session patterns</p>
        </div>
        <div className="header-actions">
          {backendOnline && (
            <div className="live-indicator"><div className="live-dot" /> LIVE</div>
          )}
          {activeSession ? (
            <button className="btn btn-danger" onClick={onEndSession}><Icon name="stop" size={15} /> End Session</button>
          ) : (
            <button className="btn btn-primary" onClick={onStartSession}><Icon name="play" size={15} /> Start Session</button>
          )}
        </div>
      </div>

      <MeasurementGuide
        definitions={definitions}
        references={RESEARCH_REFERENCES}
        sampleSize={snapshot?.sample_size ?? 0}
        activeSession={activeSession}
      />

      {/* Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card cognitive">
          <span className="metric-label">Cognitive Load</span>
          <span className="metric-value cognitive">{(cog * 100).toFixed(0)}%</span>
          <span className="metric-signal">Effort proxy from pace, errors, pauses</span>
          <div className="metric-bar"><div className="metric-bar-fill cognitive" style={{ width: `${cog * 100}%` }} /></div>
        </div>
        <div className="metric-card frustration">
          <span className="metric-label">Frustration</span>
          <span className="metric-value frustration">{(frust * 100).toFixed(0)}%</span>
          <span className="metric-signal">Correction and load-derived strain</span>
          <div className="metric-bar"><div className="metric-bar-fill frustration" style={{ width: `${frust * 100}%` }} /></div>
        </div>
        <div className="metric-card attention">
          <span className="metric-label">Attention</span>
          <span className="metric-value attention">{(att * 100).toFixed(0)}%</span>
          <span className="metric-signal">Steady interaction and lower error load</span>
          <div className="metric-bar"><div className="metric-bar-fill attention" style={{ width: `${att * 100}%` }} /></div>
        </div>
        <div className="metric-card sessions adaptive-secondary">
          <span className="metric-label">Total Sessions</span>
          <span className="metric-value sessions">{sessions.length}</span>
          <div className="metric-bar"><div className="metric-bar-fill" style={{ width: `${Math.min(sessions.length * 10, 100)}%`, background: "var(--accent-warning)" }} /></div>
        </div>
      </div>

      {/* Multimodal Emotion + Modality Controls */}
      <div className="dashboard-grid">
        <div className="card emotion-radar-card">
          <div className="card-header">
            <div>
              <div className="card-title">Emotion Radar</div>
              <div className="card-subtitle">
                {emotionState?.modalities_used?.length
                  ? `Active: ${emotionState.modalities_used.join(", ")}`
                  : "Enable modalities to start multimodal sensing"}
              </div>
            </div>
            {emotionState && (
              <span className={`status-badge ${emotionState.stress_level > 0.6 ? "suppress" : emotionState.stress_level > 0.35 ? "queue" : "active"}`}>
                <span className="status-dot" />
                {emotionState.emotion}
              </span>
            )}
          </div>
          <EmotionRadar emotionState={emotionState} />
        </div>

        <div className="card modality-card">
          <div className="card-header">
            <div className="card-title">Sensing Modalities</div>
          </div>
          <div className="modality-controls">
            <button
              className={`modality-toggle ${modalities.vision ? "active" : ""}`}
              onClick={() => onToggleModality("vision")}
              disabled={!activeSession}
              title="Toggle camera capture"
            >
              <span className="modality-icon"><Icon name="vision" size={22} /></span>
              <span className="modality-label">Vision</span>
              <span className={`modality-status ${modalities.vision ? "on" : "off"}`}>
                {modalities.vision ? "ON" : "OFF"}
              </span>
            </button>
            <button
              className={`modality-toggle ${modalities.audio ? "active" : ""}`}
              onClick={() => onToggleModality("audio")}
              disabled={!activeSession}
              title="Toggle microphone capture"
            >
              <span className="modality-icon"><Icon name="audio" size={22} /></span>
              <span className="modality-label">Audio</span>
              <span className={`modality-status ${modalities.audio ? "on" : "off"}`}>
                {modalities.audio ? "ON" : "OFF"}
              </span>
            </button>
            <button
              className={`modality-toggle ${modalities.behavior ? "active" : ""}`}
              onClick={() => onToggleModality("behavior")}
              disabled={!activeSession}
              title="Toggle keyboard/mouse tracking"
            >
              <span className="modality-icon"><Icon name="behavior" size={22} /></span>
              <span className="modality-label">Behavior</span>
              <span className={`modality-status ${modalities.behavior ? "on" : "off"}`}>
                {modalities.behavior ? "ON" : "OFF"}
              </span>
            </button>
          </div>
          {emotionState && (
            <div className="emotion-detail-grid">
              <div><span>Stress</span><strong>{(emotionState.stress_level * 100).toFixed(0)}%</strong></div>
              <div><span>Burnout Risk</span><strong>{(emotionState.burnout_risk * 100).toFixed(0)}%</strong></div>
              <div><span>Confidence</span><strong>{(emotionState.confidence * 100).toFixed(0)}%</strong></div>
              {emotionState.vision && <div><span>Gaze</span><strong>{emotionState.vision.gaze_direction}</strong></div>}
              {emotionState.audio && <div><span>Vocal</span><strong>{emotionState.audio.vocal_emotion}</strong></div>}
              {emotionState.audio && <div><span>Tempo</span><strong>{emotionState.audio.speaking_tempo.toFixed(0)} WPM</strong></div>}
            </div>
          )}
        </div>
      </div>

      {/* Gauges + Activity */}
      <div className="dashboard-grid">
        <div className="card adaptive-primary">
          <div className="card-header">
            <div>
              <div className="card-title">Real-Time Gauges</div>
              <div className="card-subtitle">{activeSession ? "Tracking active session" : "Start a session to begin"}</div>
            </div>
          </div>
          <div className="gauge-container">
            <Gauge value={cog} label="Cognitive" color="var(--accent-secondary)" />
            <Gauge value={frust} label="Frustration" color="var(--accent-danger)" />
            <Gauge value={att} label="Attention" color="var(--accent-success)" />
          </div>
        </div>

        <div className="card adaptive-secondary">
          <div className="card-header">
            <div className="card-title">Activity Feed</div>
          </div>
          <div className="activity-feed">
            {activity.length === 0 ? (
              <div className="empty-state"><div className="icon"><Icon name="inbox" size={26} /></div><p>No activity yet</p></div>
            ) : activity.map(item => (
              <div key={item.id} className="activity-item">
                <div className={`activity-icon ${item.type}`}>
                  <Icon name={item.type === "session" ? "sessions" : item.type === "notification" ? "notifications" : item.type === "auth" ? "logout" : "dashboard"} size={15} />
                </div>
                <div>
                  <div className="activity-text">{item.text}</div>
                  <div className="activity-time">{item.time.toLocaleTimeString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Adaptation recommendation */}
        <div className="card full-width">
          <div className="card-header">
            <div className="card-title">Current Adaptation</div>
            {activeSession && <span className="status-badge active"><span className="status-dot" /> Active</span>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div className={`adaptation-mark tone-${actionTone(adaptationAction)}`}>
              <Icon
                name={
                  adaptationAction === "reduce_ui_complexity" ? "chevron-down" :
                  adaptationAction === "suggest_break" ? "break" :
                  adaptationAction === "enable_focus_mode" ? "focus" :
                  adaptationAction === "pause_notifications" ? "bell-off" : "check"
                }
                size={22}
              />
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>
                {titleCaseAction(adaptationAction)}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                {snapshot ? `Based on ${snapshot.sample_size} behavior samples` : "Start a session and type or move your mouse to generate recommendations"}
              </div>
              <div className="adaptation-state-row">
                <span className="status-badge ended">Complexity: {uiConfig.complexity}</span>
                <span className="status-badge ended">Density: {uiConfig.density}</span>
                <span className="status-badge ended">Pace: {uiConfig.pace}</span>
                {uiConfig.notifications_paused && <span className="status-badge suppress">Notifications paused</span>}
              </div>
            </div>
          </div>
        </div>

        <div className="card full-width adaptive-advanced">
          <div className="card-header">
            <div>
              <div className="card-title">Attention Heatmap</div>
              <div className="card-subtitle">Pointer and click concentration during the active session</div>
            </div>
            <span className={`status-badge ${attentionPoints.length > 0 ? "active" : "ended"}`}>
              <span className="status-dot" />
              {attentionPoints.length} points
            </span>
          </div>
          <AttentionHeatmap points={attentionPoints} activeSession={activeSession} attentionLevel={att} />
        </div>
      </div>
    </>
  );
}

// ── Emotion Radar ────────────────────────────────────────────────

function EmotionRadar({ emotionState }: { emotionState: EmotionStateData | null }) {
  const metrics = useMemo(() => {
    if (!emotionState) return [0, 0, 0, 0, 0];
    return [
      emotionState.stress_level,
      emotionState.cognitive_load,
      1 - emotionState.attention_level, // invert so higher = worse
      emotionState.burnout_risk,
      1 - emotionState.confidence, // invert so higher = worse
    ];
  }, [emotionState]);

  const labels = ["Stress", "Load", "Distraction", "Burnout", "Uncertainty"];
  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 85;
  const levels = [0.25, 0.5, 0.75, 1.0];

  const angleStep = (2 * Math.PI) / 5;
  const startAngle = -Math.PI / 2;

  const point = (index: number, value: number) => {
    const angle = startAngle + index * angleStep;
    return {
      x: cx + Math.cos(angle) * maxR * value,
      y: cy + Math.sin(angle) * maxR * value,
    };
  };

  const polygonPoints = metrics.map((v, i) => point(i, v)).map(p => `${p.x},${p.y}`).join(" ");

  if (!emotionState || emotionState.modalities_used.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "40px 20px" }}>
        <div className="icon"><Icon name="focus" size={26} /></div>
        <p>Enable vision or audio modalities to see the emotion radar</p>
      </div>
    );
  }

  return (
    <div className="emotion-radar-wrap">
      <svg viewBox={`0 0 ${size} ${size}`} className="emotion-radar-svg">
        {/* Grid rings */}
        {levels.map(level => (
          <polygon
            key={level}
            className="radar-ring"
            points={Array.from({ length: 5 }, (_, i) => point(i, level))
              .map(p => `${p.x},${p.y}`)
              .join(" ")}
          />
        ))}
        {/* Axes */}
        {Array.from({ length: 5 }, (_, i) => {
          const p = point(i, 1);
          return <line key={i} className="radar-axis" x1={cx} y1={cy} x2={p.x} y2={p.y} />;
        })}
        {/* Data polygon */}
        <polygon className="radar-data" points={polygonPoints} />
        {/* Data dots */}
        {metrics.map((v, i) => {
          const p = point(i, v);
          return <circle key={i} className="radar-dot" cx={p.x} cy={p.y} r={3.5} />;
        })}
        {/* Labels */}
        {labels.map((label, i) => {
          const p = point(i, 1.22);
          return (
            <text key={label} className="radar-label" x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle">
              {label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function MeasurementGuide({ definitions, references, sampleSize, activeSession }: {
  definitions: MetricDefinition[];
  references: ResearchReference[];
  sampleSize: number;
  activeSession: string | null;
}) {
  return (
    <section className="measurement-guide" aria-label="What the dashboard is measuring">
      <div className="measurement-summary">
        <div>
          <span className="section-kicker">What this measures</span>
          <h3>Behavior signals, not mind-reading</h3>
          <p>
            FlowState estimates workload, frustration, and attention from interaction patterns.
            It does not inspect message content, diagnose health, or claim emotion certainty.
          </p>
        </div>
        <div className="measurement-status">
          <span className={`status-badge ${activeSession ? "active" : "ended"}`}>
            <span className="status-dot" />
            {activeSession ? "Live session" : "Idle"}
          </span>
          <strong>{sampleSize}</strong>
          <span>behavior samples</span>
        </div>
      </div>

      <div className="definition-grid">
        {definitions.map(item => (
          <div key={item.label} className="definition-card">
            <div>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
            <p>{item.signal}</p>
            <small>{item.interpretation}</small>
          </div>
        ))}
      </div>

      <div className="research-strip">
        <span className="section-kicker">Research basis</span>
        <div className="research-links">
          {references.map(reference => (
            <a key={reference.title} href={reference.url} target="_blank" rel="noreferrer" title={reference.note}>
              <strong>{reference.title}</strong>
              <span>{reference.authors}, {reference.year}</span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Sessions Page ────────────────────────────────────────────────

function AttentionHeatmap({ points, activeSession, attentionLevel }: {
  points: AttentionPoint[];
  activeSession: string | null;
  attentionLevel: number;
}) {
  const recentPoints = useMemo(() => points.slice(-90), [points]);
  const zone = useMemo(() => attentionZone(recentPoints), [recentPoints]);
  const latest = recentPoints[recentPoints.length - 1];
  const clicks = recentPoints.filter(point => point.kind === "click").length;

  if (!activeSession) {
    return <div className="empty-state"><div className="icon"><Icon name="focus" size={26} /></div><p>Start a session to capture attention zones</p></div>;
  }

  if (recentPoints.length === 0) {
    return <div className="empty-state"><div className="icon"><Icon name="focus" size={26} /></div><p>Move or click in the dashboard to populate the heatmap</p></div>;
  }

  return (
    <div className="heatmap-panel">
      <div className="heatmap-surface" role="img" aria-label="Attention heatmap of recent pointer movement and clicks">
        <div className="heatmap-grid" />
        {recentPoints.map((point, index) => {
          const recency = (index + 1) / recentPoints.length;
          const size = point.kind === "click" ? 72 : 48;
          return (
            <span
              key={point.id}
              className={`heatmap-dot ${point.kind}`}
              style={{
                left: `${point.x * 100}%`,
                top: `${point.y * 100}%`,
                width: size,
                height: size,
                opacity: 0.18 + recency * point.intensity * 0.72,
              }}
            />
          );
        })}
      </div>
      <div className="heatmap-stats">
        <div><span>Primary zone</span><strong>{zone.label}</strong></div>
        <div><span>Attention score</span><strong>{formatPercent(attentionLevel)}</strong></div>
        <div><span>Clicks</span><strong>{clicks}</strong></div>
        <div><span>Latest point</span><strong>{latest ? `${formatCoordinate(latest.x)}, ${formatCoordinate(latest.y)}` : "-"}</strong></div>
        <div><span>Confidence</span><strong>{formatPercent(zone.confidence)}</strong></div>
      </div>
    </div>
  );
}

function SessionsPage({ sessions, activeSession }: { sessions: Session[]; activeSession: string | null }) {
  return (
    <>
      <div className="page-header">
        <div><h2>Sessions</h2><p>Your session history</p></div>
      </div>
      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr><th>Session ID</th><th>Status</th><th>Platform</th><th>Started</th><th>Ended</th></tr>
            </thead>
            <tbody>
              {sessions.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: "center", padding: 40 }}>No sessions yet</td></tr>
              ) : sessions.map(s => (
                <tr key={s.session_id}>
                  <td style={{ fontFamily: "monospace", fontSize: 12 }}>{s.session_id.slice(0, 12)}...</td>
                  <td>
                    <span className={`status-badge ${s.session_id === activeSession ? "active" : s.ended_at ? "ended" : "active"}`}>
                      <span className="status-dot" />
                      {s.session_id === activeSession ? "Active" : s.ended_at ? "Ended" : "Active"}
                    </span>
                  </td>
                  <td>{s.platform}</td>
                  <td>{new Date(s.started_at).toLocaleString()}</td>
                  <td>{s.ended_at ? new Date(s.ended_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// ── Timeline Page ────────────────────────────────────────────────

function TimelinePage({ sessions, activeSession, liveSnapshot }: {
  sessions: Session[];
  activeSession: string | null;
  liveSnapshot: Snapshot | null;
}) {
  const [selectedSession, setSelectedSession] = useState("");
  const [history, setHistory] = useState<BehaviorHistoryResponse | null>(null);
  const [insights, setInsights] = useState<BehaviorInsightsResponse | null>(null);
  const [interventions, setInterventions] = useState<InterventionPlaybackResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const timelineRequestRef = useRef(0);
  const resolvedSession = selectedSession || activeSession || sessions[0]?.session_id || "";

  const loadTimeline = useCallback(async () => {
    if (!resolvedSession) {
      setHistory(null);
      setInsights(null);
      setInterventions(null);
      setError("");
      return;
    }
    const requestId = timelineRequestRef.current + 1;
    timelineRequestRef.current = requestId;
    setLoading(true);
    setError("");
    try {
      const [historyData, insightsData, interventionData] = await Promise.all([
        api.getEmotionHistory(resolvedSession, 160) as Promise<BehaviorHistoryResponse>,
        api.getSessionInsights(resolvedSession, 160) as Promise<BehaviorInsightsResponse>,
        api.getInterventions(resolvedSession, 60) as Promise<InterventionPlaybackResponse>,
      ]);
      if (timelineRequestRef.current !== requestId) return;
      setHistory(historyData);
      setInsights(insightsData);
      setInterventions(interventionData);
    } catch (err) {
      if (timelineRequestRef.current !== requestId) return;
      const message = err instanceof Error ? err.message : "Timeline data request failed";
      setError(message);
    } finally {
      if (timelineRequestRef.current === requestId) setLoading(false);
    }
  }, [resolvedSession]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadTimeline();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadTimeline]);

  const selectedSessionLabel = resolvedSession ? `${resolvedSession.slice(0, 12)}...` : "No session";

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Timeline</h2>
          <p>Stress curve, attention drift, and adaptation interventions over time</p>
        </div>
        <div className="header-actions">
          <select className="input session-select" value={resolvedSession} onChange={e => setSelectedSession(e.target.value)}>
            {sessions.length === 0 ? (
              <option value="">No sessions</option>
            ) : sessions.map(session => (
              <option key={session.session_id} value={session.session_id}>
                {session.session_id.slice(0, 12)} {session.session_id === activeSession ? "(active)" : ""}
              </option>
            ))}
          </select>
          <button className="btn btn-secondary" onClick={loadTimeline} disabled={!resolvedSession || loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {!resolvedSession ? (
        <div className="card">
          <div className="empty-state"><div className="icon"><Icon name="timeline" size={26} /></div><p>Start a session to build a timeline</p></div>
        </div>
      ) : (
        <div className="dashboard-grid">
          <div className="card full-width">
            <div className="card-header">
              <div>
                <div className="card-title">Stress Curve</div>
                <div className="card-subtitle">Session {selectedSessionLabel}</div>
              </div>
              {error ? <span className="status-badge suppress">Needs attention</span> : <span className="status-badge active">Synced</span>}
            </div>
            {error && <div className="auth-error timeline-error">{error}</div>}
            <StressTimelineChart
              history={history}
              liveSnapshot={liveSnapshot?.session_id === resolvedSession ? liveSnapshot : null}
              loading={loading}
            />
          </div>

          <div className="card">
            <div className="card-header"><div className="card-title">Window Summary</div></div>
            <TimelineSummary insights={insights} loading={loading} />
          </div>

          <div className="card">
            <div className="card-header"><div className="card-title">Intervention Playback</div></div>
            <InterventionList interventions={interventions} loading={loading} />
          </div>
        </div>
      )}
    </>
  );
}

function StressTimelineChart({ history, liveSnapshot, loading }: {
  history: BehaviorHistoryResponse | null;
  liveSnapshot: Snapshot | null;
  loading: boolean;
}) {
  const records = useMemo(() => {
    const historyRecords = (history?.items || []).map(item => item.snapshot);
    const merged = liveSnapshot ? [...historyRecords, liveSnapshot] : historyRecords;
    const unique = new Map<string, Snapshot>();
    for (const item of merged) {
      unique.set(`${item.updated_at}-${item.sample_size}`, item);
    }
    return Array.from(unique.values())
      .sort((a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime())
      .slice(-80);
  }, [history, liveSnapshot]);

  const width = 760;
  const height = 280;
  const padding = { top: 18, right: 24, bottom: 42, left: 48 };
  const frustration = records.map(item => item.frustration_score);
  const cognitive = records.map(item => item.cognitive_load);
  const attention = records.map(item => item.attention_level);
  const latest = records[records.length - 1];

  if (loading && records.length === 0) {
    return <div className="chart-state">Loading timeline...</div>;
  }

  if (records.length === 0) {
    return <div className="empty-state"><div className="icon"><Icon name="timeline" size={26} /></div><p>No behavior samples for this session yet</p></div>;
  }

  return (
    <div className="timeline-chart-wrap">
      <svg className="timeline-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Session stress curve">
        {[0, 0.25, 0.5, 0.75, 1].map(value => {
          const y = padding.top + (1 - value) * (height - padding.top - padding.bottom);
          return (
            <g key={value}>
              <line className="chart-grid" x1={padding.left} x2={width - padding.right} y1={y} y2={y} />
              <text className="chart-axis-label" x={12} y={y + 4}>{Math.round(value * 100)}</text>
            </g>
          );
        })}
        <path className="chart-line frustration" d={metricPath(frustration, width, height, padding)} />
        <path className="chart-line cognitive" d={metricPath(cognitive, width, height, padding)} />
        <path className="chart-line attention" d={metricPath(attention, width, height, padding)} />
        {records.map((item, index) => {
          if (index % Math.max(1, Math.ceil(records.length / 14)) !== 0 && index !== records.length - 1) return null;
          const x = records.length === 1
            ? padding.left + (width - padding.left - padding.right) / 2
            : padding.left + (index / (records.length - 1)) * (width - padding.left - padding.right);
          const tone = actionTone(item.recommended_adaptation);
          return <circle key={`${item.updated_at}-${index}`} className={`chart-event ${tone}`} cx={x} cy={height - padding.bottom + 12} r={4} />;
        })}
      </svg>
      <div className="chart-legend">
        <span><i className="legend-dot frustration" /> Frustration</span>
        <span><i className="legend-dot cognitive" /> Cognitive load</span>
        <span><i className="legend-dot attention" /> Attention</span>
      </div>
      <div className="timeline-latest">
        <div><span>Latest stress</span><strong>{formatPercent(latest.frustration_score)}</strong></div>
        <div><span>Latest load</span><strong>{formatPercent(latest.cognitive_load)}</strong></div>
        <div><span>Latest attention</span><strong>{formatPercent(latest.attention_level)}</strong></div>
        <div><span>Adaptation</span><strong>{titleCaseAction(latest.recommended_adaptation)}</strong></div>
      </div>
    </div>
  );
}

function TimelineSummary({ insights, loading }: { insights: BehaviorInsightsResponse | null; loading: boolean }) {
  if (loading && !insights) return <div className="chart-state">Calculating summary...</div>;
  if (!insights || insights.sample_count === 0) {
    return <div className="empty-state"><div className="icon">%</div><p>No summary available yet</p></div>;
  }
  return (
    <div className="summary-stack">
      <div className="summary-row"><span>Samples</span><strong>{insights.sample_count}</strong></div>
      <div className="summary-row"><span>Avg cognitive load</span><strong>{formatPercent(insights.avg_cognitive_load)}</strong></div>
      <div className="summary-row"><span>Avg frustration</span><strong>{formatPercent(insights.avg_frustration_score)}</strong></div>
      <div className="summary-row"><span>Avg attention</span><strong>{formatPercent(insights.avg_attention_level)}</strong></div>
      <div className="summary-row"><span>Latest adaptation</span><strong>{titleCaseAction(insights.latest_recommended_adaptation)}</strong></div>
    </div>
  );
}

function InterventionList({ interventions, loading }: {
  interventions: InterventionPlaybackResponse | null;
  loading: boolean;
}) {
  if (loading && !interventions) return <div className="chart-state">Loading interventions...</div>;
  const items = interventions?.items || [];
  if (items.length === 0) {
    return <div className="empty-state"><div className="icon">!</div><p>No adaptation decisions or feedback yet</p></div>;
  }
  return (
    <div className="intervention-list">
      {items.slice(0, 12).map((item, index) => {
        const action = payloadText(item.payload.action, item.event_type);
        const isFeedback = item.event_type === "feedback";
        const detail = isFeedback
          ? `Reward ${payloadText(item.payload.reward, "0")}`
          : `${payloadText(item.payload.state_key, "state")} ${payloadText(item.payload.exploration, "No") === "Yes" ? "explore" : "policy"}`;
        return (
          <div key={`${item.event_type}-${item.occurred_at}-${index}`} className={`intervention-item ${isFeedback ? "feedback" : "decision"}`}>
            <div>
              <div className="intervention-action">{titleCaseAction(action)}</div>
              <div className="intervention-meta">{detail}</div>
            </div>
            <time>{new Date(item.occurred_at).toLocaleTimeString()}</time>
          </div>
        );
      })}
    </div>
  );
}

// ── Notifications Page ───────────────────────────────────────────

function NotificationsPage({ activeSession, addActivity }: { activeSession: string | null; addActivity: (type: ActivityItem["type"], text: string) => void }) {
  const [result, setResult] = useState<{ decision: string; reason: string } | null>(null);
  const [title, setTitle] = useState("New message");
  const [source, setSource] = useState("slack");
  const [priority, setPriority] = useState("normal");

  const handleTest = async () => {
    if (!activeSession) return;
    const data = await api.evaluateNotification(activeSession, source, title, priority);
    setResult(data);
    addActivity("notification", `Notification "${title}" -> ${data.decision}`);
  };

  return (
    <>
      <div className="page-header">
        <div><h2>Notification Gating</h2><p>Test how notifications are filtered based on cognitive state</p></div>
      </div>
      <div className="dashboard-grid">
        <div className="card">
          <div className="card-header"><div className="card-title">Test a Notification</div></div>
          {!activeSession ? (
            <div className="empty-state"><div className="icon"><Icon name="warning" size={26} /></div><p>Start a session first from Dashboard</p></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="input-group">
                <label>Title</label>
                <input className="input" value={title} onChange={e => setTitle(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Source</label>
                <input className="input" value={source} onChange={e => setSource(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Priority</label>
                <select className="input" value={priority} onChange={e => setPriority(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <button className="btn btn-primary" onClick={handleTest}>Evaluate</button>
            </div>
          )}
        </div>
        <div className="card">
          <div className="card-header"><div className="card-title">Result</div></div>
          {result ? (
            <div style={{ textAlign: "center", padding: 20 }}>
              <div className={`decision-mark ${result.decision}`}>
                <Icon name={result.decision === "deliver" ? "check" : result.decision === "queue" ? "sessions" : "close"} size={26} />
              </div>
              <span className={`status-badge ${result.decision}`} style={{ fontSize: 16, padding: "8px 24px" }}>
                {result.decision.toUpperCase()}
              </span>
              <p style={{ marginTop: 16, fontSize: 13, color: "var(--text-secondary)" }}>{result.reason}</p>
            </div>
          ) : (
            <div className="empty-state"><div className="icon"><Icon name="notifications" size={26} /></div><p>Send a test notification</p></div>
          )}
        </div>
      </div>
    </>
  );
}

// ── Teams Page ───────────────────────────────────────────────────

function TeamsPage({ userId }: { userId: string }) {
  const [teamId, setTeamId] = useState("my-team");
  const [analytics, setAnalytics] = useState<{ aggregate: Record<string, unknown>; members: Record<string, unknown>[] } | null>(null);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    await api.createTeam(teamId, [userId]);
    handleFetch();
  };

  const handleFetch = async () => {
    setError("");
    const res = await api.getTeamAnalytics(teamId);
    if (res.ok) setAnalytics(res.data as typeof analytics);
    else setError("Team not found. Create it first.");
  };

  return (
    <>
      <div className="page-header">
        <div><h2>Team Analytics</h2><p>Anonymized aggregate metrics across team members</p></div>
      </div>
      <div className="dashboard-grid">
        <div className="card">
          <div className="card-header"><div className="card-title">Team Setup</div></div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="input-group">
              <label>Team ID</label>
              <input className="input" value={teamId} onChange={e => setTeamId(e.target.value)} />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn btn-primary" onClick={handleCreate}>Create Team</button>
              <button className="btn btn-secondary" onClick={handleFetch}>Load Analytics</button>
            </div>
            {error && <div className="auth-error">{error}</div>}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><div className="card-title">Team Aggregate</div></div>
          {analytics ? (
            <div className="table-wrapper">
              <table>
                <tbody>
                  <tr><td>Members</td><td style={{ fontWeight: 700 }}>{String(analytics.aggregate.member_count)}</td></tr>
                  <tr><td>Avg Cognitive Load</td><td style={{ fontWeight: 700 }}>{((analytics.aggregate.avg_cognitive_load as number) * 100).toFixed(0)}%</td></tr>
                  <tr><td>Avg Frustration</td><td style={{ fontWeight: 700 }}>{((analytics.aggregate.avg_frustration as number) * 100).toFixed(0)}%</td></tr>
                  <tr><td>Avg Attention</td><td style={{ fontWeight: 700 }}>{((analytics.aggregate.avg_attention as number) * 100).toFixed(0)}%</td></tr>
                  <tr><td>Burnout Risk</td><td style={{ fontWeight: 700, color: "var(--accent-danger)" }}>{String(analytics.aggregate.burnout_risk_count)}</td></tr>
                  <tr><td>Total Sessions</td><td style={{ fontWeight: 700 }}>{String(analytics.aggregate.total_sessions)}</td></tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state"><div className="icon"><Icon name="team" size={26} /></div><p>Create or load a team</p></div>
          )}
        </div>
      </div>
    </>
  );
}

// ── Assessments Page ─────────────────────────────────────────────

interface InstrumentSummary {
  type: string;
  name: string;
  description: string;
  estimated_seconds: number;
  question_count: number;
  research_basis: string;
}

interface InstrumentQuestion {
  id: string;
  text: string;
  subscale: string;
  min_value: number;
  max_value: number;
  reverse_scored: boolean;
  anchor_low: string;
  anchor_high: string;
}

interface InstrumentFull {
  instrument_type: string;
  name: string;
  description: string;
  estimated_seconds: number;
  questions: InstrumentQuestion[];
  scoring_method: string;
  research_basis: string;
}

interface AssessmentResultData {
  instrument_type: string;
  instrument_name: string;
  overall_score: number;
  normalized_score: number;
  severity: string;
  interpretation: string;
  recommendation: string;
  completed_at: string;
  subscale_scores: { name: string; raw_score: number; normalized: number; interpretation: string }[];
}

interface WellbeingData {
  user_id: string;
  sensor_stress: number | null;
  sensor_cognitive_load: number | null;
  sensor_attention: number | null;
  self_report_stress: number | null;
  self_report_energy: number | null;
  self_report_flow: number | null;
  self_report_burnout: number | null;
  calibration_delta: number | null;
  composite_wellbeing: number;
}

function AssessmentsPage({ userId, activeSession, addActivity }: {
  userId: string | null; activeSession: string | null;
  addActivity: (type: ActivityItem["type"], text: string) => void;
}) {
  const [instruments, setInstruments] = useState<InstrumentSummary[]>([]);
  const [activeInstrument, setActiveInstrument] = useState<InstrumentFull | null>(null);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [currentQ, setCurrentQ] = useState(0);
  const [result, setResult] = useState<AssessmentResultData | null>(null);
  const [history, setHistory] = useState<AssessmentResultData[]>([]);
  const [wellbeing, setWellbeing] = useState<WellbeingData | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.listInstruments().then((data: { instruments: InstrumentSummary[] }) => setInstruments(data.instruments || [])).catch(() => {});
    if (userId) {
      api.getAssessmentHistory(userId, undefined, 20).then((data: { assessments: AssessmentResultData[] }) => setHistory(data?.assessments || [])).catch(() => {});
      api.getWellbeing(userId, activeSession || undefined).then((data: WellbeingData) => setWellbeing(data)).catch(() => {});
    }
  }, [userId, activeSession]);

  const startAssessment = async (type: string) => {
    const data = await api.getInstrument(type);
    setActiveInstrument(data);
    setResponses({});
    setCurrentQ(0);
    setResult(null);
  };

  const handleResponse = (qid: string, value: number) => {
    setResponses(prev => ({ ...prev, [qid]: value }));
  };

  const submitAssessment = async () => {
    if (!activeInstrument || !userId) return;
    setSubmitting(true);
    try {
      const data = await api.submitAssessment(
        activeSession || "no-session",
        userId,
        activeInstrument.instrument_type,
        responses,
      );
      if (data.error) {
        addActivity("assessment", `Error: ${data.error}`);
      } else {
        setResult(data);
        addActivity("assessment", `Completed ${activeInstrument.name}: ${data.severity} severity`);
        // Refresh history and wellbeing
        api.getAssessmentHistory(userId, undefined, 20).then((d: { assessments: AssessmentResultData[] }) => setHistory(d?.assessments || [])).catch(() => {});
        api.getWellbeing(userId, activeSession || undefined).then((d: WellbeingData) => setWellbeing(d)).catch(() => {});
      }
    } catch {
      addActivity("assessment", "Failed to submit assessment");
    }
    setSubmitting(false);
  };

  const q = activeInstrument?.questions[currentQ];
  const allAnswered = activeInstrument ? activeInstrument.questions.every(q2 => q2.id in responses) : false;
  const progress = activeInstrument ? (Object.keys(responses).length / activeInstrument.questions.length) * 100 : 0;

  const severityColor = (s: string) =>
    s === "low" ? "var(--accent-success)" :
    s === "moderate" ? "var(--accent-warning)" :
    s === "high" ? "var(--accent-danger)" :
    "#ff4444";

  const instrumentIconName = (type: string): IconName =>
    type === "nasa_tlx" ? "dashboard" :
    type === "pss4" ? "warning" :
    type === "flow_short" ? "timeline" :
    type === "burnout_micro" ? "flame" :
    type === "mood_check" ? "focus" : "assessments";

  return (
    <>
      <div className="dashboard-header">
        <div>
          <h2>Psychometric Assessments</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
            Take validated assessments to calibrate sensing accuracy and track your wellbeing over time
          </p>
        </div>
      </div>

      {/* Active assessment flow */}
      {activeInstrument && !result && (
        <div className="card assessment-card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <div>
              <div className="card-title title-with-icon"><Icon name={instrumentIconName(activeInstrument.instrument_type)} size={18} /> {activeInstrument.name}</div>
              <div className="card-subtitle">Question {currentQ + 1} of {activeInstrument.questions.length}</div>
            </div>
            <button className="btn btn-small" onClick={() => { setActiveInstrument(null); setResult(null); }}><Icon name="close" size={14} /> Cancel</button>
          </div>

          {/* Progress bar */}
          <div className="metric-bar" style={{ marginBottom: 20 }}>
            <div className="metric-bar-fill cognitive" style={{ width: `${progress}%`, transition: "width 0.3s ease" }} />
          </div>

          {q && (
            <div className="assessment-question">
              <p className="question-text">{q.text}</p>
              <div className="question-anchors">
                <span>{q.anchor_low}</span>
                <span>{q.anchor_high}</span>
              </div>
              <div className="question-scale">
                {Array.from({ length: q.max_value - q.min_value + 1 }, (_, i) => q.min_value + i).map(val => (
                  <button
                    key={val}
                    className={`scale-btn ${responses[q.id] === val ? "selected" : ""}`}
                    onClick={() => {
                      handleResponse(q.id, val);
                      // Auto-advance after short delay
                      if (currentQ < activeInstrument.questions.length - 1) {
                        setTimeout(() => setCurrentQ(prev => prev + 1), 300);
                      }
                    }}
                  >
                    {val}
                  </button>
                ))}
              </div>
              <div className="question-nav">
                <button className="btn btn-small" onClick={() => setCurrentQ(Math.max(0, currentQ - 1))} disabled={currentQ === 0}><Icon name="arrow-left" size={14} /> Previous</button>
                {currentQ < activeInstrument.questions.length - 1 ? (
                  <button className="btn btn-small" onClick={() => setCurrentQ(currentQ + 1)} disabled={!responses[q.id]}>Next <Icon name="arrow-right" size={14} /></button>
                ) : (
                  <button className="btn btn-primary" onClick={submitAssessment} disabled={!allAnswered || submitting}>
                    {submitting ? "Scoring..." : "Submit Assessment"}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Assessment result */}
      {result && (
        <div className="card assessment-result" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <div>
              <div className="card-title title-with-icon"><Icon name={instrumentIconName(result.instrument_type)} size={18} /> {result.instrument_name} — Results</div>
              <div className="card-subtitle">{result.interpretation}</div>
            </div>
            <span className="status-badge" style={{ background: `${severityColor(result.severity)}22`, color: severityColor(result.severity) }}>
              {result.severity.toUpperCase()}
            </span>
          </div>

          <div className="result-overview">
            <div className="result-score">
              <div className="score-circle" style={{ borderColor: severityColor(result.severity) }}>
                {(result.normalized_score * 100).toFixed(0)}
              </div>
              <span>Overall Score</span>
            </div>
            <div className="result-recommendation">
              <strong>Recommendation</strong>
              <p>{result.recommendation}</p>
            </div>
          </div>

          <div className="subscale-grid">
            {result.subscale_scores.map(sub => (
              <div key={sub.name} className="subscale-item">
                <div className="subscale-header">
                  <span>{sub.name.replace(/_/g, " ")}</span>
                  <strong>{(sub.normalized * 100).toFixed(0)}%</strong>
                </div>
                <div className="metric-bar">
                  <div className="metric-bar-fill" style={{
                    width: `${sub.normalized * 100}%`,
                    background: sub.normalized > 0.7 ? "var(--gradient-danger)" :
                                sub.normalized > 0.4 ? "var(--accent-warning)" : "var(--gradient-success)",
                  }} />
                </div>
              </div>
            ))}
          </div>

          <button className="btn title-with-icon" onClick={() => { setActiveInstrument(null); setResult(null); }} style={{ marginTop: 16 }}>
            <Icon name="arrow-left" size={14} /> Back to Instruments
          </button>
        </div>
      )}

      {/* Instrument catalog + Wellbeing + History (only when not actively taking one) */}
      {!activeInstrument && (
        <>
          {/* Wellbeing snapshot */}
          {wellbeing && (
            <div className="card" style={{ marginBottom: 24 }}>
              <div className="card-header">
                <div className="card-title">Composite Wellbeing</div>
                <span className="status-badge active">
                  <span className="status-dot" />
                  {(wellbeing.composite_wellbeing * 100).toFixed(0)}%
                </span>
              </div>
              <div className="wellbeing-grid">
                {wellbeing.sensor_stress !== null && (
                  <div><span>Sensor Stress</span><strong>{(wellbeing.sensor_stress * 100).toFixed(0)}%</strong></div>
                )}
                {wellbeing.self_report_stress !== null && (
                  <div><span>Self-Report Stress</span><strong>{(wellbeing.self_report_stress * 100).toFixed(0)}%</strong></div>
                )}
                {wellbeing.calibration_delta !== null && (
                  <div><span>Calibration Δ</span><strong style={{ color: Math.abs(wellbeing.calibration_delta) > 0.2 ? "var(--accent-warning)" : "var(--accent-success)" }}>
                    {wellbeing.calibration_delta > 0 ? "+" : ""}{(wellbeing.calibration_delta * 100).toFixed(0)}%
                  </strong></div>
                )}
                {wellbeing.self_report_energy !== null && (
                  <div><span>Energy</span><strong>{(wellbeing.self_report_energy * 100).toFixed(0)}%</strong></div>
                )}
                {wellbeing.self_report_flow !== null && (
                  <div><span>Flow</span><strong>{(wellbeing.self_report_flow * 100).toFixed(0)}%</strong></div>
                )}
                {wellbeing.self_report_burnout !== null && (
                  <div><span>Burnout Risk</span><strong>{(wellbeing.self_report_burnout * 100).toFixed(0)}%</strong></div>
                )}
              </div>
            </div>
          )}

          <div className="dashboard-grid">
            {/* Instrument catalog */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Available Assessments</div>
              </div>
              <div className="instrument-list">
                {instruments.map(inst => (
                  <button key={inst.type} className="instrument-item" onClick={() => startAssessment(inst.type)} disabled={!userId}>
                    <div className="instrument-emoji"><Icon name={instrumentIconName(inst.type)} size={20} /></div>
                    <div className="instrument-info">
                      <div className="instrument-name">{inst.name}</div>
                      <div className="instrument-desc">{inst.description}</div>
                      <div className="instrument-meta">
                        {inst.question_count} questions · ~{inst.estimated_seconds}s
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Assessment history */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Recent Assessments</div>
              </div>
              {history.length > 0 ? (
                <div className="assessment-history-list">
                  {history.map((r, i) => (
                    <div key={i} className="history-item">
                      <span className="history-emoji"><Icon name={instrumentIconName(r.instrument_type)} size={18} /></span>
                      <div className="history-info">
                        <div className="history-name">{r.instrument_name}</div>
                        <div className="history-time">{new Date(r.completed_at).toLocaleDateString()} {new Date(r.completed_at).toLocaleTimeString()}</div>
                      </div>
                      <div className="history-score">
                        <strong style={{ color: severityColor(r.severity) }}>{(r.normalized_score * 100).toFixed(0)}%</strong>
                        <span className="history-severity" style={{ color: severityColor(r.severity) }}>{r.severity}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="icon"><Icon name="assessments" size={26} /></div>
                  <p>No assessments taken yet</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
