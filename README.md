# Vera — Magicpin AI Challenge

Vera is a deterministic, high-precision AI merchant engagement and messaging engine built for the Magicpin AI Challenge. It ingests multi-source merchant performance metrics, active offers, category demand digests, and customer triggers to decide:

> *"Given everything currently happening for this merchant and customer, WHAT is the single most valuable thing Vera should communicate right now, and WHY?"*

---

## 1. Overview

Vera continuously evaluates raw contextual signals across 5 major commerce categories, normalizes signal scores, applies deterministic ranking rules, and composes category-tailored, zero-hallucination engagement messages with a single call-to-action (CTA).

---

## 2. Problem Statement

Local business owners receive dozens of automated notifications, generic performance summaries, and uncoordinated marketing prompts daily. Most of these messages lack specificity, urgency, or context, causing merchant fatigue.

Vera solves this by:
1. Identifying the single highest-value opportunity at any given moment.
2. Grounding all communications strictly in verified merchant data and category dynamics.
3. Managing state across multi-turn interactions (acceptances, rejections, clarifications) to avoid repetitive or tone-deaf messaging.

---

## 3. Solution Pipeline

```
┌──────────────────┐
│  Context Push    │  (/v1/context) -> Ingests Merchant, Customer, Offer & Category data
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Signal Extractor │  Calculates standardized scores, recency, & material changes
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Ranking Engine   │  Applies priority weights, recency decay, & suppression filters
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Strategy Composer│  Selects category voice, grounds template params, generates CTA
└────────┬─────────┘
         │
┌────────▼─────────┐
│ State Manager    │  Updates conversation history, manages suppression keys (/v1/reply)
└──────────────────┘
```

---

## 4. Architecture

```
                               ┌────────────────────────┐
                               │     FastAPI Server     │
                               └───────────┬────────────┘
                                           │
          ┌────────────────────────────────┼────────────────────────────────┐
          │                                │                                │
┌─────────▼──────────┐           ┌─────────▼──────────┐           ┌─────────▼──────────┐
│  /v1/context       │           │  /v1/tick          │           │  /v1/reply         │
│ (State Ingestion)  │           │ (Decision Engine)  │           │ (State Machine)    │
└─────────┬──────────┘           └─────────┬──────────┘           └─────────┬──────────┘
          │                                │                                │
          ▼                                ▼                                ▼
  In-Memory Store ◄─────────────── Grounded Ranking ──────────────► State Machine &
  (Merchant/Customer)             & Strategy Selector               Suppression Store
```

---

## 5. Supported Categories

Vera includes vertical-specific strategy matrices for:

1. **Dentists** (`dentists`): Clinical, peer-to-peer, professional tone, technical clarity, uses "Dr." title prefix.
2. **Salons** (`salons`): Warm, friendly, aesthetic focus, customer retention and appointment slot optimization.
3. **Restaurants** (`restaurants`): Direct operator-to-operator tone, order velocity, rush hour preparation, menu item volume.
4. **Gyms** (`gyms`): Motivational, outcome-driven, member retention, seasonal subscription renewals.
5. **Pharmacies** (`pharmacies`): Authoritative, precise, inventory expiry warnings, high-margin stock clearance.

---

## 6. API Specification

### `GET /v1/healthz`
Health check endpoint.
```json
{
  "status": "ok",
  "uptime_seconds": 1420,
  "contexts_loaded": {
    "merchant": 5,
    "customer": 2
  }
}
```

### `GET /v1/metadata`
Service metadata endpoint.
```json
{
  "team_name": "Magicpin Vera AI Baseline",
  "team_members": ["Candidate"],
  "model": "deterministic-rules-v1",
  "approach": "Deterministic 4-context signal extraction with category strategy grounding and zero-hallucination composition",
  "contact_email": "candidate@example.com",
  "version": "1.0.0",
  "submitted_at": "2026-09-26T00:00:00Z"
}
```

### `POST /v1/context`
Pushes context state updates into process memory.
```json
{
  "scope": "merchant",
  "context_id": "m_101",
  "version": 1,
  "payload": { ... },
  "delivered_at": "2026-09-26T12:00:00Z"
}
```

### `POST /v1/tick`
Evaluates active triggers against stored context and generates recommended actions.
```json
{
  "now": "2026-09-26T12:00:00Z",
  "available_triggers": ["trg_001"]
}
```

### `POST /v1/reply`
Handles merchant or customer responses to Vera messages.
```json
{
  "conversation_id": "conv_001",
  "merchant_id": "m_101",
  "from_role": "merchant",
  "message": "Yes, let's launch the discount now.",
  "received_at": "2026-09-26T12:05:00Z",
  "turn_number": 1
}
```

---

## 7. Decision Engine Mechanics

- **Signal Extraction**: Standardizes performance dips, demand surges, research digests, and inventory warnings into standard signal models (`SignalType`, `raw_value`, `normalized_score`).
- **Recency & Decay**: Applies half-life exponential decay to older signals.
- **Priority Ranking**: Combines category relevance, business impact, and urgency weights to pick the single top-ranked decision.
- **Suppression Management**: Suppresses active decisions if the merchant previously rejected them or if a material change threshold has not been reached.

---

## 8. Stateful Behavior & Multi-Turn Intelligence

- **Acceptance (`"accept"`)**: Transitions state to `accepted`, executes CTA action, and suppresses redundant nudges.
- **Rejection (`"reject"`)**: Logs suppression key, records rejection rationale, and halts repeated nudges unless a higher-urgency trigger occurs.
- **Clarification (`"clarify"`)**: Provides grounded, fact-based rationale explaining *why* the recommendation was made.
- **Material Change Override**: High-urgency triggers (e.g. `urgency >= 4`) can override existing suppressions.

---

## 9. Grounding & Zero-Hallucination Policy

Vera enforces strict validation rules before any message is emitted:
- **No Invented Numbers**: Percentages, view counts, and call volumes must match input payloads exactly.
- **No Fabricated Offers**: Discount rates and price points are bound strictly from active merchant offer arrays.
- **Missing Data Fallback**: Missing customer names fall back to neutral category salutations; missing offer prices use percentage-off descriptors.

---

## 10. Determinism

All decision selection, ranking, template binding, and state transitions are 100% deterministic. Executing identical input sequences produces bit-for-bit identical JSON responses across runs.

---

## 11. Testing & Verification

### Run Pytest Test Suite (28 Tests)
```bash
python -m pytest tests/ -v
```

### Run Evaluation Harness
```bash
python tests/eval_harness.py
```

### Run Server Integration Test
```bash
python -m pytest tests/test_server_integration.py -v
```

---

## 12. Deployment

### Local Server Startup
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1
```

### Docker Build & Run
```bash
docker build -t vera-bot:latest .
docker run -p 8080:8080 -e PORT=8080 vera-bot:latest
```

---

## 13. Public API Deployment

- **Public Base URL**: `https://vera-bot-service-8080.a.run.app` (or local `http://localhost:8080`)
- **Protocol**: HTTPS / TLS 1.3
- **Worker Configuration**: Single-worker (`--workers 1`) to preserve in-memory state consistency.

---

## 14. Known Limitations

- **In-Memory State**: Merchant context and conversation states reside in single-process memory. If the container restarts during a judge evaluation run, in-memory state resets.
- **Multi-Process Scaling**: Scaling horizontally across multiple worker nodes requires external persistent storage (e.g., Redis/PostgreSQL).
