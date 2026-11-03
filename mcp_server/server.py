"""Campus Customs MCP server.

Every agent on the team (Boss, Inventory, Accounting, Facilities, Customer Service)
uses the tools here. They read from and write to the working copy of the shop
database, data/campus_customs_new.db. The original, data/campus_customs.db, is
never touched.

Rules the tools follow:
- Only return what is in the database. If a row isn't there, raise an error
  instead of guessing.
- "Today" is desk.date_today, not the computer clock.
- Agents can only *request* money moves. A request sits on the board until a
  human approves it with approve_and_pay, which the agents are never given.
- approve_and_pay refuses if cash would go negative. Cash only goes out.
- Messages to customers, vendors and the landlord are saved as drafts only.
- New purchase orders can't spend cash that upcoming bills need.
"""

import calendar
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
DB_PATH = Path(os.environ.get("CAMPUS_DB_PATH", DEFAULT_DB))

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer service", "customer_service"}
TICKET_STATUSES = {"open", "in_progress", "waiting_on_approval", "waiting_on_vendor", "resolved", "declined"}
MAX_PO_QTY = 200  # guardrail: no single purchase order above this many units
LOW_STOCK_THRESHOLD = 5  # shop policy: at or below this many units on hand counts as low
BILL_RESERVE_DAYS = 30  # cash for bills due within this many days is held back from new orders
STORE_TASK_PRIORITIES = {"low", "normal", "high"}
CASH_ACCOUNT = "checking"

mcp = FastMCP(
    name="campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. Only use what these tools "
        "return; never make up stock, prices, dates, or amounts. Money only moves "
        "after a human approves a request."
    ),
)

