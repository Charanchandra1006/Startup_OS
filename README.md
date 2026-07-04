# Chief — AI Startup Operating System

> An AI-native operating system for early-stage companies that coordinates specialized AI agents across finance, hiring, legal, engineering, and go-to-market — surfaces risks and opportunities before the founder asks, and executes approved operational work safely.

---

## Table of Contents

1. [What Is Chief?](#1-what-is-chief)
2. [Problem Statement](#2-problem-statement)
3. [Core Architecture](#3-core-architecture)
4. [Tech Stack (Complete)](#4-tech-stack-complete)
5. [Repository Structure (Every File)](#5-repository-structure-every-file)
6. [Data Layer — Three Segregated Stores](#6-data-layer--three-segregated-stores)
7. [Agent System — Intelligence Design](#7-agent-system--intelligence-design)
8. [Trust & Safety Model — Non-Negotiables](#8-trust--safety-model--non-negotiables)
9. [Orchestrator — State Machine & Workflow](#9-orchestrator--state-machine--workflow)
10. [Execution Service — Approval Gate & Audit](#10-execution-service--approval-gate--audit)
11. [Tool/Integration Gateway](#11-toolintegration-gateway)
12. [API Gateway](#12-api-gateway)
13. [Observability & Tracing](#13-observability--tracing)
14. [Kubernetes Infrastructure](#14-kubernetes-infrastructure)
15. [Phased Development Roadmap](#15-phased-development-roadmap)
16. [Testing Strategy](#16-testing-strategy)
17. [Getting Started (Local Development)](#17-getting-started-local-development)
18. [Environment Variables (Complete Reference)](#18-environment-variables-complete-reference)
19. [Specification Documents Index](#19-specification-documents-index)
20. [Spec Gaps & Decisions Log](#20-spec-gaps--decisions-log)

---

## 1. What Is Chief?

Chief is an **AI Chief-of-Staff for startup founders**. It replaces the scattered, manual operational work founders do across finance, hiring, legal, project management, and go-to-market — and coordinates it through a system of specialized AI agents under strict safety controls.

**Chief is NOT a chatbot.** It is an operating system that:

- **Reasons across your entire business** — connecting signals from your accounting tool, ATS, CRM, project tracker, and calendar to surface risks and opportunities you wouldn't catch in isolation.
- **Decomposes complex goals** — a single natural-language request like *"Prepare my board deck for next Tuesday"* triggers the finance agent (latest runway numbers), PM agent (milestone progress), hiring agent (pipeline status), and EA agent (scheduling) in a coordinated pipeline.
- **Never acts without permission on high-stakes decisions** — a tiered approval model ensures the founder sees exactly what will happen before any external-facing or irreversible action is taken.
- **Maintains a complete audit trail** — every action the system takes is logged in an append-only, hash-chained execution log that cannot be altered or deleted even by database administrators.

### Target User

Series Seed to Series A startup founders (1–50 employees) who are currently operating without a professional COO/Chief-of-Staff and spending 10–20 hours/week on operational overhead.

### Business Model

Design Partner → Individual Plan ($199/mo estimate) → Team Plan → Enterprise.

---

## 2. Problem Statement

A seed-stage founder is simultaneously acting as CEO, CFO, Head of HR, Head of Product, and often CTO. They are:

| Pain Point | Impact |
|---|---|
| Drowning in context switches | 10–20 hrs/week on operational overhead |
| Missing financial red flags | Cash runway surprises, anomalous transactions |
| Losing candidates to slow processes | No structured hiring pipeline |
| Board prep takes days every quarter | Manual data collection from multiple systems |
| Compliance tasks slip through cracks | Legal deadlines, contractor paperwork |
| No single view of company status | Data scattered across 5–10 SaaS tools |

Chief eliminates this by providing a **single intelligent interface** that coordinates AI agents, each expert in a specific domain, under strict safety guardrails.

---

## 3. Core Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FOUNDER INTERFACE                                │
│              Next.js 14 / Tailwind CSS / React Query                 │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│   │  Goal Input   │ │ Insight Feed │ │ Approval Q   │               │
│   └──────────────┘ └──────────────┘ └──────────────┘               │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ HTTPS/WSS
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (Node.js)                          │
│  JWT Auth │ Rate Limiting │ Tenant Extraction │ Trace ID Injection   │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ Internal (K8s cluster DNS)
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Python/LangGraph)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │Classifier│→│Decomposer│→│Dispatcher│→│Synthesizer│→│ Router   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│         ▲ State Machine: RECEIVED → … → DELIVERED                    │
└───────┬───────────────────┬──────────────────────────────────────────┘
        │ dispatch          │ actions
        ▼                   ▼
┌────────────────┐  ┌────────────────────────────────────────────────┐
│ SPECIALIST     │  │           EXECUTION SERVICE (Python)           │
│ AGENTS (Python)│  │  ┌────────┐ ┌──────────┐ ┌────────────────┐  │
│                │  │  │Denylist│→│Tier Gate │→│ Approval Gate  │  │
│ AGT-FIN        │  │  │ Check  │ │(Platform)│ │ (C/D require   │  │
│ AGT-EA         │  │  └────────┘ └──────────┘ │  human OK)     │  │
│ AGT-HIR        │  │                           └───────┬────────┘  │
│ AGT-PM         │  │                                   ▼           │
│ AGT-LEG        │  │  ┌──────────────────────────────────────────┐ │
│ AGT-ECHO       │  │  │ FAIL-CLOSED AUDIT LOG (append-only)     │ │
│                │  │  │ Must succeed BEFORE action executes      │ │
│ (Each returns  │  │  │ REVOKE UPDATE, DELETE at DB role level   │ │
│  AIDD §2.2     │  │  │ Hash-chained for tamper detection        │ │
│  contract)     │  │  └──────────────────────────────────────────┘ │
└────────┬───────┘  └───────────────────────────┬────────────────────┘
         │ data reads                           │ external writes
         ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│              TOOL / INTEGRATION GATEWAY (Python/FastAPI)             │
│  MCP Interface │ Scoped Tokens │ Denylist (Defense-in-Depth)         │
│  Mock Adapters (Phase 0) → Real Adapters (Phase 1+)                  │
│  QuickBooks │ Greenhouse │ Linear │ Google Calendar │ Gmail          │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     DATA LAYER (3 Separate PostgreSQL DBs)           │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  OPERATIONAL     │  │ FINANCIAL/LEGAL  │  │ DOCUMENT/VECTOR  │     │
│  │  PostgreSQL 15   │  │ PostgreSQL 15    │  │ PostgreSQL 15    │     │
│  │                  │  │                  │  │ + pgvector       │     │
│  │  tenants         │  │ Schema-per-tenant│  │                  │     │
│  │  users           │  │ financial_txns   │  │ playbook_docs    │     │
│  │  goals           │  │ legal_documents  │  │ (embeddings)     │     │
│  │  tasks           │  │                  │  │                  │     │
│  │  agent_runs      │  │ Separate DB      │  │ IVFFlat index    │     │
│  │  recommendations │  │ credentials!     │  │ per-tenant RLS   │     │
│  │  approval_reqs   │  │ Per-tenant       │  │                  │     │
│  │  execution_log   │  │ envelope encrypt │  │                  │     │
│  │  integrations    │  │                  │  │                  │     │
│  │  tier_rules      │  │                  │  │                  │     │
│  │  insights        │  │                  │  │                  │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ CREDENTIAL VAULT │  (HashiCorp Vault / Local Dev Vault)          │
│  │ Never stored in  │  DB holds only vault references                │
│  │ any of the 3 DBs │                                                │
│  └─────────────────┘                                                │
└──────────────────────────────────────────────────────────────────────┘
```

### Information Flow (One Request)

1. **Founder** types: *"How's our runway looking? Should I be worried?"*
2. **API Gateway** validates JWT, extracts `tenant_id`, injects `trace_id`, applies rate limit.
3. **Orchestrator** receives goal → state machine begins at `RECEIVED`.
4. **Goal Classifier** determines this is `FORECASTING` with high confidence.
5. **Task Decomposer** creates 1 task: `AGT-FIN` → "Calculate runway forecast."
6. **Dispatcher** issues a short-lived scoped token via Tool Gateway, sends task to Finance Agent.
7. **Finance Agent** reads mock accounting data (Phase 0) via scoped token, reasons about it, produces an `AgentOutput` with `supporting_data` citations, `confidence: high`, and a suggested action (`schedule_meeting` with CFO advisor, Tier C).
8. **Grounding Validator** verifies every numeric claim (`$50,000`, `12 months`) resolves to a `{source_system, source_ref}` entry. Ungrounded claims are stripped.
9. **Synthesizer** combines agent outputs into a founder-facing report with `what_happened`, `why`, `impact`, `risks`, `recommendation`, `alternatives`, `confidence`, `next_actions`.
10. **Execution Service** receives the Tier C action (`schedule_meeting`). Checks denylist (pass), checks platform tier (C → requires approval), creates `ApprovalRequest`.
11. **Founder** sees the report + pending approval card in the UI. Reviews the exact content that will be sent (byte-for-byte identical preview). Clicks Approve.
12. **Execution Service** writes to the append-only `execution_log` (must succeed first — fail-closed). Then executes via Tool Gateway.
13. **Audit log** entry is hash-chained to the previous entry for tamper detection. Full trace is queryable end-to-end via `trace_id`.

---

## 4. Tech Stack (Complete)

### Frontend (Phase 1+)

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 14.x (App Router) | Founder-facing web application |
| Tailwind CSS | 3.x | Utility-first styling |
| React Query | 5.x | Server state management, caching |
| Zustand | 4.x | Client state where needed |
| TypeScript | 5.x | Type safety |

### API Gateway

| Technology | Version | Purpose |
|---|---|---|
| Node.js | 20 LTS | Runtime |
| Express | 4.18+ | HTTP framework |
| jsonwebtoken | 9.x | JWT verification |
| express-rate-limit | 7.x | Per-tenant rate limiting |
| helmet | 7.x | Security headers (CSP, HSTS, etc.) |
| http-proxy-middleware | 3.x | Request forwarding to backend services |
| cors | 2.8+ | CORS handling |

### Core Services (Python)

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime for all AI/backend services |
| FastAPI | 0.100+ | HTTP framework for Tool Gateway, agents |
| Pydantic | 2.x | Schema validation, agent I/O contracts |
| LangGraph | latest | Orchestrator state machine workflow |
| OpenAI SDK | 1.x | LLM API calls (gpt-4o, gpt-4o-mini) |
| pytest | 7.x | Test framework |
| pytest-asyncio | 0.21+ | Async test support |

### Data Layer

| Technology | Version | Purpose |
|---|---|---|
| PostgreSQL | 15 | All three data stores |
| pgvector | 0.5+ | Vector similarity search in Document Store |
| Row-Level Security (RLS) | native | Per-tenant data isolation on all tables |
| Schema-per-tenant | native PG | Financial/Legal store isolation |

### Infrastructure & DevOps

| Technology | Version | Purpose |
|---|---|---|
| Kubernetes | 1.28+ | Container orchestration, service mesh, scaling |
| Docker | 24+ | Container images |
| kubectl | 1.28+ | K8s CLI |
| minikube / kind / Docker Desktop K8s | latest | Local K8s cluster |
| Terraform | 1.5+ | Infrastructure-as-Code (staging/prod) |
| GitHub Actions | — | CI/CD pipelines |

### Observability

| Technology | Version | Purpose |
|---|---|---|
| OpenTelemetry (OTel) | 1.x | Distributed tracing SDK |
| Jaeger | latest | Trace visualization UI |
| Prometheus | latest | Metrics collection |
| Structured JSON logging | — | All services emit JSON logs |

### Secrets & Security

| Technology | Purpose |
|---|---|
| HashiCorp Vault (prod) | Credential management, envelope encryption keys |
| Local env-backed vault (dev) | Dev-time credential abstraction |
| JWT (RS256 in prod) | Authentication tokens |
| Per-tenant envelope encryption | Financial/Legal data at rest |
| Append-only audit log | Tamper-proof execution history |

---

## 5. Repository Structure (Every File)

```
d:\Startup_OS\
│
├── README.md                          # This file — complete project reference
├── SPEC-GAPS.md                       # Tracked specification gaps with defaults taken
├── .env.example                       # Environment variable template (all services)
├── .gitignore                         # Git ignore rules
│
├── docs/                              # 12 specification documents (source of truth)
│   ├── 01_PVD_Product_Vision_Document.md
│   ├── 02_PRD_Product_Requirements_Document.md
│   ├── 03_AIDD_Agent_Intelligence_Design_Document.md
│   ├── 04_SAD_Software_Architecture_Document.md
│   ├── 05_TRD_Technical_Requirements_Document.md
│   ├── 06_DDD_Database_Design_Document.md
│   ├── 07_WDD_Workflow_Design_Document.md
│   ├── 08_UXDS_UX_UI_Design_Specification.md
│   ├── 09_SGD_Security_and_Governance_Document.md
│   ├── 10_Development_Roadmap.md
│   ├── 11_Testing_Strategy.md
│   └── 12_Deployment_and_DevOps_Guide.md
│
├── packages/                          # Shared libraries used across services
│   │
│   ├── schemas/                       # JSON Schemas (schema-first design)
│   │   ├── agent-input.schema.json    # Agent input contract (AIDD §2.1)
│   │   ├── agent-output.schema.json   # Agent output contract (AIDD §2.2)
│   │   ├── tier-rules.schema.json     # Tier rules config schema
│   │   └── denylist.json              # Hard-refusal denylist (6 action types)
│   │
│   ├── db/                            # Database migrations, roles, seeds
│   │   ├── migrations/
│   │   │   ├── operational/           # Operational Store (11 migrations)
│   │   │   │   ├── 001_create_tenants.sql
│   │   │   │   ├── 002_create_users.sql
│   │   │   │   ├── 003_create_goals.sql
│   │   │   │   ├── 004_create_tasks.sql
│   │   │   │   ├── 005_create_agent_runs.sql
│   │   │   │   ├── 006_create_recommendations.sql
│   │   │   │   ├── 007_create_approval_requests.sql
│   │   │   │   ├── 008_create_execution_log.sql    # APPEND-ONLY (NFR-004)
│   │   │   │   ├── 009_create_integrations.sql
│   │   │   │   ├── 010_create_tier_rules.sql       # Data-driven tiers
│   │   │   │   └── 011_create_insights.sql
│   │   │   ├── financial/             # Financial/Legal Store
│   │   │   │   └── 001_create_schema_template.sql  # Schema-per-tenant function
│   │   │   └── documents/             # Document/Vector Store
│   │   │       ├── 001_enable_pgvector.sql
│   │   │       └── 002_create_playbook_documents.sql
│   │   ├── roles/
│   │   │   ├── operational_roles.sql  # chief_app, chief_execution_writer, chief_audit_reader
│   │   │   └── financial_roles.sql    # chief_financial_app, chief_financial_audit
│   │   └── seed/
│   │       ├── seed_tier_rules.sql    # All tiers A-D + 6 denylist entries
│   │       └── seed_dev_tenant.sql    # Dev tenant + founder user
│   │
│   └── shared-types/                  # Shared Python types (used by ALL services)
│       └── python/
│           ├── chief_types/
│           │   ├── __init__.py
│           │   ├── models.py              # Pydantic models: AgentInput/Output, enums, contracts
│           │   ├── grounding_validator.py  # NFR-007: strips ungrounded claims programmatically
│           │   ├── tier_classifier.py      # GR-04: platform-level tier assignment
│           │   ├── denylist_enforcer.py    # §6.5: hard-refusal blocking (defense in depth)
│           │   └── observability.py        # TracingManager, AgentRunSpan, model call logging
│           └── tests/
│               ├── __init__.py
│               ├── test_grounding_validator.py
│               ├── test_tier_classifier.py
│               └── test_denylist_enforcer.py
│
├── services/                          # Microservices
│   │
│   ├── api-gateway/                   # Node.js API Gateway
│   │   ├── package.json
│   │   ├── src/
│   │   │   └── server.js              # Express server: JWT, rate limit, routing
│   │   └── tests/
│   │       └── test_server.js
│   │
│   ├── orchestrator/                  # Python — Central coordination engine
│   │   ├── orchestrator.py            # State machine, classifier, decomposer, synthesizer
│   │   ├── dispatcher.py              # Parallel/sequential task dispatch with timeouts
│   │   ├── model_router.py            # Frontier/Standard model selection
│   │   └── tests/
│   │       └── test_orchestrator.py
│   │
│   ├── execution-service/             # Python — Sole holder of external write credentials
│   │   ├── execution_service.py       # Fail-closed audit, approval gate, tier override
│   │   └── tests/
│   │       └── test_execution_service.py
│   │
│   ├── tool-gateway/                  # Python/FastAPI — Integration proxy
│   │   ├── tool_gateway.py            # Scoped tokens, denylist, mock adapters
│   │   ├── adapters/                  # Integration adapter implementations
│   │   └── tests/
│   │       └── test_tool_gateway.py
│   │
│   ├── approval-workflow/             # Python — Approval request lifecycle
│   │   ├── approval_workflow.py       # Create, decide, expire, audit history
│   │   └── tests/
│   │       └── test_approval_workflow.py
│   │
│   ├── agent-echo/                    # Python — Phase 0 test agent
│   │   ├── agent_echo.py              # Produces cited output + Tier C action for E2E test
│   │   └── tests/
│   │
│   ├── agent-ea/                      # (Placeholder) Executive Assistant agent
│   ├── agent-finance/                 # (Placeholder) Finance agent
│   ├── agent-hiring/                  # (Placeholder) Hiring agent
│   ├── agent-project/                 # (Placeholder) Project Management agent
│   └── agent-legal/                   # (Placeholder) Legal agent
│
├── infra/                             # Infrastructure-as-Code
│   ├── kubernetes/
│   │   ├── namespaces.yaml            # chief-system namespace
│   │   ├── config.yaml                # ConfigMap + Secrets
│   │   └── databases/
│   │       ├── operational-db.yaml    # StatefulSet: PostgreSQL 15
│   │       ├── financial-db.yaml      # StatefulSet: PostgreSQL 15 (SEPARATE credentials)
│   │       └── documents-db.yaml      # StatefulSet: pgvector/pgvector:pg15
│   ├── docker/                        # Dockerfiles for each service
│   └── terraform/                     # IaC for cloud deployment (staging/prod)
│
├── tests/
│   ├── e2e/
│   │   └── test_phase0_exit.py        # Phase 0 exit criteria E2E test
│   └── isolation/                     # Multi-tenancy isolation tests
│
└── apps/
    └── web/                           # Next.js founder UI (Phase 1+)
```

---

## 6. Data Layer — Three Segregated Stores

Chief uses **three physically separate PostgreSQL databases** (not one database with a `tenant_id` filter). This is a security architecture decision: a compromised Operational service cannot access Financial/Legal data because it doesn't have the credentials.

### 6.1 Operational Store (`chief_operational`, port 5432)

**Contains:** All core platform entities.

| Table | Purpose | Key Detail |
|---|---|---|
| `tenants` | Company entities | RLS policy isolates per-tenant |
| `users` | Users within a tenant | Unique constraint on (tenant_id, email) |
| `goals` | Founder goal submissions | 4000 char limit, status enum matches state machine |
| `tasks` | Decomposed sub-tasks | `depends_on UUID[]` for dependency graph |
| `agent_runs` | Every specialist agent invocation | Full I/O stored for reproducibility |
| `recommendations` | Synthesized orchestrator output | Links to contributing agent_runs |
| `approval_requests` | Pending/resolved approval decisions | `diff_preview` is byte-identical to execution payload |
| `execution_log` | **APPEND-ONLY** audit trail | `REVOKE UPDATE, DELETE` at DB role level |
| `integrations` | Connected external services | `credential_vault_ref` — never stores actual secrets |
| `tier_rules` | Action type → risk tier mapping | Data-driven, not if/else in code |
| `tenant_auto_execute_preferences` | Per-tenant auto-execute opt-in | Only Tier A/B eligible |
| `insights` | Proactive insight feed items | Persist until dismissed |

**DB Roles:**

| Role | Permissions | Used By |
|---|---|---|
| `chief_app` | SELECT/INSERT/UPDATE/DELETE on all tables **EXCEPT** execution_log (INSERT/UPDATE/DELETE revoked) | API Gateway, Orchestrator, most services |
| `chief_execution_writer` | INSERT only on execution_log, SELECT on all | Execution Service only |
| `chief_audit_reader` | SELECT only on all tables | Audit/compliance queries |

### 6.2 Financial/Legal Store (`chief_financial`, port 5433)

**Contains:** Tier-1 critical data (financial transactions, legal documents).

**Isolation model:** Schema-per-tenant. Each tenant gets its own PostgreSQL schema (e.g., `tenant_a0eebc99_9c0b_4ef8_bb6d_6bb9bd380a11`) with:

- `financial_transactions` table (amount, currency, category, anomaly flags)
- `legal_documents` table (document metadata, review flags)
- `CHECK` constraint on `tenant_id` as defense in depth
- Per-tenant envelope encryption key references

**Credentials are COMPLETELY SEPARATE from the Operational Store.** The `chief_financial_app` role has no access to the Operational database, and `chief_app` has no access to this database.

### 6.3 Document/Vector Store (`chief_documents`, port 5434)

**Contains:** Playbook documents, embeddings for RAG retrieval.

- Uses `pgvector` extension for vector similarity search
- `playbook_documents` table with `vector(1536)` column (OpenAI embedding dimension)
- IVFFlat index for similarity search (upgradable to HNSW at scale)
- Per-tenant RLS isolation

### 6.4 Credential Vault

Credentials (OAuth tokens, API keys) are **never stored in any of the three databases.** The databases hold only `credential_vault_ref` pointers to a managed secrets service:

- **Dev:** Local env-backed vault abstraction
- **Prod:** HashiCorp Vault or cloud-managed (AWS Secrets Manager / GCP Secret Manager)

---

## 7. Agent System — Intelligence Design

### 7.1 Agent Registry

Each specialist agent has a platform-assigned ID and a defined scope of competence:

| Agent ID | Domain | Data Sources | Phase |
|---|---|---|---|
| `AGT-FIN` | Finance | QuickBooks, Stripe, banking APIs | Phase 1 |
| `AGT-EA` | Executive Assistant | Calendar, Email, Documents | Phase 1 |
| `AGT-HIR` | Hiring | Greenhouse, job boards, interview scheduling | Phase 2 |
| `AGT-PM` | Project Management | Linear, Jira, GitHub | Phase 2 |
| `AGT-LEG` | Legal | Contract analysis, compliance tracking | Phase 2 |
| `AGT-SAL` | Sales | CRM, pipeline analysis | Phase 2 |
| `AGT-ECHO` | Testing | Mock data | Phase 0 ✅ |

### 7.2 Agent I/O Contract (AIDD §2)

Every agent receives an `AgentInput` and must return an `AgentOutput`. This is enforced programmatically via Pydantic, not just via prompts.

**AgentInput:**
```json
{
  "goal_context": "Founder's goal text + orchestrator classification",
  "scoped_data_access_token": "short-lived JWT (5 min TTL)",
  "task_description": "Specific sub-task to complete",
  "tenant_id": "UUID — enforced on every data call",
  "prior_context": ["UUIDs of prior agent runs in this goal"],
  "playbook_refs": ["UUIDs of playbook documents for RAG"]
}
```

**AgentOutput:**
```json
{
  "answer": "Founder-facing narrative answer",
  "supporting_data": [
    {
      "source_system": "quickbooks",
      "source_ref": "txn_summary_2024_q4",
      "value": "50000",
      "retrieved_at": "2024-12-01T10:00:00Z"
    }
  ],
  "confidence": "high",
  "caveats": ["No visibility into cash sales channel"],
  "suggested_actions": [
    {
      "action_type": "schedule_meeting",
      "payload": { "title": "Q4 Review", "attendees": ["..."] },
      "risk_tier": "C",
      "rationale": "Discuss the $50,000 monthly burn with advisor"
    }
  ],
  "model_used": "gpt-4o",
  "prompt_version": "1.2.0"
}
```

### 7.3 Key Agent Design Rules

| Rule ID | Rule | Enforcement |
|---|---|---|
| GR-01 | Every numeric/factual claim requires a `supporting_data` citation | `grounding_validator.py` — programmatic, not prompt |
| GR-04 | Agents cannot self-declare risk tier; platform overrides | `tier_classifier.py` — platform lookup table |
| GR-05 | If confidence < 0.7, ask for clarification, don't guess | Orchestrator state machine transition |
| GR-06 | Synthesis confidence ≤ min(contributing agent confidences) | `Synthesizer.synthesize()` logic |

### 7.4 Model Router

The Model Router selects between **Frontier** (gpt-4o) and **Standard** (gpt-4o-mini) models based on task complexity:

| Tier | Model | Timeout | Use Case | Cost |
|---|---|---|---|---|
| Frontier | gpt-4o | 120s | Synthesis, conflict analysis, forecasting, legal review | ~$0.005/$0.015 per 1K tokens |
| Standard | gpt-4o-mini | 60s | Classification, extraction, formatting, simple summarization | ~$0.00015/$0.0006 per 1K tokens |

---

## 8. Trust & Safety Model — Non-Negotiables

These constraints are **non-negotiable**. No code path may bypass them. They are enforced at multiple layers (defense in depth).

### 8.1 Risk Tier Classification

Risk tiers are **properties of action types**, stored as **data rows** in `tier_rules` table, NOT if/else in code. An agent cannot self-declare a lower tier.

| Tier | Description | Auto-Execute? | Approval Required? |
|---|---|---|---|
| **A** | Informational (no external effect) | Always | Never |
| **B** | Reversible, low-impact | If tenant opts in | By default yes |
| **C** | Reversible, external-facing | Never | Always |
| **D** | Irreversible or high-consequence | Never | Always |

**Registered Action Types:**

| Action Type | Tier | Auto-Execute Eligible | Hard Denied |
|---|---|---|---|
| `generate_report` | A | ✅ | ❌ |
| `generate_insight` | A | ✅ | ❌ |
| `generate_forecast` | A | ✅ | ❌ |
| `generate_summary` | A | ✅ | ❌ |
| `create_internal_draft` | B | ✅ (opt-in) | ❌ |
| `create_pm_task` | B | ✅ (opt-in) | ❌ |
| `update_internal_note` | B | ✅ (opt-in) | ❌ |
| `publish_job_posting` | C | ❌ | ❌ |
| `schedule_meeting` | C | ❌ | ❌ |
| `schedule_interview` | C | ❌ | ❌ |
| `send_candidate_communication` | C | ❌ | ❌ |
| `send_investor_email` | D | ❌ | ❌ |
| `send_external_email` | D | ❌ | ❌ |
| `distribute_board_deck` | D | ❌ | ❌ |
| `send_investor_update` | D | ❌ | ❌ |
| `contract_sign` | D | ❌ | ✅ **HARD DENIED** |
| `wire_transfer` | D | ❌ | ✅ **HARD DENIED** |
| `offer_letter_send` | D | ❌ | ✅ **HARD DENIED** |
| `termination` | D | ❌ | ✅ **HARD DENIED** |
| `compensation_change` | D | ❌ | ✅ **HARD DENIED** |
| `public_statement` | D | ❌ | ✅ **HARD DENIED** |

### 8.2 Hard-Refusal Denylist (6 Actions)

These 6 actions **can NEVER execute** via the automated executor, even if every other check is buggy. Enforced at **three independent layers**:

1. **Code constant** — `HARD_DENIED_ACTION_TYPES` frozenset in `tier_classifier.py`
2. **Tool Gateway** — `denylist_enforcer.py` check at the gateway layer, independent of tier logic
3. **Database** — `is_hard_denied = true` flag in `tier_rules` table

| Action | Why Hard-Denied |
|---|---|
| `contract_sign` | NG-2: No code path may sign contracts autonomously |
| `wire_transfer` | NG-2: No code path may move money autonomously |
| `offer_letter_send` | NG-1: No code path may make hiring decisions autonomously |
| `termination` | NG-1: No code path may make firing decisions autonomously |
| `compensation_change` | NG-1/NG-2: High-consequence financial + personnel decision |
| `public_statement` | Irreversible reputational risk |

### 8.3 Fail-Closed Audit Log

The `execution_log` table is the evidentiary backbone:

- **Append-only**: `REVOKE UPDATE, DELETE` on `execution_log` from all roles including `chief_app`.
- **Only `chief_execution_writer` can INSERT** — used exclusively by the Execution Service.
- **Synchronous write**: The audit log entry must succeed BEFORE the action executes. If the write fails, the action does NOT execute. Period.
- **Hash-chained**: Each entry includes a SHA-256 hash of the previous entry for tamper detection.
- **Full payload snapshot**: The exact payload that was executed is stored, not just a reference.

### 8.4 Grounding Validator

Every agent output passes through the **Grounding Validator** before reaching synthesis:

1. Extracts numeric/factual claims from the answer text (currency amounts, percentages, dates, runway mentions, burn rate references).
2. Checks each claim against `supporting_data` entries — each claim must map to `{source_system, source_ref, value, retrieved_at}` or be tagged `source_system: "agent_inference"`.
3. Ungrounded claims are **stripped** from the output and replaced with `[CLAIM REMOVED — no citation]`.
4. Caveats are appended to inform the founder that claims were removed.

This is a **programmatic check**, not a prompt instruction. It cannot be bypassed by prompt injection.

---

## 9. Orchestrator — State Machine & Workflow

### State Machine (AIDD §3)

```
RECEIVED
    │
    ▼
CLASSIFYING ──────────┐
    │                  │ (confidence < 0.7)
    │ (confidence ≥ 0.7)│
    ▼                  ▼
DECOMPOSING    AWAITING_CLARIFICATION
    │                  │
    │                  ├──→ STALLED (after 24h)
    │                  │
    │                  └──→ DECOMPOSING (after clarification)
    ▼
DISPATCHING
    │
    ▼
AWAITING_SPECIALIST_OUTPUT
    │
    ▼
SYNTHESIZING
    │
    ├──→ ROUTING_ACTIONS (if suggested_actions exist)
    │         │
    │         ▼
    └──→ DELIVERED
```

Each transition is validated — invalid transitions (e.g., `RECEIVED → DELIVERED`) raise `ValueError`.

### Components

| Component | File | Responsibility |
|---|---|---|
| `GoalClassifier` | `orchestrator.py` | Classifies goal type (reporting, monitoring, forecasting, composite, action_request, ad_hoc_question). Phase 0: keyword-based. Phase 1+: LLM-powered. |
| `TaskDecomposer` | `orchestrator.py` | Breaks a classified goal into a task graph with agent assignments and dependencies. |
| `Dispatcher` | `dispatcher.py` | Executes task graph respecting dependencies, parallel where possible, with bounded concurrency (max 5) and per-task timeouts. |
| `ConflictDetector` | `orchestrator.py` | Pairwise comparison of agent outputs for contradictions (same action_type with different payloads). Phase 1: surface only, no arbitration. |
| `Synthesizer` | `orchestrator.py` | Combines outputs into a unified report. Confidence is min(contributing confidences) — never silently upgraded (GR-06). |
| `ModelRouter` | `model_router.py` | Selects Frontier vs Standard model based on task complexity heuristics. Tracks cost/token usage. |

---

## 10. Execution Service — Approval Gate & Audit

The **Execution Service** is the sole holder of external write credentials. No other service can write to external systems.

### Execution Flow

```
Suggested Action received from Orchestrator
        │
        ▼
    ┌─────────────────────┐
    │ 1. DENYLIST CHECK   │  ← Independent of tier logic
    │    (hard-refusal)   │     Blocks contract_sign, wire_transfer, etc.
    └─────────┬───────────┘
              │ pass
              ▼
    ┌─────────────────────┐
    │ 2. TIER CLASSIFY    │  ← Platform rules, not agent-proposed
    │    (override agent  │     Agent says Tier B? Platform says Tier D → Tier D wins.
    │     if wrong)       │
    └─────────┬───────────┘
              │
              ▼
    ┌─────────────────────┐
    │ 3. AUTO-EXECUTE?    │  ← Tier A: always. Tier B: if tenant opted in.
    │                     │     Tier C/D: NEVER.
    └──┬──────────┬───────┘
       │ yes      │ no
       │          ▼
       │   ┌─────────────────────┐
       │   │ 4. CREATE APPROVAL  │
       │   │    REQUEST          │  ← Pending in UI, expires per tier
       │   │    (diff_preview    │     Tier B: 24h, C: 72h, D: 7d
       │   │     = exact payload)│
       │   └─────────┬───────────┘
       │             │ human approves
       │             ▼
       └────────────►│
                     ▼
    ┌─────────────────────┐
    │ 5. AUDIT LOG WRITE  │  ← MUST succeed first (fail-closed)
    │    (synchronous,    │     Hash-chained, payload snapshot
    │     append-only)    │
    └─────────┬───────────┘
              │ success
              ▼
    ┌─────────────────────┐
    │ 6. EXECUTE ACTION   │  ← Via Tool Gateway
    │    (external write) │
    └─────────────────────┘
```

---

## 11. Tool/Integration Gateway

The **Tool Gateway** is the single point through which all external services are accessed. Agents never hold raw credentials.

### Token Scoping

When an agent needs data, it receives a **short-lived, capability-scoped token** (default 5-minute TTL):

| Property | Detail |
|---|---|
| TTL | 5 minutes (configurable) |
| Scope | Specific operations (e.g., `read:transactions`) |
| Integration scope | Specific integrations (e.g., `mock_accounting`) |
| Revocable | Can be revoked instantly |
| Per-request | New token for each agent invocation, never reused |

### Denylist Enforcement (Defense in Depth)

The gateway enforces the hard-refusal denylist **independently** of the Execution Service. Even if the Execution Service has a bug, denied actions are blocked here.

### Mock Adapters (Phase 0)

| Adapter | Simulates |
|---|---|
| `mock_accounting` | QuickBooks — returns sample transactions, burn rate, runway |
| `mock_calendar` | Google Calendar — event creation |
| `mock_email` | Gmail — email sending |
| `mock_ats` | Greenhouse — candidate pipeline |
| `mock_pm` | Linear — project tasks and status |

---

## 12. API Gateway

The API Gateway is the **single public entry point**. No backend service is directly accessible.

### Endpoints

| Method | Path | Auth | Rate Limit | Forwards To |
|---|---|---|---|---|
| `GET` | `/health` | None | Global | — |
| `POST` | `/dev/token` | None (dev only) | Global | — |
| `POST` | `/api/goals` | JWT | 10/min/tenant | Orchestrator |
| `GET` | `/api/goals/:id` | JWT | Global | Orchestrator |
| `GET` | `/api/approvals` | JWT | Global | Approval Workflow |
| `POST` | `/api/approvals/:id/decide` | JWT | Global | Execution Service |
| `GET` | `/api/insights` | JWT | Global | Orchestrator |
| `GET` | `/api/integrations` | JWT | Global | Tool Gateway |
| `GET` | `/api/audit-log` | JWT | Global | Execution Service |

### JWT Token Format

```json
{
  "sub": "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22",
  "tenant_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "role": "founder",
  "iss": "chief-dev",
  "exp": 1735689600
}
```

Every request gets a `X-Trace-Id` header (generated or propagated) for distributed tracing.

---

## 13. Observability & Tracing

### Architecture

Every service uses `TracingManager` from `chief_types.observability`:

- **Standard spans**: `start_span(name, trace_id, tenant_id)` — used for any operation
- **Agent spans**: `start_agent_span(agent_name, task_id, tenant_id)` — specialized for AI calls, includes:
  - `model_id`, `prompt_version`, `prompt_tokens`, `completion_tokens`, `latency_ms`
  - Grounding validation results (`grounded_claims`, `stripped_claims`)
  - Confidence level

### Trace Correlation

A single `trace_id` flows through the entire pipeline:

```
API Gateway → Orchestrator → Dispatcher → Agent → Grounding → Synthesizer → Execution Service → Tool Gateway
```

This allows querying the full history of any goal from submission to execution in a single trace view.

---

## 14. Kubernetes Infrastructure

### Namespace

All Chief resources run in the `chief-system` namespace.

### Database StatefulSets

| StatefulSet | Image | Port | Storage | Purpose |
|---|---|---|---|---|
| `chief-operational-db` | `postgres:15` | 5432 | 10Gi PVC | Operational Store |
| `chief-financial-db` | `postgres:15` | 5432 | 10Gi PVC | Financial/Legal Store (SEPARATE credentials) |
| `chief-documents-db` | `pgvector/pgvector:pg15` | 5432 | 10Gi PVC | Document/Vector Store |

Each database is a **separate StatefulSet** with its own PersistentVolumeClaim. Credentials come from the K8s `Secret` resource (`chief-secrets`), not baked into images.

### ConfigMap / Secrets

- **ConfigMap (`chief-config`)**: Service URLs (internal K8s DNS), DB hostnames, ports, OTel endpoint.
- **Secret (`chief-secrets`)**: DB passwords, JWT secret, Vault encryption key.

### Service Discovery

All inter-service communication uses Kubernetes internal DNS:
```
http://<service-name>.chief-system.svc.cluster.local:<port>
```

---

## 15. Phased Development Roadmap

| Phase | Name | Key Deliverables | Status |
|---|---|---|---|
| **Phase 0** | Platform Foundation | DB schema, shared types, grounding validator, tier classifier, denylist, execution service, orchestrator skeleton, echo agent, E2E test | ✅ **Complete** |
| **Phase 1** | Vertical Slice (Finance + EA) | Real LLM integration, QuickBooks adapter, calendar adapter, Next.js UI, auth provider | 🔲 Next |
| **Phase 2** | Multi-Domain | Hiring agent, PM agent, conflict detection, playbook RAG | 🔲 |
| **Phase 3** | Trust & Scale | Confidence calibration, multi-tenant perf testing, SOC 2 prep | 🔲 |
| **Phase 4** | Platform Polish | Board deck generator, multi-model routing, team features | 🔲 |
| **Phase 5** | Growth | Public launch, marketplace, API access | 🔲 |

### Phase 0 Exit Criteria (✅ All Met)

> *"A fake 'hello world' agent can be dispatched, produce a cited structured output conforming to the AIDD contract, route a dummy Tier C action through the approval gate, and the full trace is inspectable end to end."*

Verified by `tests/e2e/test_phase0_exit.py`.

---

## 16. Testing Strategy

### Test Categories

| Category | What's Tested | Location |
|---|---|---|
| **Grounding Tests** | Every numeric claim in agent output has a citation | `packages/shared-types/python/tests/test_grounding_validator.py` |
| **Tier Tests** | Platform tier overrides agent-proposed tier; all 6 denylist actions blocked | `packages/shared-types/python/tests/test_tier_classifier.py` |
| **Denylist Tests** | Hard-denied actions raise RuntimeError at multiple enforcement layers | `packages/shared-types/python/tests/test_denylist_enforcer.py` |
| **Execution Service Tests** | Fail-closed audit, approval lifecycle, diff preview = payload, hash chain integrity | `services/execution-service/tests/test_execution_service.py` |
| **Tool Gateway Tests** | Token scoping, expiry, revocation, denylist at gateway layer | `services/tool-gateway/tests/test_tool_gateway.py` |
| **Approval Workflow Tests** | Lifecycle, expiration, priority sorting, audit history | `services/approval-workflow/tests/test_approval_workflow.py` |
| **Orchestrator Tests** | State machine transitions, classification, dispatch, timeout, model routing | `services/orchestrator/tests/test_orchestrator.py` |
| **API Gateway Tests** | JWT auth, rate limiting, trace_id, route definitions | `services/api-gateway/tests/test_server.js` |
| **E2E Tests** | Full pipeline: goal → classification → dispatch → grounding → approval → execution → audit | `tests/e2e/test_phase0_exit.py` |

### Critical Test Assertions

These tests represent the **non-negotiable** safety properties. If any fail, the system cannot ship:

```python
# Fail-closed: audit log failure blocks execution
service.audit_writer.set_should_fail(True)
with pytest.raises(AuditLogWriteError):
    service.submit_action(action, TENANT_ID)
assert len(service.executor.get_executions()) == 0  # NOTHING executed

# Denylist: all 6 actions blocked even with wrong tier
for action_type in ["contract_sign", "wire_transfer", "offer_letter_send",
                     "termination", "compensation_change", "public_statement"]:
    action = _make_action(action_type, RiskTier.A)  # Agent claims Tier A!
    with pytest.raises(DenylistViolationError):
        service.submit_action(action, TENANT_ID)

# Tier override: platform always wins
action = _make_action("send_investor_email", RiskTier.B)  # Agent claims B
result = service.submit_action(action, TENANT_ID)
assert result.risk_tier == RiskTier.D  # Platform says D

# Grounding: ungrounded claims are stripped
output = AgentOutput(answer="Burn is $75,000", supporting_data=[], ...)
result = validate_grounding(output)
assert not result.is_valid
assert "[CLAIM REMOVED" in result.validated_output.answer
```

---

## 17. Getting Started (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- `pnpm`
- Neon PostgreSQL Account

### Option A: Neon PostgreSQL & Alembic (MVP Setup)

We have migrated to a serverless cloud database model using Neon for the MVP/Hackathon.

```bash
# 1. Export your Neon connection string
export DATABASE_URL="postgresql+asyncpg://<user>:<password>@<host>/<database>?ssl=require"

# 2. Run Database Migrations using Alembic
cd packages/db
pip install alembic asyncpg
alembic upgrade head

# 3. Seed demo data (if not done in migration)
# The initial migration 001_initial_schema automatically seeds the 'AIHealth Inc.' demo company.
```

### Option B: Run Tests Directly (No DB required)

The shared types, grounding validator, tier classifier, denylist, execution service, and orchestrator tests all run without a database:

```bash
# Install Python deps
cd packages/shared-types/python
pip install pydantic pytest pytest-asyncio

# Run shared types tests
pytest tests/ -v

# Run execution service tests
cd ../../../services/execution-service
pytest tests/ -v

# Run orchestrator tests
cd ../orchestrator
pytest tests/ -v

# Run tool gateway tests
cd ../tool-gateway
pytest tests/ -v

# Run E2E tests
cd ../../tests/e2e
pytest test_phase0_exit.py -v

# Run API Gateway tests (Node.js)
cd ../../services/api-gateway
npm install
npm test
```

---

## 18. Environment Variables (Complete Reference)

All defined in `.env.example`. Copy to `.env` for local use.

| Variable | Default | Purpose |
|---|---|---|
| `OPERATIONAL_DB_HOST` | `localhost` | Operational PostgreSQL host |
| `OPERATIONAL_DB_PORT` | `5432` | Operational PostgreSQL port |
| `OPERATIONAL_DB_NAME` | `chief_operational` | Operational database name |
| `OPERATIONAL_DB_USER` | `chief_app` | Operational database user |
| `OPERATIONAL_DB_PASSWORD` | `changeme_operational` | Operational database password |
| `FINANCIAL_DB_HOST` | `localhost` | Financial/Legal PostgreSQL host |
| `FINANCIAL_DB_PORT` | `5433` | Financial/Legal PostgreSQL port |
| `FINANCIAL_DB_NAME` | `chief_financial` | Financial/Legal database name |
| `FINANCIAL_DB_USER` | `chief_financial_app` | Financial/Legal database user |
| `FINANCIAL_DB_PASSWORD` | `changeme_financial` | Financial/Legal database password |
| `DOCUMENTS_DB_HOST` | `localhost` | Document/Vector PostgreSQL host |
| `DOCUMENTS_DB_PORT` | `5434` | Document/Vector PostgreSQL port |
| `DOCUMENTS_DB_NAME` | `chief_documents` | Document/Vector database name |
| `DOCUMENTS_DB_USER` | `chief_docs_app` | Document/Vector database user |
| `DOCUMENTS_DB_PASSWORD` | `changeme_documents` | Document/Vector database password |
| `VAULT_BACKEND` | `local` | Credential vault backend (`local` or `vault`) |
| `VAULT_ENCRYPTION_KEY` | `changeme...` | Envelope encryption master key |
| `API_GATEWAY_PORT` | `3000` | API Gateway listen port |
| `JWT_SECRET` | `changeme_jwt_secret` | JWT signing secret |
| `JWT_ISSUER` | `chief-dev` | JWT issuer claim |
| `ORCHESTRATOR_URL` | `http://localhost:8000` | Orchestrator service URL |
| `EXECUTION_SERVICE_URL` | `http://localhost:8001` | Execution Service URL |
| `TOOL_GATEWAY_URL` | `http://localhost:8002` | Tool Gateway URL |
| `APPROVAL_WORKFLOW_URL` | `http://localhost:8003` | Approval Workflow URL |
| `AGENT_ECHO_URL` | `http://localhost:8010` | Echo Agent URL |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry collector endpoint |
| `OTEL_SERVICE_NAME` | `chief` | OTel service name |
| `DEFAULT_FRONTIER_MODEL` | `gpt-4o` | Frontier tier LLM model |
| `DEFAULT_STANDARD_MODEL` | `gpt-4o-mini` | Standard tier LLM model |
| `OPENAI_API_KEY` | `sk-changeme` | OpenAI API key (Phase 1+) |
| `ENVIRONMENT` | `development` | Environment name |
| `LOG_LEVEL` | `DEBUG` | Logging level |

---

## 19. Specification Documents Index

The `/docs/` directory contains the complete specification set. These are the **source of truth** for all design decisions.

| Doc | Title | Key Contents |
|---|---|---|
| 01 | Product Vision Document (PVD) | Mission, target user, agent roles, report content contract (§10) |
| 02 | Product Requirements Document (PRD) | Functional requirements FR-1 through FR-8, character limits, streaming |
| 03 | Agent Intelligence Design Document (AIDD) | Agent registry, I/O contract, grounding rules (GR-01–GR-06), state machine, model tier routing, prompt versioning |
| 04 | Software Architecture Document (SAD) | Component responsibilities, service boundaries, data flow |
| 05 | Technical Requirements Document (TRD) | NFRs, performance targets, fail-closed logging, token budgets |
| 06 | Database Design Document (DDD) | Three-store architecture, schema-per-tenant, append-only log, partitioning strategy |
| 07 | Workflow Design Document (WDD) | Goal processing workflow, approval lifecycle, proactive monitoring |
| 08 | UX/UI Design Specification (UXDS) | Insight feed design, approval cards, report layout |
| 09 | Security & Governance Document (SGD) | Approval-tier model, denylist, credential isolation, audit requirements |
| 10 | Development Roadmap | Phase 0–5 definitions, exit criteria per phase |
| 11 | Testing Strategy | Grounding tests, approval tests, eval pipeline, regression tracking |
| 12 | Deployment & DevOps Guide | Container strategy, K8s topology, monitoring, incident response |

---

## 20. Spec Gaps & Decisions Log

When a specification is genuinely silent on an implementation detail, the smallest reasonable default is taken and logged in [SPEC-GAPS.md](./SPEC-GAPS.md).

Current tracked gaps:

| ID | Gap | Default Taken |
|---|---|---|
| SG-001 | Credential vault implementation for dev | Env variables behind vault abstraction interface |
| SG-002 | Per-tenant encryption key rotation policy | Keys in vault with DB references; rotation deferred to Phase 1 |
| SG-003 | Specific JWT provider not specified | Generic JWT validation; provider decided in Phase 1 |
| SG-004 | AI-trace retention period not quantified | 90 days general, 1 year AI traces |
| SG-005 | Notification mechanism for AWAITING_CLARIFICATION | Goal marked STALLED after 24h, surfaced in UI feed |

---

## License

Proprietary. All rights reserved.
