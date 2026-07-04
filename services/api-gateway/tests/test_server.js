/**
 * Tests for API Gateway
 * Uses Node.js built-in test runner (no external test framework needed for Phase 0)
 */

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const jwt = require('jsonwebtoken');

const app = require('../src/server');

const PORT = 3099;
const JWT_SECRET = process.env.JWT_SECRET || 'changeme_jwt_secret';
const JWT_ISSUER = process.env.JWT_ISSUER || 'chief-dev';

let server;

function makeToken(overrides = {}) {
  const payload = {
    sub: 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    tenant_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    role: 'founder',
    ...overrides,
  };
  return jwt.sign(payload, JWT_SECRET, { issuer: JWT_ISSUER, expiresIn: '1h' });
}

function request(method, path, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: PORT,
      path,
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: JSON.parse(data), headers: res.headers });
        } catch {
          resolve({ status: res.statusCode, body: data, headers: res.headers });
        }
      });
    });

    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

before(() => {
  return new Promise((resolve) => {
    server = app.listen(PORT, resolve);
  });
});

after(() => {
  return new Promise((resolve) => {
    server.close(resolve);
  });
});

describe('Health Check', () => {
  it('returns ok without auth', async () => {
    const res = await request('GET', '/health');
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.status, 'ok');
  });
});

describe('Authentication', () => {
  it('rejects requests without token', async () => {
    const res = await request('POST', '/api/goals', { text: 'test' });
    assert.strictEqual(res.status, 401);
  });

  it('rejects requests with invalid token', async () => {
    const res = await request('POST', '/api/goals', { text: 'test' }, {
      Authorization: 'Bearer invalid-token',
    });
    assert.strictEqual(res.status, 401);
  });

  it('accepts requests with valid token', async () => {
    const token = makeToken();
    const res = await request('POST', '/api/goals', { text: 'test goal' }, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.tenant_id, 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
  });

  it('rejects token without tenant_id', async () => {
    const token = jwt.sign({ sub: 'user1' }, JWT_SECRET, { issuer: JWT_ISSUER });
    const res = await request('POST', '/api/goals', { text: 'test' }, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 401);
    assert.ok(res.body.error.includes('tenant_id'));
  });
});

describe('Trace ID', () => {
  it('generates trace_id if not provided', async () => {
    const res = await request('GET', '/health');
    assert.ok(res.headers['x-trace-id']);
  });

  it('uses provided trace_id', async () => {
    const res = await request('GET', '/health', null, {
      'X-Trace-Id': 'custom-trace-123',
    });
    assert.strictEqual(res.headers['x-trace-id'], 'custom-trace-123');
  });
});

describe('Routes', () => {
  it('POST /api/goals', async () => {
    const token = makeToken();
    const res = await request('POST', '/api/goals', { text: 'Financial report' }, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 200);
    assert.ok(res.body.trace_id);
  });

  it('GET /api/approvals', async () => {
    const token = makeToken();
    const res = await request('GET', '/api/approvals', null, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 200);
  });

  it('GET /api/insights', async () => {
    const token = makeToken();
    const res = await request('GET', '/api/insights', null, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 200);
  });

  it('GET /api/audit-log', async () => {
    const token = makeToken();
    const res = await request('GET', '/api/audit-log', null, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 200);
  });

  it('returns 404 for unknown routes', async () => {
    const token = makeToken();
    const res = await request('GET', '/api/nonexistent', null, {
      Authorization: `Bearer ${token}`,
    });
    assert.strictEqual(res.status, 404);
  });
});
