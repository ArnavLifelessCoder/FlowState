"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────

interface Snapshot {
  session_id: string;
  cognitive_load: number;
  frustration_score: number;
  attention_level: number;
  recommended_adaptation: string;
  sample_size: number;
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
  type: "session" | "behavior" | "notification" | "auth";
  text: string;
  time: Date;
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
          <div className="logo">🧠</div>
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

// ── Main Dashboard ───────────────────────────────────────────────

export default function Home() {
  const [userId, setUserId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("User");
  const [page, setPage] = useState("dashboard");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const trackerRef = useRef<number | null>(null);

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

  // Behavior tracker - sends keypress events while a session is active
  useEffect(() => {
    if (!activeSession) return;
    let eventCount = 0;

    const handleKey = (e: KeyboardEvent) => {
      eventCount++;
      api.sendBehaviorEvent(activeSession, {
        type: "keypress",
        timestamp: performance.now() / 1000,
        metadata: { key: e.key, is_backspace: e.key === "Backspace" },
      }).then((data: Snapshot) => {
        if (data?.session_id) setSnapshot(data);
      });
    };

    const handleMouse = (e: MouseEvent) => {
      api.sendBehaviorEvent(activeSession, {
        type: "mouse_move",
        timestamp: performance.now() / 1000,
        metadata: { x: e.clientX, y: e.clientY },
      }).then((data: Snapshot) => {
        if (data?.session_id) setSnapshot(data);
      });
    };

    document.addEventListener("keydown", handleKey);
    const mouseThrottle = setInterval(() => {}, 200);
    document.addEventListener("mousemove", handleMouse);

    // Auto-send events every 2s to keep metrics flowing
    trackerRef.current = window.setInterval(() => {
      api.sendBehaviorEvent(activeSession, {
        type: "keypress",
        timestamp: performance.now() / 1000,
        metadata: { key: "auto", is_backspace: false },
      }).then((data: Snapshot) => {
        if (data?.session_id) setSnapshot(data);
      });
    }, 2000);

    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousemove", handleMouse);
      clearInterval(mouseThrottle);
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
    setSessions(prev => [data, ...prev]);
    addActivity("session", `Started session ${data.session_id.slice(0, 8)}...`);
  };

  const handleEndSession = async () => {
    if (!activeSession) return;
    await api.endSession(activeSession);
    addActivity("session", `Ended session ${activeSession.slice(0, 8)}...`);
    setActiveSession(null);
    setSnapshot(null);
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
    setSessions([]);
  };

  // If not logged in
  if (!userId) {
    return <AuthPage onLogin={handleLogin} />;
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">🧠</div>
          <h1>FlowState</h1>
        </div>
        <nav className="sidebar-nav">
          <button className={`nav-item ${page === "dashboard" ? "active" : ""}`} onClick={() => setPage("dashboard")}>
            <span className="icon">📊</span> Dashboard
          </button>
          <button className={`nav-item ${page === "sessions" ? "active" : ""}`} onClick={() => setPage("sessions")}>
            <span className="icon">⏱️</span> Sessions
          </button>
          <button className={`nav-item ${page === "notifications" ? "active" : ""}`} onClick={() => setPage("notifications")}>
            <span className="icon">🔔</span> Notifications
          </button>
          <button className={`nav-item ${page === "teams" ? "active" : ""}`} onClick={() => setPage("teams")}>
            <span className="icon">👥</span> Team Analytics
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="user-badge">
            <div className="user-avatar">{displayName[0]?.toUpperCase()}</div>
            <div className="user-info">
              <div className="name">{displayName}</div>
              <div className="role">Developer</div>
            </div>
            <button className="btn-icon" onClick={handleLogout} title="Sign out">🚪</button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        {page === "dashboard" && (
          <DashboardPage
            snapshot={snapshot} activeSession={activeSession} sessions={sessions}
            activity={activity} backendOnline={backendOnline}
            onStartSession={handleStartSession} onEndSession={handleEndSession}
          />
        )}
        {page === "sessions" && <SessionsPage sessions={sessions} activeSession={activeSession} />}
        {page === "notifications" && <NotificationsPage activeSession={activeSession} addActivity={addActivity} />}
        {page === "teams" && <TeamsPage userId={userId} />}
      </main>
    </div>
  );
}

// ── Dashboard Page ───────────────────────────────────────────────

function DashboardPage({ snapshot, activeSession, sessions, activity, backendOnline, onStartSession, onEndSession }: {
  snapshot: Snapshot | null; activeSession: string | null; sessions: Session[];
  activity: ActivityItem[]; backendOnline: boolean;
  onStartSession: () => void; onEndSession: () => void;
}) {
  const cog = snapshot?.cognitive_load ?? 0;
  const frust = snapshot?.frustration_score ?? 0;
  const att = snapshot?.attention_level ?? 0;

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>Real-time cognitive and emotional monitoring</p>
        </div>
        <div className="header-actions">
          {backendOnline && (
            <div className="live-indicator"><div className="live-dot" /> LIVE</div>
          )}
          {activeSession ? (
            <button className="btn btn-danger" onClick={onEndSession}>⏹ End Session</button>
          ) : (
            <button className="btn btn-primary" onClick={onStartSession}>▶ Start Session</button>
          )}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card cognitive">
          <span className="metric-label">Cognitive Load</span>
          <span className="metric-value cognitive">{(cog * 100).toFixed(0)}%</span>
          <div className="metric-bar"><div className="metric-bar-fill cognitive" style={{ width: `${cog * 100}%` }} /></div>
        </div>
        <div className="metric-card frustration">
          <span className="metric-label">Frustration</span>
          <span className="metric-value frustration">{(frust * 100).toFixed(0)}%</span>
          <div className="metric-bar"><div className="metric-bar-fill frustration" style={{ width: `${frust * 100}%` }} /></div>
        </div>
        <div className="metric-card attention">
          <span className="metric-label">Attention</span>
          <span className="metric-value attention">{(att * 100).toFixed(0)}%</span>
          <div className="metric-bar"><div className="metric-bar-fill attention" style={{ width: `${att * 100}%` }} /></div>
        </div>
        <div className="metric-card sessions">
          <span className="metric-label">Total Sessions</span>
          <span className="metric-value sessions">{sessions.length}</span>
          <div className="metric-bar"><div className="metric-bar-fill" style={{ width: `${Math.min(sessions.length * 10, 100)}%`, background: "var(--accent-warning)" }} /></div>
        </div>
      </div>

      {/* Gauges + Activity */}
      <div className="dashboard-grid">
        <div className="card">
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

        <div className="card">
          <div className="card-header">
            <div className="card-title">Activity Feed</div>
          </div>
          <div className="activity-feed">
            {activity.length === 0 ? (
              <div className="empty-state"><div className="icon">📭</div><p>No activity yet</p></div>
            ) : activity.map(item => (
              <div key={item.id} className="activity-item">
                <div className={`activity-icon ${item.type}`}>
                  {item.type === "session" ? "⏱️" : item.type === "notification" ? "🔔" : item.type === "auth" ? "🔑" : "📊"}
                </div>
                <div>
                  <div className="activity-text" dangerouslySetInnerHTML={{ __html: item.text }} />
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
            <div style={{ fontSize: 40 }}>
              {snapshot?.recommended_adaptation === "reduce_ui_complexity" ? "🔽" :
               snapshot?.recommended_adaptation === "suggest_break" ? "☕" :
               snapshot?.recommended_adaptation === "enable_focus_mode" ? "🎯" :
               snapshot?.recommended_adaptation === "pause_notifications" ? "🔕" : "✅"}
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>
                {snapshot?.recommended_adaptation?.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) || "No Recommendation"}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                {snapshot ? `Based on ${snapshot.sample_size} behavior samples` : "Start a session and type or move your mouse to generate recommendations"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Sessions Page ────────────────────────────────────────────────

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
    addActivity("notification", `Notification "${title}" → <strong>${data.decision}</strong>`);
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
            <div className="empty-state"><div className="icon">⚠️</div><p>Start a session first from Dashboard</p></div>
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
              <div style={{ fontSize: 56, marginBottom: 12 }}>
                {result.decision === "deliver" ? "✅" : result.decision === "queue" ? "⏳" : "🚫"}
              </div>
              <span className={`status-badge ${result.decision}`} style={{ fontSize: 16, padding: "8px 24px" }}>
                {result.decision.toUpperCase()}
              </span>
              <p style={{ marginTop: 16, fontSize: 13, color: "var(--text-secondary)" }}>{result.reason}</p>
            </div>
          ) : (
            <div className="empty-state"><div className="icon">🔔</div><p>Send a test notification</p></div>
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
            <div className="empty-state"><div className="icon">👥</div><p>Create or load a team</p></div>
          )}
        </div>
      </div>
    </>
  );
}