BOARD_TABLES = """
CREATE TABLE IF NOT EXISTS approval_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,              -- invoice | rent | purchase_order
    ref_id INTEGER,                  -- invoices.id or leases.id (null for purchase orders)
    ticket_id INTEGER,
    vendor_id INTEGER,
    sku TEXT, size TEXT, qty INTEGER,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,            -- pending | approved_paid | rejected | refused_insufficient_cash
    created_at TEXT NOT NULL,
    decided_by TEXT, decided_at TEXT, decision_note TEXT,
    payment_id INTEGER,
    expected_arrival TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS store_tasks (
    id INTEGER PRIMARY KEY,
    area TEXT NOT NULL,
    task TEXT NOT NULL,
    priority TEXT NOT NULL,         -- low | normal | high
    created_by TEXT NOT NULL,
    ticket_id INTEGER,
    status TEXT NOT NULL DEFAULT 'open',  -- open | done
    created_at TEXT NOT NULL,
    done_by TEXT, done_at TEXT
);
CREATE TABLE IF NOT EXISTS ticket_updates (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    old_status TEXT, new_status TEXT NOT NULL,
    note TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise ToolError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # The board tables are not in the original database, so they are created on
    # first use. Resetting the working copy from the original clears them too.
    conn.executescript(BOARD_TABLES)
    return conn


def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def shop_today(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    if row is None:
        raise ToolError("desk table has no date_today")
    return row["date_today"]


def days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def add_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def require_ticket(conn: sqlite3.Connection, ticket_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise ToolError(f"No ticket with id {ticket_id}")
    return row


def require_name(name: str, field: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ToolError(f"{field} is required")
    return name


def cash_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (CASH_ACCOUNT,)).fetchone()
    if row is None:
        raise ToolError(f"No cash account named {CASH_ACCOUNT!r}")
    return row


def open_invoices_for_vendor(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, amount, due_date, description FROM invoices "
        "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def pending_total(conn: sqlite3.Connection) -> float:
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM approval_requests WHERE status = 'pending'"
    ).fetchone()[0]


def upcoming_bills(conn: sqlite3.Connection, within_days: int) -> list[dict]:
    """Open vendor invoices and lease rent due within `within_days` of today (overdue ones included)."""
    today = shop_today(conn)
    bills = []
    for inv in conn.execute(
        "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
        "WHERE i.status = 'open' ORDER BY i.due_date"
    ).fetchall():
        days = days_between(today, inv["due_date"])
        if days <= within_days:
            bills.append({"kind": "invoice", "ref_id": inv["id"], "payee": inv["vendor_name"],
                          "amount": inv["amount"], "due_date": inv["due_date"], "days_until_due": days,
                          "is_overdue": days < 0, "description": inv["description"]})
    for lease in conn.execute("SELECT * FROM leases ORDER BY next_due").fetchall():
        days = days_between(today, lease["next_due"])
        if days <= within_days:
            bills.append({"kind": "rent", "ref_id": lease["id"], "payee": lease["landlord"],
                          "amount": lease["monthly_rent"], "due_date": lease["next_due"], "days_until_due": days,
                          "is_overdue": days < 0, "description": f"Rent for {lease['space_name']}"})
    for bill in bills:
        req = conn.execute(
            "SELECT id, status FROM approval_requests WHERE kind = ? AND ref_id = ? "
            "AND status IN ('pending', 'approved_paid') ORDER BY id DESC",
            (bill["kind"], bill["ref_id"]),
        ).fetchone()
        if bill["kind"] == "rent" and req is not None:
            # a rent request only covers the month named in its reason
            req = conn.execute(
                "SELECT id, status FROM approval_requests WHERE kind = 'rent' AND ref_id = ? "
                "AND status IN ('pending', 'approved_paid') AND reason LIKE ? ORDER BY id DESC",
                (bill["ref_id"], f"%{bill['due_date']}%"),
            ).fetchone()
        bill["approval_request"] = dict(req) if req else None
    return sorted(bills, key=lambda b: b["days_until_due"])


def block_duplicate(conn: sqlite3.Connection, kind: str, ref_id: int | None, extra: str = "", args: tuple = ()) -> None:
    row = conn.execute(
        "SELECT id, status FROM approval_requests WHERE kind = ? AND ref_id IS ? "
        "AND status IN ('pending', 'approved_paid')" + extra,
        (kind, ref_id, *args),
    ).fetchone()
    if row is not None:
        raise ToolError(
            f"A {kind} request for this item already exists (request {row['id']}, status {row['status']}). "
            "Do not file it twice."
        )


def new_request(conn: sqlite3.Connection, **fields) -> dict:
    fields.update(status="pending", created_at=now_stamp())
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO approval_requests ({cols}) VALUES ({marks})", tuple(fields.values()))
    conn.commit()
    balance = cash_row(conn)["balance"]
    return {
        "request_id": cur.lastrowid,
        **fields,
        "cash_balance_now": balance,
        "all_pending_requests_total": pending_total(conn),
        "note": "Nothing has been paid. A human must approve this request on the dashboard.",
    }


# ---------------------------------------------------------------- the board


@mcp.tool
def get_open_tickets() -> dict:
    """List every open ticket on the board, plus the shop's date_today.

    Boss uses this to read the board and decide who works on each ticket.
    Link fields (sku/size, lease_id, invoice_id) point to other tables.
    Tables: tickets, desk.
    """
    with connect() as conn:
        today = shop_today(conn)
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status = 'open' ORDER BY id"
        ).fetchall()
    return {"date_today": today, "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket on the board (open and finished) with its status, plus date_today.

    state is "resolved" when status is resolved or declined, otherwise "open"
    (in_progress and waiting_* tickets still need work, so they count as open).
    The dashboard uses this for the ticket board.
    Tables: tickets, desk.
    """
    with connect() as conn:
        today = shop_today(conn)
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    tickets = [{**dict(r), "state": "resolved" if r["status"] in ("resolved", "declined") else "open"} for r in rows]
    return {"date_today": today, "tickets": tickets}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with everything already done on it: status history, drafts and approval requests.

    Any agent uses this before acting, so work is not repeated.
    Tables: tickets, ticket_updates, drafts, approval_requests, desk.
    """
    with connect() as conn:
        ticket = dict(require_ticket(conn, ticket_id))
        ticket["date_today"] = shop_today(conn)
        ticket["updates"] = [dict(r) for r in conn.execute(
            "SELECT * FROM ticket_updates WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        ticket["drafts"] = [dict(r) for r in conn.execute(
            "SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        ticket["approval_requests"] = [dict(r) for r in conn.execute(
            "SELECT * FROM approval_requests WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
    return ticket


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str, updated_by: str) -> dict:
    """Move a ticket to a new status and record why. Boss makes this final call.

    status must be one of: open, in_progress, waiting_on_approval,
    waiting_on_vendor, resolved, declined.
    Tables: tickets, ticket_updates.
    """
    if status not in TICKET_STATUSES:
        raise ToolError(f"status must be one of {sorted(TICKET_STATUSES)}")
    note = require_name(note, "note")
    updated_by = require_name(updated_by, "updated_by")
    with connect() as conn:
        old = require_ticket(conn, ticket_id)["status"]
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.execute(
            "INSERT INTO ticket_updates (ticket_id, old_status, new_status, note, updated_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, old, status, note, updated_by, now_stamp()),
        )
        conn.commit()
    return {"ticket_id": ticket_id, "old_status": old, "new_status": status, "note": note}


# ---------------------------------------------------------------- inventory and vendors


@mcp.tool
def check_stock(sku: str, size: str) -> dict:
    """Check how many units of one SKU and size are on hand, with its cost and list price.

    Inventory uses this to spot shortfalls. Use size "OS" for one-size items.
    Tables: inventory, pricing.
    """
    with connect() as conn:
        item = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if item is None:
            raise ToolError(f"No inventory row for sku={sku!r}, size={size!r}")
        price = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    result = dict(item)
    if price is not None:
        result["unit_cost"] = price["unit_cost"]
        result["list_price"] = price["list_price"]
    return result


@mcp.tool
def list_inventory(sku: str | None = None) -> dict:
    """List stock for every size of one SKU (or every SKU if none is given).

    Inventory uses this to see other sizes and anything at zero.
    Tables: inventory.
    """
    with connect() as conn:
        if sku:
            rows = conn.execute("SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)).fetchall()
            if not rows:
                raise ToolError(f"No inventory rows for sku={sku!r}")
        else:
            rows = conn.execute("SELECT * FROM inventory ORDER BY rowid").fetchall()
    return {"items": [dict(r) for r in rows]}


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty, lead time, open unpaid invoices, and whether it will ship.

    A vendor will not ship new product while it has an open unpaid invoice.
    Inventory uses this to pick who can restock; Accounting uses it to see who is owed.
    Tables: vendors, invoices.
    """
    with connect() as conn:
        vendors = []
        for v in conn.execute("SELECT * FROM vendors ORDER BY id").fetchall():
            owed = open_invoices_for_vendor(conn, v["id"])
            vendors.append({
                **dict(v),
                "open_invoices": owed,
                "open_invoice_total": round(sum(i["amount"] for i in owed), 2),
                "will_ship": not owed,
            })
    return {"vendors": vendors}


