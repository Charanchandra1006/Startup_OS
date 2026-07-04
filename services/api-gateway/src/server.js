/**
 * Chief AI Startup OS — API Gateway
 * Implements: SAD §2 (API Gateway), TRD §3 (auth/rate limiting)
 *
 * The single entry point for all founder-facing API calls.
 * Responsibilities:
 * 1. JWT authentication and tenant extraction
 * 2. Rate limiting per tenant
 * 3. Request routing to backend services
 * 4. CORS, security headers (Helmet)
 * 5. Request/response logging with trace_id propagation
 */

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../../../.env') });
const express = require('express');
const jwt = require('jsonwebtoken');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const { v4: uuidv4 } = require('uuid');
const { Pool } = require('pg');
const bcrypt = require('bcryptjs');

const app = express();

// ─── Configuration ───────────────────────────────────────────────────────────

const PORT = process.env.API_GATEWAY_PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'changeme_jwt_secret';
const JWT_ISSUER = process.env.JWT_ISSUER || 'chief-dev';

// Service URLs (from K8s ConfigMap or environment)
const SERVICES = {
  orchestrator: process.env.ORCHESTRATOR_URL || 'http://localhost:8000',
  executionService: process.env.EXECUTION_SERVICE_URL || 'http://localhost:8001',
  toolGateway: process.env.TOOL_GATEWAY_URL || 'http://localhost:8002',
  approvalWorkflow: process.env.APPROVAL_WORKFLOW_URL || 'http://localhost:8003',
};

// PostgreSQL Pool for Neon (Phase 3 Migration)
let dbUrl = process.env.DATABASE_URL;
if (dbUrl) {
  dbUrl = dbUrl.replace('postgresql+asyncpg://', 'postgresql://');
  // Strip all query parameters to prevent conflicts with the ssl object below
  if (dbUrl.includes('?')) {
    dbUrl = dbUrl.split('?')[0];
  }
}

const dbPool = new Pool({
  connectionString: dbUrl,
  ssl: {
    rejectUnauthorized: false // Required for most Neon/cloud setups in Node.js
  }
});

dbPool.on('error', (err, client) => {
  console.error('Unexpected error on idle client', err);
});

// ─── Middleware ──────────────────────────────────────────────────────────────

// Security headers
app.use(helmet());

// CORS
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3001',
  credentials: true,
}));

// Body parsing
app.use(express.json({ limit: '1mb' }));

// Trace ID injection — every request gets a unique trace ID
app.use((req, res, next) => {
  req.traceId = req.headers['x-trace-id'] || uuidv4();
  res.setHeader('X-Trace-Id', req.traceId);
  next();
});

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      method: req.method,
      path: req.path,
      status: res.statusCode,
      duration_ms: duration,
      trace_id: req.traceId,
      tenant_id: req.tenantId || null,
      user_id: req.userId || null,
    }));
  });
  next();
});

// ─── Rate Limiting (per-tenant) ──────────────────────────────────────────────

// Global rate limit: 100 requests per minute per IP
const globalLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests. Please try again later.' },
  keyGenerator: (req) => req.tenantId || req.ip,
});

// Goal submission rate limit: 10 goals per minute per tenant
const goalLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  message: { error: 'Goal submission rate limit exceeded.' },
  keyGenerator: (req) => req.tenantId || req.ip,
});

app.use(globalLimiter);

// ─── JWT Authentication ──────────────────────────────────────────────────────

/**
 * JWT middleware: validates token and extracts tenant_id + user_id.
 * Every authenticated request has req.tenantId and req.userId set.
 *
 * Token payload must contain:
 * - sub: user ID
 * - tenant_id: tenant UUID
 * - role: user role (founder, co_founder, admin, viewer)
 */
function authenticateJWT(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid Authorization header' });
  }

  const token = authHeader.split(' ')[1];

  try {
    const payload = jwt.verify(token, JWT_SECRET, { issuer: JWT_ISSUER });
    req.userId = payload.sub;
    req.tenantId = payload.tenant_id;
    req.userRole = payload.role || 'viewer';

    if (!req.tenantId) {
      return res.status(401).json({ error: 'Token missing tenant_id claim' });
    }

    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expired' });
    }
    return res.status(401).json({ error: 'Invalid token' });
  }
}

// ─── Health Check (unauthenticated) ──────────────────────────────────────────

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'api-gateway', timestamp: new Date().toISOString() });
});

// ─── Dev Token Generator (Phase 0 only — remove in production) ───────────────

app.post('/dev/token', (req, res) => {
  if (process.env.ENVIRONMENT !== 'development') {
    return res.status(404).json({ error: 'Not found' });
  }

  const {
    tenant_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    user_id = 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    role = 'founder',
  } = req.body;

  const token = jwt.sign(
    { sub: user_id, tenant_id, role },
    JWT_SECRET,
    { issuer: JWT_ISSUER, expiresIn: '24h' }
  );

  res.json({ token, expires_in: '24h' });
});

