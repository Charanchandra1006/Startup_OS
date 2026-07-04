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

const express = require('express');
const jwt = require('jsonwebtoken');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const { v4: uuidv4 } = require('uuid');

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
app.get('/api/approvals', (req, res) => {
  res.json({
    message: 'Pending approvals — forwarding to approval workflow',
    tenant_id: req.tenantId,
    _forward_to: `${SERVICES.approvalWorkflow}/approvals?tenant_id=${req.tenantId}`,
  });
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
app.get('/api/insights', (req, res) => {
  res.json({
    message: 'Insight feed — forwarding to orchestrator',
    tenant_id: req.tenantId,
    _forward_to: `${SERVICES.orchestrator}/insights?tenant_id=${req.tenantId}`,
  });
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