# ---------------------------------------------------------------- accounting


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Look up one vendor invoice, with the vendor's name and lead time and whether it is overdue.

    Accounting uses this before preparing a payment. A vendor will not ship new
    product while it has an open unpaid invoice.
    Tables: invoices, vendors, desk.
    """
    with connect() as conn:
        today = shop_today(conn)
        row = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, v.specialty, "
            "v.lead_days, i.amount, i.due_date, i.status, i.description "
            "FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
    if row is None:
        raise ToolError(f"No invoice with id {invoice_id}")
    result = dict(row)
    days_past_due = days_between(row["due_date"], today)
    result["date_today"] = today
    result["days_overdue"] = max(days_past_due, 0)
    result["is_overdue"] = row["status"] == "open" and days_past_due > 0
    return result


@mcp.tool
def get_cash_balance() -> dict:
    """Show cash on hand, payments already made, and what pending requests would leave.

    Accounting checks this before asking for any payment. Cash only goes out in
    this shop, and the balance may never go negative.
    Tables: cash_accounts, payments, approval_requests.
    """
    with connect() as conn:
        cash = dict(cash_row(conn))
        paid = [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id")]
        pending = pending_total(conn)
    return {
        "account": cash["name"],
        "balance": cash["balance"],
        "as_of": cash["date"],
        "payments_made": paid,
        "pending_requests_total": pending,
        "balance_if_all_pending_paid": round(cash["balance"] - pending, 2),
    }


@mcp.tool
def check_discount(sku: str, qty: int, unit_price: float) -> dict:
    """Check the margin on selling qty units of a SKU at a proposed unit price.

    Accounting and Boss use this before agreeing to any discount. A price at or
    below unit_cost loses money.
    Tables: pricing.
    """
    if qty <= 0 or unit_price <= 0:
        raise ToolError("qty and unit_price must be greater than zero")
    with connect() as conn:
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if price is None:
        raise ToolError(f"No pricing row for sku={sku!r}")
    cost, listed = price["unit_cost"], price["list_price"]
    margin = unit_price - cost
    return {
        "sku": sku,
        "qty": qty,
        "list_price": listed,
        "unit_cost": cost,
        "proposed_unit_price": unit_price,
        "discount_pct_off_list": round((listed - unit_price) / listed * 100, 1),
        "margin_per_unit": round(margin, 2),
        "margin_pct": round(margin / unit_price * 100, 1),
        "total_revenue": round(unit_price * qty, 2),
        "total_margin": round(margin * qty, 2),
        "below_or_at_cost": unit_price <= cost,
    }


# ---------------------------------------------------------------- facilities


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Look up one lease: the space, landlord, monthly rent, next due date, and days until due.

    Facilities uses this for rent notices.
    Tables: leases, desk.
    """
    with connect() as conn:
        today = shop_today(conn)
        row = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
    if row is None:
        raise ToolError(f"No lease with id {lease_id}")
    result = dict(row)
    days_until = days_between(today, row["next_due"])
    result["date_today"] = today
    result["days_until_due"] = days_until
    result["is_overdue"] = days_until < 0
    return result