// --- Phase 2 Pitch Demo (SSE Stream) ---
// Note: Placed above authenticateJWT because EventSource does not support Auth headers
app.get('/api/demo/series-a', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });

  const sendEvent = (event, data) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  let step = 0;
  
  // Scripted Demo Sequence
  const sequence = [
    // Step 0: Dispatch agents
    () => sendEvent('agents_dispatched', {
      agents: ['Finance Agent', 'Hiring Agent', 'Legal Agent', 'Marketing Agent', 'Engineering Agent']
    }),
    
    // Step 1: Agents processing
    () => sendEvent('agents_processing', {
      completed: ['Legal Agent', 'Marketing Agent', 'Engineering Agent'],
      running: ['Finance Agent', 'Hiring Agent']
    }),

    // Step 2: Conflict Detected
    () => sendEvent('conflict_detected', {
      agent_a: { name: 'Finance Agent', claim: 'Budget allows only 2 hires.' },
      agent_b: { name: 'Hiring Agent', claim: 'Product roadmap needs 5 engineers.' }
    }),

    // Step 3: Conflict Resolved & Report Generated
    () => sendEvent('report_generated', {
      resolution: 'Hire 2 senior engineers now and postpone 3 junior hires until revenue reaches the next milestone.',
      report: {
        financial_health: { status: 'Stable', color: 'green' },
        hiring: { status: 'Understaffed', color: 'yellow' },
        engineering: { status: 'On Track', color: 'green' },
        legal: { status: 'No Issues', color: 'green' },
        risk_score: 'Medium',
        top_recommendation: 'Delay non-critical hiring by 30 days to extend runway by 4.2 months.'
      }
    })
  ];

  const timer = setInterval(() => {
    if (step < sequence.length) {
      sequence[step]();
      step++;
    } else {
      clearInterval(timer);
      res.end();
    }
  }, 2500); // 2.5 second delay between steps to build suspense

  req.on('close', () => {
    clearInterval(timer);
  });
});

