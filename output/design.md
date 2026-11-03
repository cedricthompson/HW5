# Campus Customs Ops Desk: dashboard design

The Ops Desk is the React page where a person picks a ticket, watches the five agents work it live, and approves the money. It's built with React + Vite + TypeScript in `frontend/`. It calls the FastAPI backend in `backend/main.py`, and the backend reaches the shop only through the `campus-customs` MCP server.

## How to open it

Two terminals, both started from the project:

```bash
cd backend && source ../.venv/bin/activate && uvicorn main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

Then open **http://localhost:5173**.

**How the two connect:**
- The page calls the backend at `http://localhost:8000`. `API_URL` in `frontend/src/api.ts` defaults to that, and `VITE_API_URL` can override it.
- The backend allows that one page origin and nothing else. `DASHBOARD_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]` in `backend/main.py` is the browser's permission to call the routes. A page on any other origin gets no CORS permission.

---

## What it looks like

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ [CC] Campus Customs Ops Desk          Shop date 2026-08-31 · ● Backend connected · Reset │  ← navy header, drifting gradient
│▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│  ← moving yellow stripe
├──────────────────┬───────────────────────────────────────────────────┬───────────────────┤
│ TICKET BOARD     │ AGENT TEAM                                  ● LIVE│ CHECKING BALANCE  │
│ ┌──────────────┐ │ [Boss]--→[Accounting]--→[Inventory]--→[Cust. Svc] │   $3,400.00       │
│ │#101 Bulldog  │ │ ┌──────────┐ ┌──────────┐ ┌──────────┐            │ pending · if paid │
│ │tee  RESOLVED │ │ │BO Boss   │ │AC Acctg  │ │IN Invent.│  …5 cards  │ payments list     │
│ │[Run again]   │ │ │ waiting… │ │ working● │ │ idle     │            ├───────────────────┤
│ ├──────────────┤ │ └──────────┘ └──────────┘ └──────────┘            │ APPROVALS  NEEDS  │
│ │#102 Rent due │ ├───────────────────────────────────────────────────┤ YOU · 1           │
│ │[Run team]    │ │ WHAT THE TEAM DID · ticket #101                   │ Vendor invoice    │
│ ├──────────────┤ │ Boss · final call … Your next step: approve #1    │ $840.00           │
│ │#103 Hoodies  │ │ [Accounting card] [Inventory card] [CS card]      │ [Approve & pay]   │
│ │[Run team]    │ ├───────────────────────────────────────────────────┤ [Reject]          │
│ └──────────────┘ │ LIVE ACTIVITY (newest on top, indented by depth)  │                   │
│                  │ Customer Service · save_draft(ticket_id: 101 …)   │                   │
│                  │   Inventory · Handed off to Customer Service      │                   │
└──────────────────┴───────────────────────────────────────────────────┴───────────────────┘
```

There are three columns on a laptop screen. On a narrow window they stack in this order: tickets, team, cash and approvals.

| Area | What's in it |
|---|---|
| **Header** | The CC crest, the title, the shop date from `desk.date_today` (not the computer clock), a connection light (green when the backend answers), and **Reset data** |
| **Ticket board** | All 3 tickets: type icon, `#id · type`, subject, requester, the customer's note, the database status pill, and a **Run team** button |
| **Agent team** | The handoff chain, then one card per agent. Each card shows a colored avatar, name, role, a phase badge (Idle / Working / Waiting / Done), the agent's latest line, and chips for each tool it has used |
| **What the team did** | After a run: the bills-due alert (if any), **Boss's final call** with **Your next step**, one card per agent that worked (summary, actions, request and draft IDs), and who was *not* called |
| **Live activity** | Every step, newest first: what an agent said, each tool call with its arguments, each tool result, handoffs, guardrails, finish, and errors. Rows are indented by handoff depth, and the token count is shown at the top |
| **Checking balance** | The balance from `cash_accounts`, the pending total, the balance if everything pending is paid, and the payments made |
| **Approvals** | The requests agents prepared, an "Approving as" name, and **Approve & pay** / **Reject** |

---

## What you asked for → where it is