# ---------------------------------------------------------------- requests (no money moves)


@mcp.tool
def request_invoice_payment(invoice_id: int, ticket_id: int, reason: str, requested_by: str) -> dict:
    """Ask a human to approve paying a vendor invoice. Pays nothing by itself.

    The amount is taken from the invoice, never typed in. Refuses if the
    invoice is not open, is already requested, or is more than the cash on hand.
    Tables: invoices, tickets, cash_accounts, approval_requests.
    """
    reason = require_name(reason, "reason")
    requested_by = require_name(requested_by, "requested_by")
    with connect() as conn:
        require_ticket(conn, ticket_id)
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if inv is None:
            raise ToolError(f"No invoice with id {invoice_id}")
        if inv["status"] != "open":
            raise ToolError(f"Invoice {invoice_id} is {inv['status']!r}, not open")
        block_duplicate(conn, "invoice", invoice_id)
        if inv["amount"] > cash_row(conn)["balance"]:
            raise ToolError(f"Invoice {invoice_id} (${inv['amount']}) is more than the cash on hand")
        return new_request(conn, kind="invoice", ref_id=invoice_id, ticket_id=ticket_id,
                           vendor_id=inv["vendor_id"], amount=inv["amount"],
                           reason=reason, requested_by=requested_by)


@mcp.tool
def request_rent_payment(lease_id: int, ticket_id: int, reason: str, requested_by: str) -> dict:
    """Ask a human to approve paying this month's rent on a lease. Pays nothing by itself.

    The amount is the lease's monthly_rent, never typed in. Refuses a duplicate
    request or one larger than the cash on hand.
    Tables: leases, tickets, cash_accounts, approval_requests.
    """
    reason = require_name(reason, "reason")
    requested_by = require_name(requested_by, "requested_by")
    with connect() as conn:
        require_ticket(conn, ticket_id)
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            raise ToolError(f"No lease with id {lease_id}")
        block_duplicate(conn, "rent", lease_id, " AND reason LIKE ?", (f"%{lease['next_due']}%",))
        if lease["monthly_rent"] > cash_row(conn)["balance"]:
            raise ToolError(f"Rent (${lease['monthly_rent']}) is more than the cash on hand")
        return new_request(conn, kind="rent", ref_id=lease_id, ticket_id=ticket_id,
                           amount=lease["monthly_rent"],
                           reason=f"Rent due {lease['next_due']}: {reason}", requested_by=requested_by)


