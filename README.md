# HW 5 — Campus Customs Multi-Agent Operations

A five-agent team runs the Campus Customs shop:
- **Boss** routes tickets and makes the final calls.
- **Inventory** handles stock and restocking.
- **Accounting** handles cash, bills, and payments, which a person must approve.
- **Facilities** handles the lease and store upkeep.
- **Customer Service** drafts customer messages, which are never sent.

The project has three parts that talk to each other:

```
React board (frontend/, :5173)  →  FastAPI backend (backend/main.py, :8000)  →  MCP server (mcp_server/server.py)  →  data/campus_customs_new.db
```

- **Model:** every agent uses **`gpt-6-luna` through Portkey**, and no other model.
- **Shop facts:** they come only from the MCP server, which reads the working copy of the database.
- **Payments:** agents only *prepare* them. Cash moves only when a person clicks **Approve & pay**.

## What's in the repo

| Path | What it is |
|---|---|
| `data/campus_customs.db` | The **original** shop database. Never changed; use it to reset. |
| `data/campus_customs_new.db` | The **working copy** the app reads and writes. As committed, it holds the state after the final graded run (3 tickets resolved, cash $152.00). |
| `mcp_server/` | FastMCP server with 24 tools (`server.py`), its README, and `start.sh` (used by `.mcp.json`) |
| `backend/` | FastAPI routes (`main.py`), data types (`models.py`), the five agents (`boss.py`, `inventory.py`, `accounting.py`, `facilities.py`, `customer_service.py`), the agent loop and handoffs (`team.py`), the audit writer (`audit.py`), a command-line runner (`run.py`), and the agent prompts in `prompts/` |
| `frontend/` | The React + Vite + TypeScript Ops Desk |
| `output/` | `harness.md` (the full write-up), `mcp_smoke.json`, `desk_tickets.html`, `design.md`, `resolved_tickets.json`, `resolved_board.html` (plus `screenshots/`), `audit_trail.json`, `github_url.txt` |
| `AI_prompts.md` | Every prompt I typed into my vibe coder, by problem |
| `.env.example` | Copy to `.env` and add your own Portkey key. The real `.env` is not in the repo. |

## Setup (once)

You need Python 3.11+ and Node.js 18+.

```bash
git clone <this repo> hw5 && cd hw5
cp .env.example .env                  # then put your PORTKEY_API_KEY in .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm install && cd ..
```

## 1. Clean run: copy the original database to the working copy

The committed working copy shows the finished run. To start fresh, copy the original over it:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

This restores the starting state: 3 open tickets and $3,400.00 in checking, with no requests, drafts or payments. The MCP server recreates its empty board tables (`approval_requests`, `drafts`, `ticket_updates`, `store_tasks`) the first time it connects. You can also reset from the dashboard with **Reset data**, or with `POST /reset` (step 6).

## 2. Start the MCP server

The backend starts the MCP server on its own, as a child process, so you don't need a separate terminal for it. To run it by itself, for example to inspect the tools:

```bash
sh mcp_server/start.sh                # same as: .venv/bin/python mcp_server/server.py
```

To use it from Claude Code, open the project folder. `.mcp.json` registers it as `campus-customs`, and Claude Code asks you to approve it once.

## 3. Start the FastAPI backend (terminal 1)

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs.

| Route | What it does |
|---|---|
| `GET /tickets` | The tickets, each with its status and `open`/`resolved` state |
| `POST /tickets/{id}/run` | Runs the agent team on one ticket |
| `GET /events` | Recent agent events: what each agent said, and the tools it used |
| `GET /approvals` | Payment and purchase requests waiting for a person |
| `POST /approvals/{id}/approve` | A person approves. **The only route that moves cash.** |
| `POST /approvals/{id}/reject` | A person rejects |
| `GET /cash` | The checking balance from `cash_accounts` |
| `POST /reset` | Copies the original database over the working copy |

CORS allows only the dashboard's origin, `http://localhost:5173`.

## 4. Start the React board (terminal 2)

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. Pick a ticket and click **Run team** to watch the agents work live. Approve payments in the **Approvals** panel and watch the checking balance change.

## 5. Full three-ticket run

1. **Reset the database first**, with **Reset data** on the board or step 1 above, so the run starts at $3,400.00.
2. Click **Run team** on ticket **103 first**, then 101, then 102. With 103 first, Accounting ranks the bills while there's still cash.
3. Approve the requests the agents prepare as they appear: invoice 501 ($840), rent ($2,400), and any purchase order.
4. Run a ticket again if it's waiting on an approval you've since given, so Boss sees the payment landed and marks it resolved.

Every step is appended to `output/audit_trail.json`, which is never wiped.

From the command line, without the board:

```bash
.venv/bin/python -m backend.run --all      # or --ticket 101, or --daily
```

## 6. Reset before another full run

Use **Reset data** on the board, or `curl -X POST localhost:8000/reset`, or stop the backend and run the `cp` from step 1.

## Results of the graded run (Nov 3, 2026)

Run order 103 → 101 → 102, with Boss's "fill from stock" rule. All three tickets resolved.

| Ticket | Final status | Cash |
|---|---|---|
| #103 Bulk hoodies | resolved: all 20 offered from stock (8 M + 12 L) at $40 | −$2,400.00 and −$840.00 (rent and invoice 501, filed during 103 by bill priority, approved by Cedric) |
| #101 Bulldog tee | resolved | −$8.00 (purchase order for 1 tee, approved by Cedric) |
| #102 Rent due | resolved | $0.00 (rent was already paid) |

Checking: $3,400.00 → **$152.00**, which matches `cash_accounts`. Problem 9 was run three times. `output/harness.md` compares them: Nov 2 resolved 2 of 3 and ended at $160.00; an earlier Nov 3 run resolved all 3 but offered only 8 hoodies. Details are in `output/desk_tickets.html`, `output/resolved_tickets.json` and `output/resolved_board.html`.