// --- Direct Auth (Email/Password) ---
app.post('/api/auth/register', async (req, res) => {
  const { name, company_name, email, password } = req.body;
  if (!name || !company_name || !email || !password) {
    return res.status(400).json({ error: 'All fields are required.' });
  }

  try {
    const existing = await dbPool.query('SELECT id FROM users WHERE email = $1', [email]);
    if (existing.rows.length > 0) {
      return res.status(409).json({ error: 'Email already exists.' });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    
    // Create new tenant
    const tenantRes = await dbPool.query(
      'INSERT INTO tenants (name) VALUES ($1) RETURNING id',
      [company_name]
    );
    const tenantId = tenantRes.rows[0].id;

    // Create user
    const userRes = await dbPool.query(
      `INSERT INTO users (tenant_id, email, name, role, password_hash)
       VALUES ($1, $2, $3, 'founder', $4) RETURNING id`,
      [tenantId, email, name, passwordHash]
    );
    const userId = userRes.rows[0].id;

    const token = jwt.sign(
      { sub: userId, tenant_id: tenantId, role: 'founder' },
      JWT_SECRET,
      { issuer: JWT_ISSUER, expiresIn: '24h' }
    );

    res.json({ token, user: { id: userId, name, email } });
  } catch (err) {
    console.error('Registration Error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required.' });
  }

  try {
    const userRes = await dbPool.query('SELECT id, tenant_id, name, role, password_hash FROM users WHERE email = $1', [email]);
    if (userRes.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials.' });
    }

    const user = userRes.rows[0];
    if (!user.password_hash) {
      return res.status(401).json({ error: 'Please login with Google.' });
    }

    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) {
      return res.status(401).json({ error: 'Invalid credentials.' });
    }

    const token = jwt.sign(
      { sub: user.id, tenant_id: user.tenant_id, role: user.role },
      JWT_SECRET,
      { issuer: JWT_ISSUER, expiresIn: '24h' }
    );

    res.json({ token, user: { id: user.id, name: user.name, email } });
  } catch (err) {
    console.error('Login Error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// --- Google OAuth (Phase 1) ---
// Placed above authenticateJWT because browser redirects don't send Auth headers
app.get('/api/auth/google/login', (req, res) => {
  const tenantId = req.query.tenant_id;
  if (!tenantId) {
    return res.status(400).send("tenant_id is required");
  }
  res.redirect(`${SERVICES.toolGateway}/auth/google/login?tenant_id=${tenantId}`);
});

app.get('/api/auth/google/callback', (req, res) => {
  const state = req.query.state;
  const code = req.query.code;
  if (!state || !code) {
    return res.status(400).send("Invalid callback parameters");
  }
  res.redirect(`${SERVICES.toolGateway}/auth/google/callback?state=${state}&code=${code}`);
});

// ─── Authenticated Routes ────────────────────────────────────────────────────

// All routes below this line require JWT authentication
app.use('/api', authenticateJWT);

// --- Goals ---
app.post('/api/goals', goalLimiter, (req, res) => {
  // Forward to Orchestrator with tenant context headers
  const headers = {
    'X-Tenant-Id': req.tenantId,
    'X-User-Id': req.userId,
    'X-Trace-Id': req.traceId,
    'Content-Type': 'application/json',
  };

  // In production: proxy to orchestrator service
  // Phase 0: echo back for pipeline testing
  res.json({
    message: 'Goal received — forwarding to orchestrator',
    goal: req.body,
    tenant_id: req.tenantId,
    trace_id: req.traceId,
    _forward_to: `${SERVICES.orchestrator}/goals`,
  });
});

app.get('/api/goals/:goalId', (req, res) => {
  res.json({
    message: 'Goal status — forwarding to orchestrator',
    goal_id: req.params.goalId,
    tenant_id: req.tenantId,
    _forward_to: `${SERVICES.orchestrator}/goals/${req.params.goalId}`,
  });
});

// --- Approvals ---
app.get('/api/approvals', async (req, res) => {
  try {
    const result = await dbPool.query(
      "SELECT id, action_type, risk_tier, rationale, diff_preview, created_at FROM approval_requests WHERE tenant_id = $1 AND status = 'pending' ORDER BY created_at DESC",
      [req.tenantId]
    );
    res.json(result.rows);
  } catch (error) {
    console.error('DB Error fetching approvals:', error);
    res.status(500).json({ error: 'Database error fetching approvals' });
  }
});

app.post('/api/approvals/:approvalId/decide', (req, res) => {
  res.json({
    message: 'Approval decision — forwarding to execution service',
    approval_id: req.params.approvalId,
    decision: req.body,
    tenant_id: req.tenantId,
    _forward_to: `${SERVICES.executionService}/approvals/${req.params.approvalId}/decide`,
  });
});

// --- Insights Feed ---
app.get('/api/insights', async (req, res) => {
  try {
    const result = await dbPool.query(
      "SELECT id, domain as category, title, detail as content, urgency as severity, created_at as time FROM insights WHERE tenant_id = $1 ORDER BY created_at DESC",
      [req.tenantId]
    );
    // Format timestamp for UI (basic approximation)
    const formattedRows = result.rows.map(row => ({
      ...row,
      time: new Date(row.time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
    }));
    res.json(formattedRows);
  } catch (error) {
    console.error('DB Error fetching insights:', error);
    res.status(500).json({ error: 'Database error fetching insights' });
  }
});

// --- Integrations ---
app.get('/api/integrations', (req, res) => {
  res.json({
    message: 'Integration list — forwarding to tool gateway',
    tenant_id: req.tenantId,
    _forward_to: `${SERVICES.toolGateway}/integrations?tenant_id=${req.tenantId}`,
  });
});

// --- Audit Log ---
app.get('/api/audit-log', (req, res) => {
  res.json({
    message: 'Audit log — forwarding to execution service',
    tenant_id: req.tenantId,
    _forward_to: `${SERVICES.executionService}/audit-log?tenant_id=${req.tenantId}`,
  });
});

// --- Metrics ---
app.get('/api/metrics', async (req, res) => {
  try {
    const result = await dbPool.query(
      "SELECT health_score, revenue_growth_pct, runway_months, critical_risks, decisions_waiting, est_decision_time_mins FROM tenant_metrics WHERE tenant_id = $1",
      [req.tenantId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Metrics not found for tenant' });
    }
    res.json(result.rows[0]);
  } catch (error) {
    console.error('DB Error fetching metrics:', error);
    res.status(500).json({ error: 'Database error fetching metrics' });
  }
});



// ─── 404 Handler ─────────────────────────────────────────────────────────────

app.use((req, res) => {
  res.status(404).json({ error: 'Not found', path: req.path });
});

// ─── Error Handler ───────────────────────────────────────────────────────────

app.use((err, req, res, next) => {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    error: err.message,
    stack: err.stack,
    trace_id: req.traceId,
  }));
  res.status(500).json({ error: 'Internal server error', trace_id: req.traceId });
});

// ─── Start ───────────────────────────────────────────────────────────────────

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Chief API Gateway listening on port ${PORT}`);
    console.log(`Environment: ${process.env.ENVIRONMENT || 'development'}`);
  });
}

module.exports = app;