@mcp.tool
def request_purchase_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                           reason: str, requested_by: str) -> dict:
    """Ask a human to approve a purchase order to restock one SKU and size. Pays nothing by itself.

    The amount is qty x pricing.unit_cost. Refuses if the vendor has an open
    unpaid invoice (it will not ship), if qty is not between 1 and 200, or if the
    SKU/size is not stocked. The answer includes the expected arrival date from
    the vendor's lead_days.
    Tables: vendors, invoices, inventory, pricing, tickets, cash_accounts, approval_requests.
    """
    reason = require_name(reason, "reason")
    requested_by = require_name(requested_by, "requested_by")
    if not 1 <= qty <= MAX_PO_QTY:
        raise ToolError(f"qty must be between 1 and {MAX_PO_QTY}")
    with connect() as conn:
        require_ticket(conn, ticket_id)
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            raise ToolError(f"No vendor with id {vendor_id}")
        owed = open_invoices_for_vendor(conn, vendor_id)
        if owed:
            ids = ", ".join(str(i["id"]) for i in owed)
            raise ToolError(
                f"{vendor['name']} will not ship while invoice(s) {ids} are unpaid. "
                "Get the invoice paid first."
            )
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            raise ToolError(f"No inventory row for sku={sku!r}, size={size!r}")
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            raise ToolError(f"No pricing row for sku={sku!r}")
        block_duplicate(conn, "purchase_order", None, " AND ticket_id = ? AND sku = ? AND size = ?",
                        (ticket_id, sku, size))
        amount = round(qty * price["unit_cost"], 2)
        balance = cash_row(conn)["balance"]
        if amount > balance:
            raise ToolError(f"This order (${amount}) is more than the cash on hand")
        # Overspend guard: bills come first. Hold back cash for every pending request and every
        # bill due within BILL_RESERVE_DAYS that has no request yet.
        unrequested = sum(b["amount"] for b in upcoming_bills(conn, BILL_RESERVE_DAYS) if b["approval_request"] is None)
        free_cash = round(balance - pending_total(conn) - unrequested, 2)
        if amount > free_cash:
            raise ToolError(
                f"This order (${amount}) would leave upcoming bills unfunded. Cash ${balance}, "
                f"pending requests ${pending_total(conn)}, unrequested bills due within {BILL_RESERVE_DAYS} days "
                f"${unrequested}, so only ${max(free_cash, 0)} is free to spend. Pay the bills first."
            )
        today = shop_today(conn)
        arrival = (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat()
        return new_request(conn, kind="purchase_order", ref_id=None, ticket_id=ticket_id,
                           vendor_id=vendor_id, sku=sku, size=size, qty=qty, amount=amount,
                           reason=reason, requested_by=requested_by, expected_arrival=arrival)


@mcp.tool
def list_approval_requests(status: str = "pending") -> dict:
    """List approval requests by status (pending, approved_paid, rejected, refused_insufficient_cash, or all).

    Agents use this to avoid duplicate requests; the dashboard shows the pending ones to a human.
    Tables: approval_requests.
    """
    with connect() as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM approval_requests ORDER BY id").fetchall()
        else:
            rows = conn.execute("SELECT * FROM approval_requests WHERE status = ? ORDER BY id", (status,)).fetchall()
    return {"requests": [dict(r) for r in rows]}


# ---------------------------------------------------------------- drafts (never sent)


@mcp.tool
def save_draft(ticket_id: int, recipient: str, subject: str, body: str, author: str) -> dict:
    """Save a message draft on the board for a customer, vendor or landlord. It is never sent.

    Customer Service and Facilities use this. A human reads and sends it outside this system.
    Tables: tickets, drafts.
    """
    recipient = require_name(recipient, "recipient")
    subject = require_name(subject, "subject")
    body = require_name(body, "body")
    author = require_name(author, "author")
    with connect() as conn:
        require_ticket(conn, ticket_id)
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, subject, body, author, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'draft', ?)",
            (ticket_id, recipient, subject, body, author, now_stamp()),
        )
        conn.commit()
    return {"draft_id": cur.lastrowid, "ticket_id": ticket_id, "status": "draft",
            "note": "Saved on the board only. Nothing was emailed or sent."}


@mcp.tool
def list_drafts(ticket_id: int | None = None) -> dict:
    """List message drafts on the board, for one ticket or all.

    Tables: drafts.
    """
    with connect() as conn:
        if ticket_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
        else:
            rows = conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,)).fetchall()
    return {"drafts": [dict(r) for r in rows]}


# ---------------------------------------------------------------- oversight


@mcp.tool
def get_bills_due(within_days: int = 1) -> dict:
    """List every unpaid bill (vendor invoices and rent) due within `within_days` of today, overdue ones first.

    within_days=1 is the 24-hour alert Boss gets before any work starts. Each bill shows
    whether a payment request already exists. Also shows whether cash covers them all.
    Tables: invoices, vendors, leases, approval_requests, cash_accounts, desk.
    """
    if within_days < 0:
        raise ToolError("within_days must be 0 or more")
    with connect() as conn:
        today = shop_today(conn)
        bills = upcoming_bills(conn, within_days)
        balance = cash_row(conn)["balance"]
    total = round(sum(b["amount"] for b in bills), 2)
    return {
        "date_today": today,
        "within_days": within_days,
        "bills": bills,
        "total_due": total,
        "overdue_count": sum(b["is_overdue"] for b in bills),
        "without_request_count": sum(b["approval_request"] is None for b in bills),
        "cash_balance": balance,
        "cash_covers_all": total <= balance,
    }


