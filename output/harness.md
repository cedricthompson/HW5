# Harness — Campus Customs Multi-Agent Operations

Notes on the shop database that the agent team works from.

- **Original:** `data/campus_customs.db`. Never changed, so it can be used to reset.
- **Working copy:** `data/campus_customs_new.db`. The MCP server and backend point here, and later problems update it.
- **Today:** `desk.date_today` = **2026-08-31**. Use this date to decide what is overdue, not the computer clock.


**Contents**
1. [Tables](#tables): the 9 shop tables, plus the 4 board tables the MCP server adds
2. [MCP server tools](#all-mcp-tools-and-the-tables-they-use): all 24 tools and the tables each one uses
3. [Agent team](#agent-team-backend): the 5 agents, their prompts and tools, handoffs, the agent loop, and the audit trail
4. [API routes](#api-routes-backendmainpy-fastapi): the FastAPI backend
5. [Dashboard](#dashboard-frontend-react--vite--typescript): the React desk
6. [Safety and guardrails](#safety-and-guardrails)
7. [Results of the full run (Problem 9)](#results-of-the-full-run-problem-9)
---

## Tables

| Table | Fields | Why it matters for the agents |
|---|---|---|
| `desk` | `date_today`, `notes` | Sets "today" for every agent, so overdue and due-soon checks agree. |
| `tickets` | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at` | The work board: Boss reads each open ticket and routes it, and the link fields point to the other tables. |
| `inventory` | `sku`, `name`, `size`, `qty`, `location` (key: `sku` + `size`) | Inventory checks stock by SKU and size to find shortfalls. |
| `pricing` | `sku`, `unit_cost`, `list_price` | Accounting checks margins, so no discount drops a price below cost. |
| `vendors` | `id`, `name`, `specialty`, `lead_days` | Inventory picks who can restock an item and how many days it takes. |
| `invoices` | `id`, `vendor_id`, `amount`, `due_date`, `status`, `description` | Unpaid bills. A vendor with an open invoice won't ship, and past-due bills count as overdue. |
| `leases` | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | Facilities tracks rent for the shop space and when it's due. |
| `cash_accounts` | `name`, `balance`, `date` | Accounting checks this before any payment, and the pay tool refuses if the balance would go negative. |
| `payments` | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | Record of every payment a human approved. It starts empty, and `approved_by` shows who signed off. |
| `approval_requests` *(board table)* | `id`, `kind`, `ref_id`, `ticket_id`, `vendor_id`, `sku`, `size`, `qty`, `amount`, `reason`, `requested_by`, `status`, `created_at`, `decided_by`, `decided_at`, `decision_note`, `payment_id`, `expected_arrival` | Payments and purchase orders agents *prepared*, waiting for a person. Only `approve_and_pay` turns one into a payment. |
| `drafts` *(board table)* | `id`, `ticket_id`, `recipient`, `subject`, `body`, `author`, `status`, `created_at` | Messages to customers, the landlord and vendors. Always `draft`, never sent. |
| `ticket_updates` *(board table)* | `id`, `ticket_id`, `old_status`, `new_status`, `note`, `updated_by`, `created_at` | Every status change Boss made, and why. |
| `store_tasks` *(board table)* | `id`, `area`, `task`, `priority`, `created_by`, `ticket_id`, `status`, `created_at`, `done_by`, `done_at` | Upkeep tasks (spills, hangers, trash) Facilities puts on the board for staff. |

---

The four *board tables* aren't in the original file. The MCP server creates them in the working copy on first use, and a reset removes them.

## Starting data (snapshot of the original)

- **Cash:** `checking` = **$3,400.00** (as of 2026-08-31). This is the only account.
- **Inventory:**

  | SKU | Item | S | M | L | XL | OS | Location |
  |---|---|---|---|---|---|---|---|
  | CC-HOOD-NAVY | Basic Hoodie Big Yale | 4 | **8** | 14 | 6 | — | Aisle A |
  | CC-TEE-WHITE | Classic Bulldog Tee | **0** | 5 | 3 | 2 | — | Aisle B |
  | CC-HAT-BLUE | Yale Cap | — | — | — | — | 40 | Aisle C |
  | CC-MUG-CREST | Crest Mug | — | — | — | — | **0** | Aisle D |

- **Pricing:**

  | SKU | Unit cost | List price | Margin per unit |
  |---|---|---|---|
  | CC-HOOD-NAVY | $22.00 | $58.00 | $36.00 (62%) |
  | CC-TEE-WHITE | $8.00 | $28.00 | $20.00 (71%) |
  | CC-HAT-BLUE | $6.00 | $22.00 | $16.00 (73%) |
  | CC-MUG-CREST | $3.50 | $14.00 | $10.50 (75%) |

- **Vendors:**

  | ID | Vendor | Specialty | Lead days |
  |---|---|---|---|
  | 1 | Bulldog Print Co | apparel reprint | 5 |
  | 2 | Elm City Gifts | mugs and small goods | 3 |
  | 3 | QuickShip CT | local courier | 1 |

- **Invoices:** #501, Bulldog Print Co (vendor 1), **$840.00**, due **2026-08-28**, status `open`, "Rush reprint CC-TEE-WHITE S". It is **3 days overdue**. The invoice has no quantity field. At the $8 unit cost, $840 would be about 105 tees, so it's a batch reprint of size S, not one shirt (a rush job may cost more per tee).
- **Leases:** #1 Chapel Street shop, landlord Elm City Properties, **$2,400.00/month**, next due **2026-09-02**, in 2 days.
- **Payments:** none yet.

---

## The three open tickets and how they link

### Ticket 101 — customer order (Tauhid Zaman, "Bulldog tee")
- **Links:** `sku` CC-TEE-WHITE + `size` S → `inventory`, `pricing`. `invoice_id` 501 → `invoices` → `vendor_id` 1 → `vendors`.
- **What the data shows:** size S has **0 in stock**. The restock is already on invoice 501, a rush reprint of that exact tee, but the invoice is unpaid and overdue, so Bulldog Print Co won't ship.
- **Agents involved:** Inventory (shortfall), Accounting (prepare the $840 payment for approval), Customer Service (draft an update to the customer). After payment, vendor 1's lead time is 5 days, so the tee would arrive about **2026-09-05**.

### Ticket 102 — rent notice (Elm City Properties, "Rent due")
- **Links:** `lease_id` 1 → `leases`.
- **What the data shows:** **$2,400** rent is due **2026-09-02**. It isn't overdue yet, but it's due soon.
- **Agents involved:** Facilities (lease), Accounting (prepare the $2,400 payment for approval, check cash).

### Ticket 103 — price override (Yale AI Club, "Bulk hoodie discount")
- **Links:** `sku` CC-HOOD-NAVY + `size` M + `qty` 20 → `inventory`, `pricing`. A restock would go through `vendors` (vendor 1, apparel).
- **What the data shows:** they want **20** but only **8** size M are in stock, a **shortfall of 12**. List price is $58 and cost is $22, so any discount has to stay above $22/unit. The restock vendor is Bulldog Print Co, the same vendor blocked by unpaid invoice 501.
- **Agents involved:** Inventory (shortfall + vendor), Accounting (margin check on the discount, purchase order), Boss (final call on the price), Customer Service (draft a reply to the club).

---

## Things the agents need to watch for

1. **Cash is tight.** $3,400 covers invoice 501 plus rent ($840 + $2,400 = $3,240), which leaves **$160**. A purchase order for 12 more hoodies at cost ($264) would push the total to **$3,504**, which is more than the shop has. The pay tool must refuse rather than go negative, and Boss has to set priorities.
2. **Invoice 501 blocks two tickets.** Until it's paid, Bulldog Print Co won't ship the tee (101) or reprint hoodies (103).
3. **Every payment needs human approval.** That goes through the dashboard, which writes a row in `payments`, lowers `cash_accounts.balance`, and marks the invoice or lease as paid.
4. **Nothing is sent.** Customer and vendor messages stay as drafts on the board.
5. **Crest Mug is out of stock (0)**, but no ticket asks for it.

---

## MCP server tools (`mcp_server/server.py`)

Built with FastMCP. The server reads the working copy, `data/campus_customs_new.db`, and every agent on the team uses these tools. All three only read data. Tools that pay bills and update tables come in later problems.

### 1. `get_open_tickets()`
- **Tables it reads:** `tickets` (rows where `status = 'open'`, with every field: `type`, `requester`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `notes`) and `desk` (`date_today`).
- **Tickets it unlocks:** **101, 102 and 103**. It's the first call for every ticket.
- **Why it's the right tool:** Boss can't route anything until it sees the board. This one call returns each ticket's link fields (CC-TEE-WHITE size S plus invoice 501 for ticket 101, lease 1 for ticket 102, 20 × CC-HOOD-NAVY size M for ticket 103) together with today's date, 2026-08-31. From that, Boss can send 101 and 103 to Inventory and Accounting and 102 to Facilities and Accounting, and every agent measures "overdue" from the same day.

### 2. `check_stock(sku, size)`
- **Tables it reads:** `inventory` (`qty` and `location` for one `sku` + `size`) and `pricing` (`unit_cost` and `list_price` for that `sku`).
- **Tickets it unlocks:** **101** (Bulldog tee) and **103** (bulk hoodie discount).
- **Why it's the right tool:**
  - **Ticket 101:** it returns **0** on hand for CC-TEE-WHITE size S in Aisle B. That proves Tauhid's order can't be filled from the shelf and has to wait for the reprint on invoice 501.
  - **Ticket 103:** it returns **8** on hand for CC-HOOD-NAVY size M against the 20 the Yale AI Club asked for, a shortfall of 12. The same call also gives the **$22 cost** and **$58 list price**, so Accounting can check any discount against the $22 floor without a second lookup.

### 3. `get_invoice(invoice_id)`
- **Tables it reads:** `invoices` (`amount`, `due_date`, `status`, `description`), joined to `vendors` on `vendor_id` (`name`, `specialty`, `lead_days`), plus `desk` (`date_today`) to work out `days_overdue`.
- **Tickets it unlocks:** **101** directly, through its `invoice_id` 501. It also explains why **103**'s restock is stuck.
- **Why it's the right tool:** ticket 101 points at invoice 501. This tool shows the invoice is **$840** to **Bulldog Print Co**, was due **2026-08-28**, is still `open` and **3 days overdue**, and that the vendor has a **5-day lead time**. That's exactly what Accounting needs to prepare the payment for human approval, and what Customer Service needs to tell Tauhid the tee can arrive about 5 days after payment. It also shows that the only apparel vendor is blocked until the bill is paid, which holds up the hoodie reprint for ticket 103 too.

### Gap for the next tools (filled in Problem 5)
Ticket **102** (rent) only gets as far as `get_open_tickets`, which returns `lease_id` 1. No tool yet reads `leases` (the $2,400 rent due 2026-09-02) or `cash_accounts` (the $3,400 in checking). Those tools came in Problem 5 (`get_lease`, `get_cash_balance`, `request_rent_payment`, `approve_and_pay` and more). See the full tool list below.

If a SKU/size or invoice isn't in the database, the tools return an error instead of making something up.

---

## Agent team (`backend/`)

Built with Pydantic AI. **Every agent uses `gpt-6-luna` through Portkey** (`PORTKEY_API_KEY` in `.env`), and no other model is used. Every shop fact comes from the `campus-customs` MCP server above, which works on `data/campus_customs_new.db`. There is no second tools layer.

| Agent | File | Prompt | Job | MCP tools it is given |
|---|---|---|---|---|
| **Boss** | `backend/boss.py` | `backend/prompts/boss.md` | Oversees the whole shop. Routes tickets, makes final calls (discount price, which bills get paid first), and sets ticket status. Gets the 24-hour bills alert, and touches base with Inventory when stock is low. | `get_open_tickets`, `get_ticket`, `update_ticket_status`, `check_stock`, `get_invoice`, `get_lease`, `get_cash_balance`, `check_discount`, `list_approval_requests`, `list_drafts`, `get_bills_due`, `get_low_stock`, `list_store_tasks` |
| **Inventory** | `backend/inventory.py` | `backend/prompts/inventory.md` | Checks stock by SKU and size, works out shortfalls, and runs the low-stock watch: restock vendor, lead time, `will_ship`, earliest arrival, suggested quantity, and which customers are affected. | `get_ticket`, `check_stock`, `list_inventory`, `list_vendors`, `get_invoice`, `get_low_stock` |
| **Accounting** | `backend/accounting.py` | `backend/prompts/accounting.md` | Owns the bill calendar. Files payment requests early enough that a person can approve them before the due date. Keeps upcoming bills funded before any purchase, and checks margins. | `get_ticket`, `get_invoice`, `get_cash_balance`, `check_discount`, `check_stock`, `list_vendors`, `get_lease`, `list_approval_requests`, `request_invoice_payment`, `request_rent_payment`, `request_purchase_order`, `get_bills_due` |
| **Facilities** | `backend/facilities.py` | `backend/prompts/facilities.md` | The lease and rent notices, plus store upkeep: floors clear of spills, no hangers on the floor, trash in trash cans, aisles clear. Puts checklist tasks on the board for staff. | `get_ticket`, `get_lease`, `get_cash_balance`, `save_draft`, `list_drafts`, `create_store_task`, `list_store_tasks`, `list_inventory` |
| **Customer Service** | `backend/customer_service.py` | `backend/prompts/customer_service.md` | Makes sure every open customer ticket gets a reply draft the same shop day, and drafts proactive notes to customers when something they asked for runs low. Never sends anything. | `get_ticket`, `check_stock`, `list_inventory`, `list_approval_requests`, `list_drafts`, `save_draft`, `get_low_stock`, `get_open_tickets` |

**Full connectivity:** every agent also has `ask_teammate(teammate, request)`, so any agent can hand work to any other agent and get a structured report back.

**Other backend files:**
- `backend/team.py`: the model, the MCP connection, delegation, and the agent loop.
- `backend/models.py`: data types (`AgentReport`, `BossDecision`, `Fact`, `AuditEvent`, `TeamDeps`, `TeamBudget`).
- `backend/audit.py`: the audit trail writer.
- `backend/run.py`: the command line, with three modes:
  - `--ticket 101`: work one ticket
  - `--all`: work every open ticket
  - `--daily`: the daily operations check across the whole shop

### Boss oversight: what Boss watches besides tickets
| Duty | How it works |
|---|---|
| **Bills due within 24 hours** | Every run starts with `get_bills_due(within_days=1)`. If any bill is due today, due tomorrow, or overdue, Boss gets a **BILLS DUE ALERT** before any other work. Boss has Accounting file any missing request and tells the person which request IDs to approve today, in order. (The shop date has no clock time, so "within 24 hours" means due today or tomorrow.) With the starting data, the alert fires for invoice 501, which is 3 days overdue. Rent, due in 2 days, is not in the 24-hour window. |
| **Bills coming up / no overspending** | Accounting reviews `get_bills_due(within_days=30)` and files a request for anything overdue or due within 7 days. The purchase-order tool refuses any order that would spend cash those bills need. |
| **Low stock (touch base with Inventory)** | `get_low_stock` lists everything at 5 units or fewer. Boss asks Inventory for the vendor, lead time, earliest arrival, and affected customers. **"Hasn't sold" can't be measured:** the database has no sales history, so the agents are told never to call an item unsold. They may only flag it for a person to review. |
| **Clean, safe store (Facilities)** | Facilities puts one checklist task per area (Aisles A–D, the entrance and the checkout) on the board with `create_store_task`. Spills are high priority. A person does the work and marks it done. |
| **Customers looked after (Customer Service)** | Every open customer ticket gets a reply draft. When an item a customer asked for is low or out, Customer Service drafts a proactive note to that customer. |

## API routes (`backend/main.py`, FastAPI)
Start it from `backend/` with `uvicorn main:app --reload --port 8000`. The React dashboard calls `http://localhost:8000`. CORS allows only the Vite page origin, `http://localhost:5173` (and `127.0.0.1:5173`). Every route reads and writes the shop through the same MCP server (one server process for the life of the backend).

| Route | What it does | MCP tool(s) |
|---|---|---|
| `GET /tickets` | The tickets, each with `status` and `state` (`open` or `resolved`) | `list_tickets` |
| `GET /tickets/{id}` | One ticket with its status history, drafts and approval requests | `get_ticket` |
| `POST /tickets/{id}/run` | Runs the agent team on that ticket and returns Boss's decision and the updated ticket. If a bill is due within 24 hours (or overdue) and has no payment request, Boss gets the bills alert first. One run at a time (409 if busy). | the agents' tools |
| `GET /events?limit=&ticket_id=&run_id=&after=` | Recent agent events from `output/audit_trail.json`, newest first: what each agent said, the tools it called with their arguments and results, handoffs, guardrails, and tokens. `after` lets the board fetch only new events. | — (reads the audit file) |
| `GET /approvals?status=pending` | Payment and purchase requests the agents prepared | `list_approval_requests` |
| `POST /approvals/{id}/approve` body `{"approved_by": "<person>"}` | **The only route that moves cash.** A person clicked Approve: writes `payments`, lowers cash, and marks the invoice paid or moves the lease date. Refused for an agent's name, a request that isn't pending, or a payment that would make cash negative. Returns the new balance. | `approve_and_pay` |
| `POST /approvals/{id}/reject` body `{"rejected_by", "reason"}` | A person rejects. No money moves. | `reject_request` |
| `GET /cash` | Current checking balance from `cash_accounts`, plus pending total and payments made | `get_cash_balance` |
| `POST /reset` | Copies `data/campus_customs.db` over `data/campus_customs_new.db` for a fresh run. Clears requests, drafts, tasks and status history. **The audit trail is not wiped** (runs are told apart by `run_id`). Blocked while agents are running. | — |

**Tested** with uvicorn started from `backend/`, on a throwaway copy of the database:
- `/tickets` returned 101–103 as open, and `/cash` returned $3,400.
- Approving with the name "Accounting" was refused, and so was a blank name.
- Approving invoice 501 as a person changed cash $3,400 → $2,560, and approving it a second time was refused.
- Reject worked, and `/reset` restored $3,400 and cleared the requests.
- With a scripted model (no tokens), `POST /tickets/101/run` ran the full chain Boss → Accounting → Inventory → Customer Service, filed 1 request and 1 draft, and set the ticket to `waiting_on_approval`. `/events` showed every step. A second run skipped the bills alert, because the request already existed.

## Dashboard (`frontend/`, React + Vite + TypeScript)
Run it with `cd frontend && npm install && npm run dev`, then open http://localhost:5173 (the backend must be running on :8000). The design write-up is in `output/design.md`.

| Part | What it shows | Routes it calls |
|---|---|---|
| Ticket board | All 3 tickets with type, requester, notes and status. **Run team** button on each. A yellow **Resolved** stamp drops onto a ticket when its run finishes. | `GET /tickets`, `POST /tickets/{id}/run` |
| Agent team | One card per agent: idle, working (pulsing ring and typing dots), waiting on a teammate, or done (check mark). Each card shows its latest line and the tools it has used. Above the cards, the handoff chain builds live (e.g. Boss → Accounting → Inventory → Customer Service). | `GET /events` (polled every 0.8 s during a run) |
| Live activity | Every step as it happens, newest on top and indented by handoff depth: what each agent said, each tool call with its arguments and result, handoffs, guardrails, and the running token count | `GET /events` |
| What the team did | After the run: the bills-due alert (if any), Boss's final call and **your next step**, a short card per agent (summary, actions, request and draft IDs), and who was not called | run response + `GET /events?run_id=` |
| Checking balance | Animated balance from `cash_accounts`, pending total, what's left if everything is approved, and payments made | `GET /cash` |
| Approvals | Requests waiting for a person, with **Approve & pay** and **Reject**. After approval the balance counts down to the new amount and a confirmation appears. | `GET /approvals`, `POST /approvals/{id}/approve`, `/reject` |
| Reset data | Restores the original database for a fresh run | `POST /reset` |

Colors are Yale blue, Bulldog yellow, and grays. Motion includes a drifting header gradient, a moving yellow stripe, a progress bar during runs, a spinning border on the running ticket, pulsing active agents, dashed handoff arrows, feed rows that slide in, the stamp drop, the count-up balance, and toasts. It respects `prefers-reduced-motion`.

**Tested** in the browser against a test-only copy of the backend that used scripted agents (no tokens) and a throwaway database:
- Ticket 101 streamed live, and the chain built step by step: Boss → Accounting → Inventory → Customer Service.
- The ticket got the Resolved stamp, and the summary showed every agent's work.
- One approval appeared. Approving as "Cedric" moved the balance $3,400.00 → $2,560.00 and listed the payment.

## How the team works a ticket

### Ticket flow: first owner, then hand off
Boss doesn't send a ticket to everyone. It finds the root cause and sends the ticket to the **one** agent who owns that problem. Each agent does its part, then hands off to the next agent who must act, instead of bouncing the work back to Boss. Boss only steps back in for its own decisions (like a discount price). The expected chain for each open ticket is written out in `output/desk_tickets.html`:

| Ticket | Root cause | Boss calls first | Expected chain |
|---|---|---|---|
| 101 · tee order | Invoice 501 is unpaid, so the reprint is held | **Accounting** | Accounting (payment request) → Inventory (earliest arrival) → Customer Service (draft to Tauhid) → Boss sets `waiting_on_approval` |
| 102 · rent notice | Rent due 2026-09-02 | **Facilities** | Facilities (checks lease) → Accounting (rent request) → Facilities (landlord draft) → Boss sets `waiting_on_approval` |
| 103 · hoodie discount | Only 8 of 20 on hand; restock blocked by the unpaid invoice and by cash | **Inventory** | Inventory (shortfall) → Accounting (margins, cash, no PO) → Boss decides price → Customer Service (draft to club) → Boss sets `in_progress` |

### Agent loop
Each agent run steps through Pydantic AI's loop with `agent.iter()`:
1. The prompt goes in.
2. The model replies, often with tool calls.
3. The MCP tools (or `ask_teammate`) run, and their results go back to the model.
4. Steps 2–3 repeat until the agent returns its structured report.

A teammate asked with `ask_teammate` runs the same loop one level deeper. It shares the run's token budget and is recorded in the same audit trail.

### Audit trail: `output/audit_trail.json`
A JSON array that is **appended to on every step and never wiped**. Each row has:
- `timestamp`, `run_id`, `ticket_id`
- `agent`, `parent_agent`, `depth`, `step`
- `event`: `run_start`, `user_prompt`, `model_request`, `model_response`, `tool_call`, `tool_result`, `delegation`, `guardrail`, `run_end` or `error`
- `detail`: the prompt, the model's text, each tool's name, arguments and output, refusals, and the final report
- `usage`: the team's running token count

Long values are cut at 2,000 characters. A finished agent's report (`run_end`) has been kept whole since Problem 9. Before that, a few long Boss reports were cut to text, and `GET /events` now still pulls their summary out.

---

## All MCP tools and the tables they use

`mcp_server/server.py` now has **24 tools**. The first 3 are from Problem 3, and the rest were added for the agent team.

| # | Tool | Tables | What it does | Used by |
|---|---|---|---|---|
| 1 | `get_open_tickets` | `tickets`, `desk` | Every open ticket and `date_today` | Boss, Customer Service |
| 2 | `check_stock` | `inventory`, `pricing` | Stock, location, cost and list price for one SKU and size | Boss, Inventory, Accounting, Customer Service |
| 3 | `get_invoice` | `invoices`, `vendors`, `desk` | One invoice with vendor, lead days and days overdue | Boss, Inventory, Accounting |
| 4 | `get_ticket` | `tickets`, `ticket_updates`, `drafts`, `approval_requests`, `desk` | One ticket and everything already done on it | All |
| 5 | `update_ticket_status` | `tickets`, `ticket_updates` | Sets a ticket's status (fixed list) with a note, and keeps the history | Boss |
| 6 | `list_inventory` | `inventory` | All sizes of a SKU, or the whole catalog | Inventory, Facilities, Customer Service |
| 7 | `list_vendors` | `vendors`, `invoices` | Each vendor's specialty, lead days, open invoices, and `will_ship` | Inventory, Accounting |
| 8 | `get_cash_balance` | `cash_accounts`, `payments`, `approval_requests` | Balance, payments made, pending total, and the balance if everything pending were paid | Boss, Accounting, Facilities |
| 9 | `check_discount` | `pricing` | Discount %, margin per unit and in total, and a below-cost flag | Boss, Accounting |
| 10 | `get_lease` | `leases`, `desk` | Rent, next due date, days until due, overdue flag | Boss, Accounting, Facilities |
| 11 | `request_invoice_payment` | `invoices`, `tickets`, `cash_accounts`, `approval_requests` | Files a request to pay an invoice. **Pays nothing.** | Accounting |
| 12 | `request_rent_payment` | `leases`, `tickets`, `cash_accounts`, `approval_requests` | Files a request to pay rent. **Pays nothing.** | Accounting |
| 13 | `request_purchase_order` | `vendors`, `invoices`, `leases`, `inventory`, `pricing`, `tickets`, `cash_accounts`, `approval_requests` | Files a restock order (qty × unit cost) with the arrival date. Refused if the vendor has an unpaid invoice, or if it would spend cash that upcoming bills need. **Pays nothing.** | Accounting |
| 14 | `list_approval_requests` | `approval_requests` | Requests by status | Boss, Accounting, Customer Service |
| 15 | `save_draft` | `tickets`, `drafts` | Saves a message on the board. **Never sent.** | Facilities, Customer Service |
| 16 | `list_drafts` | `drafts` | Drafts for a ticket, or all of them | Boss, Facilities, Customer Service |
| 17 | `get_bills_due` | `invoices`, `vendors`, `leases`, `approval_requests`, `cash_accounts`, `desk` | Every unpaid invoice and rent payment due within N days (overdue first), whether each has a request, and whether cash covers them | Boss, Accounting, and the runner's 24-hour alert |
| 18 | `get_low_stock` | `inventory`, `tickets` | Every SKU and size at or below 5 units, with the open tickets that need it. Says plainly that there is no sales history | Boss, Inventory, Customer Service |
| 19 | `create_store_task` | `store_tasks`, `tickets` | Puts an upkeep task (spills, hangers, trash) on the board for staff, with priority low, normal or high | Facilities |
| 20 | `list_store_tasks` | `store_tasks` | Store tasks by status, high priority first | Boss, Facilities |
| 21 | `approve_and_pay` | `approval_requests`, `payments`, `cash_accounts`, `invoices`, `leases`, `vendors`, `desk` | **Human only.** Pays an approved request: writes `payments`, lowers cash, then marks the invoice paid, moves the lease to next month, or sets the purchase order's arrival. Refuses a negative balance. | Dashboard (a person) |
| 22 | `reject_request` | `approval_requests` | **Human only.** Rejects a request. No money moves. | Dashboard (a person) |
| 23 | `complete_store_task` | `store_tasks` | **Human only.** Marks a store task done, by the person who did it | Dashboard (a person) |
| 24 | `list_tickets` | `tickets`, `desk` | Every ticket (open and finished) with its status and a `state` of open or resolved | Dashboard (`GET /tickets`) |

**Board tables added by the server:** `approval_requests`, `drafts`, `ticket_updates` and `store_tasks`. The server creates them in the working copy on first use (`CREATE TABLE IF NOT EXISTS`). They are not in the original database, so restoring `campus_customs_new.db` from `campus_customs.db` clears them too.

**Shop policy values** (set in `mcp_server/server.py`):
- Low stock = 5 units or fewer on hand.
- Cash for bills due within 30 days is held back from new orders.
- A purchase order is capped at 200 units.

---

## Safety and guardrails

These are the controls a real business puts on staff who handle real money and customers. Each one is enforced in code, not just in a prompt.

### Money
1. **Separation of duties.** Agents can only *request* a payment. `approve_and_pay`, `reject_request` and `complete_store_task` are human-only:
   - They are left out of every agent's tool list.
   - `make_agent` refuses to build an agent that has them.
   - `stamp_identity` blocks them if called anyway.
   - The server refuses a name that belongs to an agent.
2. **No typed amounts.** Request amounts are read from the database (invoice amount, monthly rent, qty × unit cost). An agent cannot inflate or invent a number.
3. **No negative cash.** Requests larger than the balance are refused. `approve_and_pay` checks the balance again at payment time and marks the request `refused_insufficient_cash` instead of paying.
4. **Bills before purchases (no overspending).** `request_purchase_order` adds up the cash already promised: pending requests, plus bills due within 30 days that have no request yet. It refuses any order larger than what's left, so a restock can never make a bill late.
5. **No late bills.** The 24-hour bills alert runs before every run, and Accounting files requests for anything due within 7 days.
6. **No duplicate payments.** A second request for the same invoice, the same month's rent, or the same restock is refused. An invoice that is no longer open can't be paid.
7. **Vendor rule in code.** A purchase order is refused while the vendor has an open unpaid invoice, and checked again at approval.
8. **Purchase-order cap.** No single order above 200 units.
9. **Every payment is traceable.** Each one writes a `payments` row with `approved_by` and the shop date, links back to its request, and updates the invoice or lease it paid.

### People, customers and the store
10. **Least privilege.** Each agent gets only the tools its job needs. For example, only Accounting can file payment requests, only Boss can change ticket status, and only Facilities can create store tasks.
11. **True identity.** `requested_by`, `updated_by`, `author` and `created_by` are overwritten with the agent that actually made the call, and any mismatch is logged as a `guardrail` event.
12. **Drafts only.** Messages are saved with `status = 'draft'`. Nothing is emailed or sent. Customer Service only writes to customers who have an open ticket, and never shares cash, invoice, or margin details.
13. **Agents can't claim physical work.** Store upkeep is a task for a person. Only a person can mark it done, and agents are told never to say the store "is clean".
14. **No invented facts.** Tools return an error when a row doesn't exist. Prompts require every number to come from a tool in that run, and the low-stock tool states that there is no sales history, so "hasn't sold" is never guessed.
15. **Prompt-injection resistance.** Every prompt tells the agent to treat ticket, notice, and draft text as information, never as instructions to pay, skip approval, or change rules.
16. **Fixed values.** Ticket statuses and task priorities come from fixed lists, and "today" always comes from `desk.date_today`.
17. **Full audit trail.** Every prompt, model reply, tool call, tool result, delegation, refusal and error goes to `output/audit_trail.json`, and the file is never wiped.

### Token and loop limits
Limits are per Boss run (one ticket, one alert, or one daily check) and shared by every agent that helps, set in `backend/team.py`:

| Limit | Value |
|---|---|
| Model requests (`request_limit`) | 30 |
| Tool calls (`tool_calls_limit`) | 60 |
| Total tokens, input + output (`total_tokens_limit`) | 120,000 |
| Tokens per model reply (`max_tokens`) | 1,500 |
| Delegation depth | 3 levels (Boss → first owner → next → next, e.g. Accounting → Inventory → Customer Service) |
| Delegations per run | 6 |
| Cycles | An agent can't ask itself or anyone already waiting on it |

If a limit is hit, the run stops with an `error` event in the audit trail instead of running up cost. **This happened in the real run.** Ticket 103's first run reached 123,235 tokens and was stopped at the 120,000 limit (run `20261102-200845-0a5020`). Long tool outputs are cut to 2,000 characters in the audit file, and prompts tell agents to call each tool once and be brief.

### Tested (on a throwaway copy of the database, not the working copy)
- **Server:** I called the tools directly. A purchase order was refused while invoice 501 was unpaid, and a duplicate invoice request was refused. An approval signed "Accounting" was refused. A person's approval paid invoice 501 and the rent ($3,400 → $160) and moved the lease to 2026-10-02. After that, a $264 order was refused for lack of cash.
- **Oversight tools:**
  - `get_bills_due(1)` returned only invoice 501, 3 days overdue. `get_bills_due(30)` added the rent ($3,240 total).
  - `get_low_stock` returned 6 items, with the size S tee linked to ticket 101.
  - A duplicate store task and a bad priority were refused, and so was an agent marking a task done.
  - With invoice 501 paid ($2,560 cash) but rent not yet requested, a $264 hoodie order was refused: "only $160.0 is free to spend". A $110 order fit.
- **Agent loop (scripted model, no tokens):** Boss delegated to Inventory, and Inventory's attempt to delegate back to Boss was blocked. Boss's call to `approve_and_pay` failed because the tool doesn't exist for agents, and a wrong `updated_by` was corrected to "Boss". Every step was appended to the audit file.
- **Live `gpt-6-luna` check:** Inventory on ticket 101 correctly reported 0 on hand, invoice 501 covering the reprint, and the vendor blocked until it's paid. It took 3 requests and 7,284 tokens.


---

## Results of the full run (Problem 9)

On Nov 2, 2026, the database was reset to the original values, and then all three tickets were run from the dashboard with real `gpt-6-luna` calls. Every step is in `output/audit_trail.json`, which now has 962 events. That includes two earlier ticket 101 runs from before the reset, whose effects the reset cleared.

| Ticket | Boss called first | Handoff chain | Person approved | Cash | Final status |
|---|---|---|---|---|---|
| #101 Bulldog tee | Accounting | Boss → Accounting → Inventory → Customer Service | Request #1, invoice 501, $840.00 (Cedric) | −$840.00 | **resolved** |
| #102 Rent due | Facilities | Boss → Facilities → Accounting → Facilities | Request #2, rent, $2,400.00 (Cedric) | −$2,400.00 | **resolved** |
| #103 Bulk hoodies | Inventory | Boss → Inventory → Accounting → Boss → Customer Service | None (the purchase order was refused for cash) | $0.00 | **in_progress** (left open by the user's decision) |

**Cash:** $3,400.00 (start, after reset) − $840.00 − $2,400.00 = **$160.00**. That equals `cash_accounts.balance`. The `payments` table totals $3,240.00, and no requests are pending.

**Tokens:** 7 runs after the reset used 471,988 tokens in total. The cheapest was ticket 102's close-out (24,390, Boss alone). The most expensive was ticket 103's first run, which the 120K limit stopped.

**Guardrails seen in the real run:**
- **Token limit:** stopped ticket 103's first run at 120,000.
- **Cycle guardrail:** refused seven attempts to hand work back to an agent already waiting in the chain, for example Customer Service → Inventory on ticket 101.
- **Delegation cap:** turned away Inventory's attempt to ask Accounting a second time on ticket 103.
- **Cash guardrail:** `request_purchase_order` refused the 12-hoodie order: "$264.0 is more than the cash on hand".
- **People only:** both payments were approved by a person (`approved_by = Cedric`). No agent can call `approve_and_pay`.

**What didn't go as expected (and fixes):**
- **The bills-due alert's handoff left out the ticket ID**, so Accounting's first request attempt was refused. The request was filed in the ticket run instead. Fix to consider: have the alert pass the ticket linked to each bill.
- **Ticket 101's close-out sent the ticket down the chain again** instead of only confirming, which cost 52,525 tokens and produced a second customer draft. Ticket 102's close-out followed the re-check rule exactly.
- **Boss kept ticket 103 open:** it treated "can't fund the other 12 hoodies" as unfinished work. Per the user's decision, the ticket was left `in_progress` rather than re-run.
- **Boss's status rule was clarified mid-run:** `resolved` = the shop's part is done (payments paid, replies drafted, decision made).

**Output files:**

| File | What it holds |
|---|---|
| `output/desk_tickets.html` | Expected (written before the run) and Actual (from the run) for each ticket, plus the Cash tab with the itemized ledger |
| `output/resolved_tickets.json` | For each ticket: ID, final status, outcome, each agent's contribution, tools, human approvals, cash change, drafts, status history, run IDs. The cash ledger is checked against `cash_accounts`. |
| `output/resolved_board.html` | Screenshots of the React board for each ticket (`output/screenshots/`) |
| `output/audit_trail.json` | Every step of every real run, append-only |
| `output/design.md` | The dashboard design write-up |
| `output/mcp_smoke.json` | Problem 4's MCP tool smoke test |
