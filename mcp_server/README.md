# Campus Customs MCP Server

This is the toolbox for the Campus Customs agent team. Every agent (Boss, Inventory, Accounting, Facilities and Customer Service) works the tickets by calling these tools instead of reading the database directly. The tools only return what is in the database, and they return an error if a row isn't there.

## Database

- **Uses:** `data/campus_customs_new.db`, the working copy. The tools read it and update it. Set `CAMPUS_DB_PATH` to point the server at a different copy, for example when testing.
- **Never touches:** `data/campus_customs.db`, the original. Copy it over the working copy to reset before a full run.
- **"Today"** is `desk.date_today` (2026-08-31), not the computer clock.
- **Board tables:** the server adds `approval_requests`, `drafts`, `ticket_updates` and `store_tasks` to the working copy on first use. A reset removes them.

## Tools (24)

### Read
| Tool | Tables | Returns |
|---|---|---|
| `get_open_tickets()` | `tickets`, `desk` | Every open ticket with its link fields, plus `date_today` |
| `list_tickets()` | `tickets`, `desk` | Every ticket, open or finished, with `status` and `state` (open/resolved). Used by the dashboard |
| `get_ticket(ticket_id)` | `tickets`, `ticket_updates`, `drafts`, `approval_requests`, `desk` | One ticket with its status history, drafts and requests |
| `check_stock(sku, size)` | `inventory`, `pricing` | Units on hand, location, `unit_cost`, `list_price` |
| `list_inventory(sku=None)` | `inventory` | Every size of a SKU, or the whole catalog |
| `list_vendors()` | `vendors`, `invoices` | Specialty, `lead_days`, open invoices, and `will_ship` |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | Amount, due date, status, vendor, `lead_days`, `days_overdue` |
| `get_cash_balance()` | `cash_accounts`, `payments`, `approval_requests` | Balance, payments made, pending total, balance if all pending were paid |
| `check_discount(sku, qty, unit_price)` | `pricing` | Discount %, margin per unit and in total, below-cost flag |
| `get_lease(lease_id)` | `leases`, `desk` | Rent, next due date, days until due, overdue flag |
| `list_approval_requests(status="pending")` | `approval_requests` | Requests by status |
| `list_drafts(ticket_id=None)` | `drafts` | Message drafts |
| `get_bills_due(within_days=1)` | `invoices`, `vendors`, `leases`, `approval_requests`, `cash_accounts`, `desk` | Unpaid invoices and rent due within N days (overdue first), whether each has a request, and whether cash covers them. `within_days=1` is the 24-hour alert |
| `get_low_stock(threshold=5)` | `inventory`, `tickets` | Items at or below the threshold, with open tickets that need them (no sales history exists) |
| `list_store_tasks(status="open")` | `store_tasks` | Store upkeep tasks, high priority first |

### Write to the board (no money moves)
| Tool | Tables | Does |
|---|---|---|
| `update_ticket_status(ticket_id, status, note, updated_by)` | `tickets`, `ticket_updates` | Sets the status (`open`, `in_progress`, `waiting_on_approval`, `waiting_on_vendor`, `resolved`, `declined`) with a note |
| `request_invoice_payment(invoice_id, ticket_id, reason, requested_by)` | `invoices`, `tickets`, `cash_accounts`, `approval_requests` | Files a request for the invoice amount |
| `request_rent_payment(lease_id, ticket_id, reason, requested_by)` | `leases`, `tickets`, `cash_accounts`, `approval_requests` | Files a request for the monthly rent |
| `request_purchase_order(vendor_id, sku, size, qty, ticket_id, reason, requested_by)` | `vendors`, `invoices`, `leases`, `inventory`, `pricing`, `tickets`, `cash_accounts`, `approval_requests` | Files a restock request for qty × unit cost, with the expected arrival date. Refused while the vendor has an unpaid invoice, or if it would spend cash that bills due within 30 days need |
| `save_draft(ticket_id, recipient, subject, body, author)` | `tickets`, `drafts` | Saves a message draft. Never sent |
| `create_store_task(area, task, priority, created_by, ticket_id=None)` | `store_tasks`, `tickets` | Puts an upkeep task (spills, hangers, trash) on the board for staff |

### Human only (the dashboard, never the agents)
| Tool | Tables | Does |
|---|---|---|
| `approve_and_pay(request_id, approved_by)` | `approval_requests`, `payments`, `cash_accounts`, `invoices`, `leases`, `vendors`, `desk` | Pays a pending request. Writes `payments`, lowers cash, and marks the invoice paid, moves the lease's next due date, or sets the purchase order's arrival. Refuses if cash would go negative or the approver is an agent |
| `reject_request(request_id, rejected_by, reason)` | `approval_requests` | Rejects a request. No money moves |
| `complete_store_task(task_id, done_by)` | `store_tasks` | Marks a store task done by the person who did it |

## Rules built into the tools

- Amounts are always read from the database, never typed in by an agent.
- No duplicate requests, no paying an invoice twice, and no negative cash.
- A vendor with an open unpaid invoice won't ship, so its purchase orders are refused.
- No purchase order above 200 units, and none that would spend cash needed for bills due within 30 days.
- Low stock means 5 units or fewer. There is no sales history, so "hasn't sold" is never reported.
- Messages stay as drafts.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python mcp_server/server.py
```

The FastAPI backend (`backend/main.py`) keeps one server process open and calls these tools for the dashboard routes; `approve_and_pay` is only reached through `POST /approvals/{id}/approve`.

Claude Code connects to it through `.mcp.json` at the project root, which runs `mcp_server/start.sh` (it starts the server with the project's `.venv`).

Built with [FastMCP](https://gofastmcp.com).
