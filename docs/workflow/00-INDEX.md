# 🚀 SatQuery AI — 3-Day POC Sprint Guide

> **SIH 2026 · ISRO/SAC** — Agentic Remote-Sensing AI System
> **Deadline:** 3 days | **Team:** 5 members | **Approach:** Fully vibe-coded with Claude/Antigravity

---

## Document Index

| # | Document | What It Covers |
|---|----------|----------------|
| 01 | [POC Overview](01-POC-OVERVIEW.md) | What we're building in 3 days, what's in/out of scope, success criteria |
| 02 | [Architecture — POC](02-ARCHITECTURE-POC.md) | Simplified architecture for the 3-day build |
| 03 | [Work Division](03-WORK-DIVISION.md) | 5 members × 3 days — who does what, hour by hour |
| 04 | [Backend Plan](04-BACKEND-PLAN.md) | FastAPI backend — endpoints, schemas, model registry |
| 05 | [Frontend Plan](05-FRONTEND-PLAN.md) | Next.js frontend — upload, query, results, trace |
| 06 | [Agent & Router](06-AGENT-ROUTER-PLAN.md) | Rule-based router + input validation + trace builder |
| 07 | [Model Pipelines](07-PIPELINES-PLAN.md) | Model-agnostic pipeline wrappers (model slots TBD) |
| 08 | [Model Recommendations](08-MODEL-RECOMMENDATIONS.md) | Recommended models for RTX 4060 8GB — dedicated per input type |
| 09 | [Demo Script](09-DEMO-SCRIPT.md) | 5 demo scenarios, test data, fallback plan |

---

## Quick Start

```
1. Read 01-POC-OVERVIEW    → Understand the 3-day scope
2. Read 03-WORK-DIVISION   → Find your assignment
3. Read your assigned doc   → 04/05/06/07 based on your role
4. Read 08-MODEL-RECS      → Understand the model strategy
5. Build. Ship. Demo.
```

## 3-Day Build Sequence

```
Day 1 (Sept 1) → Scaffold + Core Pipelines
  Morning:  Project setup, env, dependencies
  Afternoon: Backend API + Frontend shell + Router skeleton
  Evening:  First model wrapper working end-to-end

Day 2 (Sept 2) → All Pipelines + Integration
  Morning:  All 5 pipeline wrappers functional
  Afternoon: Frontend ↔ Backend fully connected
  Evening:  Execution trace + evidence generation

Day 3 (Sept 3) → Polish + Demo Prep
  Morning:  Fine-tuning scripts run / adapters loaded
  Afternoon: All 5 demo scenarios passing
  Evening:  Demo rehearsal, backup data, recording
```

> [!IMPORTANT]
> This is a POC. Ship working > ship perfect. Every feature must pass through the agent — no manual model selection.
