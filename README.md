# ShadowTwin

**Crash-test your security before attackers do.**

ShadowTwin is a digital twin of an organisation's IT environment. It models assets and
their relationships as a graph, estimates breach risk, and shows which defensive controls
reduce that risk the most, without touching real infrastructure.

Built for **CYBERGEN 2026 – Problem Statement 1** (AI-Powered Digital Twin for Cyber Attack Simulation).

## Features
- **Org twin** – assets, zones and relationships as a graph
- **Risk paths** – each step tagged with a MITRE ATT&CK / ATLAS technique ID
- **Blast radius** – what is reachable from a compromised asset
- **Breach probability** – Monte Carlo estimate across attacker personas
- **Defence planner + What-if** – toggle controls and compare before vs after
- **AI layer** – twin from plain English, step-by-step explanations
- **Standards** – STIX 2.1 export, local-LLM privacy mode

## Tech stack
| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui, Cytoscape.js, Recharts |
| Backend | FastAPI + Pydantic v2 |
| Engine | NetworkX + NumPy |
| AI | LLM with schema-validated JSON output, Ollama local mode |
| Ops | Docker Compose, GitHub Actions, Render + Vercel |

## Run locally
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
API docs: http://127.0.0.1:8000/docs

Or with Docker:
```bash
docker compose up --build
```

## Tests
```bash
cd backend && python -m pytest tests/ -v
```

## Team
| Role | Member |
|---|---|
| Engine lead | Shaju |
| Frontend | Dilip |
| AI + MITRE | JK |
| Data, deploy + pitch | Sakthivel |
