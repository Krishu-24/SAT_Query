# SatQuery AI — 3-Day POC Sprint Guide

> SIH 2026 · ISRO/SAC  
> Agentic remote-sensing AI system  
> Deadline: 3 days | Team: 5 members

## Document Index

| # | Document | Scope |
|---|---|---|
| 01 | [POC Overview](01-POC-OVERVIEW.md) | Project goal, in-scope features, delivery criteria |
| 02 | [Architecture — POC](02-ARCHITECTURE-POC.md) | Core system design and execution flow |
| 03 | [Work Division](03-WORK-DIVISION.md) | Role allocation and daily sprint plan |
| 04 | [Backend Plan](04-BACKEND-PLAN.md) | FastAPI structure, contracts, and integration path |
| 05 | [Frontend Plan](05-FRONTEND-PLAN.md) | UI architecture and interaction flow |
| 06 | [Agent & Router](06-AGENT-ROUTER-PLAN.md) | Input validation, routing logic, and tracing |
| 07 | [Model Pipelines](07-PIPELINES-PLAN.md) | Model wrappers and execution contracts |
| 08 | [Model Recommendations](08-MODEL-RECOMMENDATIONS.md) | Hardware-aware model selection and VRAM planning |
| 09 | [Demo Script](09-DEMO-SCRIPT.md) | Five demo scenarios and presentation flow |

## Recommended Reading Sequence

1. Read the overview to confirm scope and success criteria.
2. Review the work division to understand ownership.
3. Read the role-specific plan: backend, frontend, router, or pipeline.
4. Check the model recommendations before final implementation decisions.

## 3-Day Build Sequence

### Day 1

- scaffold the project and environment
- implement core API and router skeleton
- validate first end-to-end pipeline

### Day 2

- complete the five pipeline wrappers
- connect frontend to backend
- generate evidence and execution trace outputs

### Day 3

- stabilize edge cases and polishing
- run full demo flow and rehearsal
- prepare fallback assets and presentation materials

> This is a proof-of-concept build. The goal is a working system with clear evidence, not a perfect production system.
