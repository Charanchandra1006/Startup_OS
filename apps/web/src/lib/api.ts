export const API_BASE_URL = "http://localhost:3000/api";
export const DEV_TOKEN_URL = "http://localhost:3000/dev/token";

let currentToken: string | null = null;

/**
 * Helper to get the dev token (mocking real auth for now).
 * In production, this would be handled by Auth0/Clerk middleware.
 */
export async function getAuthToken(): Promise<string> {
  if (currentToken) return currentToken;

  const res = await fetch(DEV_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_id: "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", // Matches the Demo Company SQL seed
      user_id: "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22",
      role: "founder"
    })
  });

  if (!res.ok) {
    throw new Error("Failed to fetch dev token");
  }
  
  const data = await res.json();
  currentToken = data.token;
  return currentToken!;
}

/**
 * Generic fetch wrapper that injects the auth token.
 */
async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  const headers = {
    ...options.headers,
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  };

  const res = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
  if (!res.ok) {
    throw new Error(`API call failed: ${res.statusText}`);
  }
  return res.json();
}

// ─── Domain Methods ──────────────────────────────────────────────────────────

export async function fetchMetrics() {
  return apiFetch("/metrics");
}

export async function fetchInsights() {
  return apiFetch("/insights");
}

export async function fetchApprovals() {
  return apiFetch("/approvals");
}

export async function submitGoal(task_description: string) {
  return apiFetch("/goals", {
    method: "POST",
    body: JSON.stringify({
      id: crypto.randomUUID(),
      task_description,
      context: {}
    })
  });
}

export async function decideApproval(approvalId: string, decision: "approve" | "reject") {
  return apiFetch(`/approvals/${approvalId}/decide`, {
    method: "POST",
    body: JSON.stringify({ status: decision === "approve" ? "approved" : "rejected" })
  });
}