| You said | How the dashboard does it |
|---|---|
| Build it in `frontend/` with React, Vite and TypeScript | `frontend/` has `package.json`, `vite.config.ts`, `tsconfig.json` and `src/*.tsx`. No UI libraries: just React and hand-written CSS. |
| Call the routes from Problem 7 | `src/api.ts` wraps all of them: `/tickets`, `/tickets/{id}/run`, `/events`, `/approvals`, `/approvals/{id}/approve`, `/reject`, `/cash`, `/reset` |
| Show all three tickets | The ticket board on the left, loaded from `GET /tickets` |
| Pick one ticket and start the agent team on it | **Run team** on a ticket card calls `POST /tickets/{id}/run` |
| Show each agent and what it's saying and doing while the ticket runs | While the run is going, the page polls `GET /events` every 0.8 seconds. The agent cards, the handoff chain, and the live activity feed all update from those events. |
| Mark the ticket resolved when the run finishes | A yellow **RESOLVED** stamp drops onto the ticket card (see below) |
| Short summary of what each agent did | The **What the team did** panel, built from each agent's final report |
| Let the human approve a pay or purchase when asked | The **Approvals** panel. Boss's "Your next step" has a button that scrolls to it. |
| Show the checking balance after the payment is approved | The balance card counts down to the new amount, lists the payment, and a toast says "Paid $840.00 · checking $3,400.00 → $2,560.00" |
| Make it look good, in Campus Customs blue, yellow and grays | Yale blue `#00356b`, a brighter blue `#286dc0`, Bulldog yellow `#f5c518`, and a gray scale from `#f2f4f7` to `#1b2431` |
| Give it movement | See "Creative choices" below |
| Front end talks to the backend at `:8000`; backend allows the Vite origin `:5173` | `API_URL` = `http://localhost:8000`, and the backend's CORS allows only `http://localhost:5173` (and `127.0.0.1:5173`) |

---

## How resolved tickets show up, and why

**What you see:**
- While the team works a ticket, its card gets a spinning blue-and-yellow border and the button reads "Running…".
- When the run finishes, a yellow **RESOLVED** stamp drops onto the card's corner (it lands big and tilted, then settles), and the button changes to **Run again**.
- The **database status pill** stays on the card next to the stamp, for example *Waiting on approval*.

**Why both:**
- **"Resolved" means the agent team finished its work on the ticket.** Every owner did their part, the chain came back to Boss, and Boss made the final call. That's what the assignment asks the board to mark.
- **The status pill tells the honest business state.** Ticket 101 is resolved *for the team*, but its tee still can't ship until a person approves the $840 invoice. If the stamp replaced the status, the board would hide the one thing a person still needs to do. Showing both answers two questions at a glance: *is the team done?* and *is the shop done?*
- **The stamp persists in the browser across reloads.** Clicking **Reset data** clears it along with the database, so a fresh run starts clean.

**Who decides the status pill:**
- Boss sets the status with `update_ticket_status`: `waiting_on_approval`, `in_progress`, `resolved`, and so on.
- `GET /tickets` also reports a `state` of `open` or `resolved`. A ticket the database itself marks `resolved` or `declined` gets the stamp too.

---

## How cash flow shows up, and why

Money is the part of the shop where a mistake costs real dollars, so the page makes three things obvious: **agents never pay, a person does, and the balance can't go negative.**

1. **Agents prepare, people pay.** When Accounting files a payment or purchase request, nothing leaves the account. The request appears in **Approvals** with:
   - its kind (vendor invoice, rent, or purchase order)
   - the amount, read from the database and never typed by an agent
   - the reason, the ticket, and which agent prepared it

   The panel glows yellow, and a **NEEDS YOU** badge pulses until it's empty.
2. **Pending money is shown before it's spent.** The balance card shows three numbers:
   - the balance now
   - **Waiting on approval** (the total of pending requests)
   - **If all approved** (what would be left)

   With today's data, approving invoice 501 and the rent would leave $160. You can see that before clicking anything.
3. **Approve & pay is the only thing that moves cash.** It calls `POST /approvals/{id}/approve` with your name. The MCP server checks everything again:
   - the request is still pending
   - the name isn't an agent's
   - the vendor or invoice is still valid
   - the payment won't push cash below zero

   Then it writes `payments`, lowers `cash_accounts.balance`, and marks the invoice paid or moves the lease to next month.