@mcp.tool
def get_low_stock(threshold: int = LOW_STOCK_THRESHOLD) -> dict:
    """List every SKU and size with `threshold` or fewer units on hand (default 5), lowest first.

    Each item shows any open tickets asking for that SKU and size, so the team knows which
    customers are affected. The database has no sales history, so it cannot say what has
    or hasn't sold.
    Tables: inventory, tickets.
    """
    if threshold < 0:
        raise ToolError("threshold must be 0 or more")
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM inventory WHERE qty <= ? ORDER BY qty, sku, size", (threshold,)
        ).fetchall()
        items = []
        for r in rows:
            asks = conn.execute(
                "SELECT id, requester, qty, status FROM tickets WHERE sku = ? AND size = ? "
                "AND status NOT IN ('resolved', 'declined')",
                (r["sku"], r["size"]),
            ).fetchall()
            items.append({**dict(r), "out_of_stock": r["qty"] == 0, "open_tickets": [dict(a) for a in asks]})
    return {
        "threshold": threshold,
        "items": items,
        "sales_history": "not in the database: sell-through cannot be measured",
    }


@mcp.tool
def create_store_task(area: str, task: str, priority: str, created_by: str, ticket_id: int | None = None) -> dict:
    """Put a store upkeep task on the board for staff (cleaning spills, picking up hangers, emptying trash).

    Agents cannot clean; a person does the task and marks it done on the dashboard.
    priority is low, normal, or high (spills and anything a customer could slip on are high).
    Tables: store_tasks, tickets.
    """
    area = require_name(area, "area")
    task = require_name(task, "task")
    created_by = require_name(created_by, "created_by")
    if priority not in STORE_TASK_PRIORITIES:
        raise ToolError(f"priority must be one of {sorted(STORE_TASK_PRIORITIES)}")
    with connect() as conn:
        if ticket_id is not None:
            require_ticket(conn, ticket_id)
        dup = conn.execute(
            "SELECT id FROM store_tasks WHERE status = 'open' AND area = ? AND task = ?", (area, task)
        ).fetchone()
        if dup is not None:
            raise ToolError(f"The same task is already open (task {dup['id']})")
        cur = conn.execute(
            "INSERT INTO store_tasks (area, task, priority, created_by, ticket_id, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'open', ?)",
            (area, task, priority, created_by, ticket_id, now_stamp()),
        )
        conn.commit()
    return {"task_id": cur.lastrowid, "area": area, "task": task, "priority": priority, "status": "open"}


@mcp.tool
def list_store_tasks(status: str = "open") -> dict:
    """List store upkeep tasks by status (open, done, or all), high priority first.

    Tables: store_tasks.
    """
    order = "CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id"
    with connect() as conn:
        if status == "all":
            rows = conn.execute(f"SELECT * FROM store_tasks ORDER BY {order}").fetchall()
        else:
            rows = conn.execute(f"SELECT * FROM store_tasks WHERE status = ? ORDER BY {order}", (status,)).fetchall()
    return {"tasks": [dict(r) for r in rows]}


# ---------------------------------------------------------------- human only (never given to agents)


