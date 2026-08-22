export const API_BASE_URL = typeof window !== 'undefined' 
  ? `${window.location.protocol}//${window.location.hostname}:4000/api` 
  : "http://localhost:4000/api";


let currentToken: string | null = null;

export async function getAuthToken(): Promise<string> {
  if (typeof window !== "undefined" && (window as any).Clerk?.session) {
    const token = await (window as any).Clerk.session.getToken();
    if (token) return token;
  }
  
  // Fallback if not authenticated via Clerk yet
  const fallback = typeof window !== "undefined" ? localStorage.getItem("chief_token") : null;
  if (fallback) return fallback;

  throw new Error("No Clerk session found. User must be signed in.");
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
  console.log(`[API_BOUNDARY_DIAGNOSTIC] FRONTEND -> POST /goals: "${task_description}"`);
  const res = await apiFetch("/goals", {
    method: "POST",
    body: JSON.stringify({
      task_description,
      context: {}
    })
  });
  console.log(`[API_BOUNDARY_DIAGNOSTIC] FRONTEND <- POST /goals result:`, res);
  return res;
}

export async function fetchGoalStatus(goalId: string) {
  console.log(`[API_BOUNDARY_DIAGNOSTIC] FRONTEND -> GET /goals/${goalId}`);
  const res = await apiFetch(`/goals/${goalId}`);
  console.log(`[API_BOUNDARY_DIAGNOSTIC] FRONTEND <- GET /goals/${goalId} result:`, res);
  return res;
}

export async function decideApproval(approvalId: string, decision: "approve" | "reject") {
  return apiFetch(`/approvals/${approvalId}/decide`, {
    method: "POST",
    body: JSON.stringify({ status: decision === "approve" ? "approved" : "rejected" })
  });
}