4. **The balance moves so you notice.** After approval, the big number counts down (for example $3,400.00 → $2,560.00), the card flashes a yellow ring, and the payment appears in the list with "approved by Cedric · 2026-08-31". A toast repeats the before → after.
5. **Refusals are shown, not hidden.** If a payment would overdraw the account, the server marks it `refused_insufficient_cash`, cash doesn't change, and an amber toast explains why. **Reject** asks for a reason, and no money moves.

**Why this way:** in this homework cash only goes out, so the most useful thing the page can show is *what's already promised* next to *what's left*. That lets a person see the overspend risk Accounting is guarding against before approving anything.

---

## Creative choices that make it feel special

- **Every agent has a color, and it follows them everywhere:**
  - Boss in Yale navy, Accounting in Bulldog yellow, Inventory in blue, Facilities in slate gray, Customer Service in sky blue.
  - The same color is used on the avatar, the chain node, the feed badge, and the summary card, so your eye can follow one agent through the whole run.
- **The handoff chain builds itself.** As each agent hands off, a new node pops in with a dashed arrow whose dashes keep flowing (Boss → Accounting → Inventory → Customer Service). It shows the flow from Problem 6 ("send it to the first owner, then hand off") instead of describing it.
- **Agents look alive:**
  - The agent working right now lifts up, its avatar sends out pulsing rings, and its badge shows bouncing typing dots.
  - An agent waiting on a teammate gets a slow breathing ring and says who it's waiting on.
  - A finished agent gets a green check that pops in.
- **The feed reads like a conversation.** Rows slide in from the left, newest on top, indented one step for every handoff, so you can see who asked whom. Handoffs are highlighted in yellow, guardrails in gold, and errors in red. Plumbing calls such as `final_result` and the raw `ask_teammate` result are hidden, so it reads like people working, not logs.
- **The "Resolved" stamp is a stamp.** It drops in large and tilted, then lands at an angle on the ticket's corner, like a rubber stamp on a paper ticket.
- **The header is never quite still.** The navy gradient drifts slowly, the CC crest bobs, the yellow caution stripe under the header keeps moving, and a blue-to-yellow progress bar sweeps across the top while agents work.
- **Boss gets the spotlight.** The final call sits in a navy card with a yellow label. **Your next step** comes right under it with a button that scrolls to Approvals, so the hand-off from agents to the person is one click.
- **Money gets weight:**
  - The balance is the largest number on the page, on a navy card with a slow yellow glow.
  - It counts up and down instead of jumping.
  - Approvals have a yellow edge, matching the color Accounting uses.
- **It's calm when nothing is happening.** Idle agents fade back a little, and empty panels say what will appear and why. Motion is saved for when work is happening.
- **It respects people who turn motion off.** With the system's "reduce motion" setting on, every animation stops and the page still works.
- **No extra libraries:** the icons are a dozen inline SVG paths, and every animation is plain CSS. The page loads fast, and every visual choice is in one file (`src/App.css`).

---

## Files

| File | What it holds |
|---|---|
| `frontend/src/App.tsx` | Page layout, run loop (start the run, poll events, finish), approve, reject, reset |
| `frontend/src/api.ts` | One function per backend route, with `API_URL = http://localhost:8000` |
| `frontend/src/agents.ts` | Agent names and colors, turning audit events into feed lines, live agent state, handoff chain, reports |
| `frontend/src/types.ts` | TypeScript shapes of every backend response |
| `frontend/src/components/` | `TicketList`, `AgentTeam`, `ActivityFeed`, `RunSummary`, `CashCard`, `Approvals`, `Icon` |
| `frontend/src/useCountUp.ts` | The animated balance |
| `frontend/src/App.css` | Palette, layout, and all the motion |

## How it was checked

- **Type-check and build:** `tsc --noEmit` and `vite build` both pass.
- **Live run in the browser, with no tokens:** against a test-only copy of the backend that used scripted agents and a throwaway database.
  - Ticket 101 streamed live, and the chain built Boss → Accounting → Inventory → Customer Service.
  - The ticket got the RESOLVED stamp, and the summary showed every agent.
  - One approval appeared. Approving it as "Cedric" moved checking $3,400.00 → $2,560.00 and listed the payment.
- **Connection:** with both real servers running from `~/Developer/hw5-multi-agent`, a request from `http://localhost:5173` gets `access-control-allow-origin: http://localhost:5173`, and a request from any other origin gets no permission.
