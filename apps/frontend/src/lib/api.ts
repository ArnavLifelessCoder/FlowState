const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

class FlowStateAPI {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("fs_access_token");
      this.refreshToken = localStorage.getItem("fs_refresh_token");
    }
  }

  private saveTokens(tokens: TokenPair) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (typeof window !== "undefined") {
      localStorage.setItem("fs_access_token", tokens.access_token);
      localStorage.setItem("fs_refresh_token", tokens.refresh_token);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("fs_access_token");
      localStorage.removeItem("fs_refresh_token");
    }
  }

  get isAuthenticated() {
    return !!this.accessToken;
  }

  private async request(path: string, options: RequestInit = {}) {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> || {}),
    };
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }
    const res = await fetch(`${API_BASE}/api/v1${path}`, {
      ...options,
      headers,
    });
    if (res.status === 401 && this.refreshToken) {
      const refreshed = await this.refresh();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${this.accessToken}`;
        return fetch(`${API_BASE}/api/v1${path}`, { ...options, headers });
      }
    }
    return res;
  }

  // Auth
  async register(username: string, password: string, displayName?: string) {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, display_name: displayName || username }),
    });
    return { ok: res.ok, status: res.status, data: await res.json() };
  }

  async login(username: string, password: string) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      const data: TokenPair = await res.json();
      this.saveTokens(data);
      return { ok: true, data };
    }
    return { ok: false, data: await res.json() };
  }

  async refresh(): Promise<boolean> {
    if (!this.refreshToken) return false;
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (res.ok) {
        const data: TokenPair = await res.json();
        this.saveTokens(data);
        return true;
      }
    } catch {}
    this.clearTokens();
    return false;
  }

  async getMe() {
    const res = await this.request("/auth/me");
    return res.ok ? res.json() : null;
  }

  // Sessions
  async createSession(userId: string) {
    const res = await this.request("/session", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    });
    return res.json();
  }

  async getSession(sessionId: string) {
    const res = await this.request(`/session/${sessionId}`);
    return res.ok ? res.json() : null;
  }

  async endSession(sessionId: string) {
    const res = await this.request(`/session/${sessionId}/end`, { method: "POST" });
    return res.json();
  }

  async listSessions(userId: string, activeOnly = false) {
    const q = activeOnly ? "?active_only=true" : "";
    const res = await this.request(`/session/user/${userId}${q}`);
    return res.json();
  }

  // Behavior
  async sendBehaviorEvent(sessionId: string, event: object) {
    const res = await this.request("/behavior/event", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, event }),
    });
    return res.json();
  }

  async getCurrentBehavior(sessionId: string) {
    const res = await this.request(`/behavior/current/${sessionId}`);
    if (!res.ok) {
      throw new Error(`Current behavior request failed with ${res.status}`);
    }
    return res.json();
  }

  // Notifications
  async evaluateNotification(sessionId: string, source: string, title: string, priority = "normal") {
    const res = await this.request("/notifications/evaluate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, source, title, priority }),
    });
    return res.json();
  }

  async getNotificationQueue(sessionId: string) {
    const res = await this.request(`/notifications/queue/${sessionId}`);
    return res.json();
  }

  async getNotificationStats(sessionId: string) {
    const res = await this.request(`/notifications/stats/${sessionId}`);
    return res.json();
  }

  // Adaptation
  async getAdaptationConfig(sessionId: string) {
    const res = await this.request(`/adaptation/config/${sessionId}`);
    if (!res.ok) {
      throw new Error(`Adaptation config request failed with ${res.status}`);
    }
    return res.json();
  }

  // Teams
  async createTeam(teamId: string, userIds: string[]) {
    const res = await this.request("/teams", {
      method: "POST",
      body: JSON.stringify({ team_id: teamId, user_ids: userIds }),
    });
    return res.json();
  }

  async getTeamAnalytics(teamId: string) {
    const res = await this.request(`/teams/${teamId}`);
    return { ok: res.ok, data: await res.json() };
  }

  async listTeams() {
    const res = await this.request("/teams");
    return res.json();
  }

  // Analytics
  async getEmotionHistory(sessionId: string, limit = 120) {
    const safeLimit = Math.max(1, Math.min(limit, 500));
    const res = await this.request(`/analytics/emotion-history/${sessionId}?limit=${safeLimit}`);
    if (!res.ok) {
      throw new Error(`Emotion history request failed with ${res.status}`);
    }
    return res.json();
  }

  async getSessionInsights(sessionId: string, lookback = 120) {
    const safeLookback = Math.max(1, Math.min(lookback, 500));
    const res = await this.request(`/analytics/insights/${sessionId}?lookback=${safeLookback}`);
    if (!res.ok) {
      throw new Error(`Session insights request failed with ${res.status}`);
    }
    return res.json();
  }

  async getInterventions(sessionId: string, limit = 50) {
    const safeLimit = Math.max(1, Math.min(limit, 500));
    const res = await this.request(`/adaptation/interventions/${sessionId}?limit=${safeLimit}`);
    if (!res.ok) {
      throw new Error(`Interventions request failed with ${res.status}`);
    }
    return res.json();
  }

  // Privacy
  async exportUserData(userId: string) {
    const res = await this.request(`/privacy/export/${userId}`);
    return res.json();
  }

  async deleteUserData(userId: string) {
    const res = await this.request(`/privacy/data/${userId}`, { method: "DELETE" });
    return res.json();
  }

  // Health
  async health() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  }
}

export const api = new FlowStateAPI();
export type { TokenPair };
