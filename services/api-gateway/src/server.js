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
const { clerkMiddleware, requireAuth, getAuth } = require('@clerk/express');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
const { createProxyMiddleware, fixRequestBody } = require('http-proxy-middleware');
const { v4: uuidv4 } = require('uuid');
const { Pool } = require('pg');

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

// CORS - Allow any origin dynamically for the pitch presentation
app.use(cors({
  origin: function(origin, callback) {
    callback(null, true);
  },
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

// ─── Public Health Check ─────────────────────────────────────────────────────

app.get('/health', async (req, res) => {
  try {
    // Ping DB to ensure it's alive
    await dbPool.query('SELECT 1');
    res.status(200).json({ status: 'ok', db: 'connected', service: 'api-gateway' });
  } catch (error) {
    console.error('Health Check DB Error:', error);
    res.status(503).json({ status: 'error', db: 'disconnected', service: 'api-gateway' });
  }
});

// ─── Clerk Authentication & Tenant Mapping ───────────────────────────────────

/**
 * Maps Clerk's orgId to our internal tenant_id UUID.
 */
async function mapTenantMiddleware(req, res, next) {
  const auth = getAuth(req);
  
  if (!auth || !auth.userId) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  req.userId = auth.userId;
  
  const clerkOrgId = auth.orgId;
  
  if (!clerkOrgId) {
    // If user hasn't selected an org, default to the demo tenant for now
    // In a real app, you might force them to create an org first.
    req.tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
    req.userRole = 'founder';
    return next();
  }

  try {
    const result = await dbPool.query('SELECT tenant_id FROM clerk_org_tenant_map WHERE clerk_org_id = $1', [clerkOrgId]);
    if (result.rows.length > 0) {
      req.tenantId = result.rows[0].tenant_id;
      req.userRole = auth.orgRole || 'founder';
      next();
    } else {
      // Auto-provision a tenant for this new Clerk Org
      const tenantRes = await dbPool.query('INSERT INTO tenants (name) VALUES ($1) RETURNING id', [`Org ${clerkOrgId}`]);
      const newTenantId = tenantRes.rows[0].id;
      
      await dbPool.query('INSERT INTO clerk_org_tenant_map (clerk_org_id, tenant_id) VALUES ($1, $2)', [clerkOrgId, newTenantId]);
      
      req.tenantId = newTenantId;
      req.userRole = auth.orgRole || 'founder';
      next();
    }
  } catch (err) {
    console.error('Tenant mapping error:', err);
    res.status(500).json({ error: 'Internal server error during tenant resolution' });
  }
}

// ─── Authenticated Routes ────────────────────────────────────────────────────

// Mount integration routes for syncing OAuth tokens
const integrationsRoutes = require('./routes/integrations');
app.use('/api/integrations', mapTenantMiddleware, integrationsRoutes);

// All routes below this line require Clerk authentication
app.use('/api', clerkMiddleware(), requireAuth(), mapTenantMiddleware);

// --- Goals ---
app.post('/api/goals', goalLimiter, createProxyMiddleware({
  target: SERVICES.orchestrator,
  changeOrigin: true,
  pathRewrite: {
    '^/api/goals': '/goals',
  },
  onProxyReq: (proxyReq, req, res) => {
    // Add tenant context to proxy request headers
    proxyReq.setHeader('X-Tenant-Id', req.tenantId);
    proxyReq.setHeader('X-User-Id', req.userId);
    proxyReq.setHeader('X-Trace-Id', req.traceId);
    
    // Ensure body is sent correctly since express.json() already parsed it
    fixRequestBody(proxyReq, req);
  }
}));

app.get('/api/goals/:goalId', createProxyMiddleware({
  target: SERVICES.orchestrator,
  changeOrigin: true,
  pathRewrite: {
    '^/api/goals': '/goals',
  },
  onProxyReq: (proxyReq, req, res) => {
    proxyReq.setHeader('X-Tenant-Id', req.tenantId);
    proxyReq.setHeader('X-User-Id', req.userId);
    proxyReq.setHeader('X-Trace-Id', req.traceId);
  }
}));

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

// --- Real-Time Goal Stream (SSE) — STARTUP_OS_MASTER_BUILD_PLAN Part 3.4 ---
// Replaces the duplicate mock demo SSE route that was here (lines 464-501).
// Tails the goal_events DB table for real pipeline state.
app.get('/api/goals/:goalId/stream', async (req, res) => {
  const { goalId } = req.params;
  const tenantId = req.tenantId;

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no', // Disable nginx buffering for SSE
  });

  const sendEvent = (event, data) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  // Track the last event we sent so we only send new ones
  let lastEventTime = new Date(0).toISOString();
  let closed = false;
  const TERMINAL_STATES = ['DELIVERED', 'FAILED', 'STALLED'];

  const poll = async () => {
    if (closed) return;
    try {
      const result = await dbPool.query(
        `SELECT state, detail, created_at FROM goal_events
         WHERE goal_id = $1 AND tenant_id = $2 AND created_at > $3
         ORDER BY created_at ASC`,
        [goalId, tenantId, lastEventTime]
      );

      for (const row of result.rows) {
        sendEvent('state_change', {
          state: row.state,
          detail: row.detail,
          timestamp: row.created_at,
        });
        lastEventTime = row.created_at.toISOString();

        // Close stream on terminal states
        if (TERMINAL_STATES.includes(row.state)) {
          sendEvent('stream_end', { reason: row.state });
          res.end();
          closed = true;
          return;
        }
      }
    } catch (err) {
      console.error('SSE poll error:', err.message);
      // Don't kill the stream on transient DB errors — retry next poll
    }

    if (!closed) {
      setTimeout(poll, 500); // poll every 500ms
    }
  };

  // Start polling
  poll();

  // Clean up on client disconnect
  req.on('close', () => {
    closed = true;
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
      // Fallback for new tenants who haven't had their metrics calculated by the analytics agent yet
      return res.json({
        health_score: 100,
        revenue_growth_pct: 0,
        runway_months: 12.0,
        critical_risks: 0,
        decisions_waiting: 0,
        est_decision_time_mins: 0
      });
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