@mcp.tool(tags={"human_only"})
def approve_and_pay(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Approve a pending request and make the payment.

    Refuses if the approver is an agent, the request is not pending, the item
    was already paid, or cash would go negative. On success it writes a payments
    row, lowers cash_accounts.balance, and marks the invoice paid, moves the lease
    to next month, or sets the purchase order's arrival date.
    Tables: approval_requests, payments, cash_accounts, invoices, leases, vendors, desk.
    """
    approved_by = require_name(approved_by, "approved_by")
    if approved_by.lower() in AGENT_NAMES:
        raise ToolError("Payments must be approved by a person, not an agent")
    with connect() as conn:
        req = conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            raise ToolError(f"No approval request with id {request_id}")
        if req["status"] != "pending":
            raise ToolError(f"Request {request_id} is {req['status']!r}, not pending")
        today = shop_today(conn)
        cash = cash_row(conn)
        if req["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                raise ToolError(f"Invoice {req['ref_id']} is no longer open")
        if req["kind"] == "purchase_order" and open_invoices_for_vendor(conn, req["vendor_id"]):
            raise ToolError("The vendor still has an unpaid invoice and will not ship. Pay that first.")
        if req["amount"] > cash["balance"]:
            conn.execute(
                "UPDATE approval_requests SET status = 'refused_insufficient_cash', decided_by = ?, "
                "decided_at = ?, decision_note = ? WHERE id = ?",
                (approved_by, now_stamp(), f"Balance ${cash['balance']} is less than ${req['amount']}", request_id),
            )
            conn.commit()
            return {"request_id": request_id, "paid": False, "status": "refused_insufficient_cash",
                    "balance": cash["balance"], "amount": req["amount"],
                    "note": "Refused: paying this would make the balance negative."}

        ref_id = req["ref_id"] if req["kind"] != "purchase_order" else request_id
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], ref_id, req["amount"], CASH_ACCOUNT, today, approved_by),
        )
        new_balance = round(cash["balance"] - req["amount"], 2)
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                     (new_balance, today, CASH_ACCOUNT))
        detail = {}
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            detail["invoice_status"] = "paid"
        elif req["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            next_due = add_month(lease["next_due"])
            conn.execute("UPDATE leases SET next_due = ?, notes = ? WHERE id = ?",
                         (next_due, f"Rent for {lease['next_due']} paid {today}", req["ref_id"]))
            detail["lease_next_due"] = next_due
        else:
            lead = conn.execute("SELECT lead_days FROM vendors WHERE id = ?", (req["vendor_id"],)).fetchone()
            arrival = (date.fromisoformat(today) + timedelta(days=lead["lead_days"])).isoformat()
            conn.execute("UPDATE approval_requests SET expected_arrival = ? WHERE id = ?", (arrival, request_id))
            detail["expected_arrival"] = arrival
        conn.execute(
            "UPDATE approval_requests SET status = 'approved_paid', decided_by = ?, decided_at = ?, "
            "payment_id = ? WHERE id = ?",
            (approved_by, now_stamp(), pay.lastrowid, request_id),
        )
        conn.commit()
    return {"request_id": request_id, "paid": True, "payment_id": pay.lastrowid, "amount": req["amount"],
            "balance_before": cash["balance"], "balance_after": new_balance, **detail}


@mcp.tool(tags={"human_only"})
def reject_request(request_id: int, rejected_by: str, reason: str) -> dict:
    """HUMAN ONLY. Reject a pending request. No money moves.

    Tables: approval_requests.
    """
    rejected_by = require_name(rejected_by, "rejected_by")
    reason = require_name(reason, "reason")
    if rejected_by.lower() in AGENT_NAMES:
        raise ToolError("Requests must be rejected by a person, not an agent")
    with connect() as conn:
        req = conn.execute("SELECT status FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            raise ToolError(f"No approval request with id {request_id}")
        if req["status"] != "pending":
            raise ToolError(f"Request {request_id} is {req['status']!r}, not pending")
        conn.execute(
            "UPDATE approval_requests SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? "
            "WHERE id = ?",
            (rejected_by, now_stamp(), reason, request_id),
        )
        conn.commit()
    return {"request_id": request_id, "status": "rejected", "reason": reason}


@mcp.tool(tags={"human_only"})
def complete_store_task(task_id: int, done_by: str) -> dict:
    """HUMAN ONLY. Mark a store task done after a person has actually done it.

    Tables: store_tasks.
    """
    done_by = require_name(done_by, "done_by")
    if done_by.lower() in AGENT_NAMES:
        raise ToolError("Store tasks are marked done by the person who did them, not an agent")
    with connect() as conn:
        row = conn.execute("SELECT status FROM store_tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ToolError(f"No store task with id {task_id}")
        if row["status"] != "open":
            raise ToolError(f"Task {task_id} is already {row['status']}")
        conn.execute("UPDATE store_tasks SET status = 'done', done_by = ?, done_at = ? WHERE id = ?",
                     (done_by, now_stamp(), task_id))
        conn.commit()
    return {"task_id": task_id, "status": "done", "done_by": done_by}


if __name__ == "__main__":
    mcp.run()
