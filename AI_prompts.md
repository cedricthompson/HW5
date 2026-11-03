# AI Prompts Log — HW 5: Campus Customs Multi-Agent Operations

Every prompt I typed into my vibe coder (Claude Code) for this assignment, word for word.

Each problem section has:
- **Problem number and title**
- **Prompt:** at least one prompt, in my own words
- **Follow-up prompt:** only if I needed one

---

## Setup (before Problem 1)

**Prompts:**

1. NOw I'm ready to start homework 5
2. *(attached a screenshot of the assignment's Scenario, Data, and Rules of this shop sections)*
3. Can you save this I"ll be back.
4. This is homework 5: Campus Customs Multi-Agent Operations
   *(attached the same screenshot again)*
5. @"/Users/cedricthompson/Downloads/data-2/"
6. is the api saved
7. I meant to use same api
8. How do i install node.js
9. I'm done.

---

## Problem 1 — The Vibe Coder Prompts

**Prompt:**

> Yo, Claude. For problem one, the title of this is The Vibe Coder Prompts. And so I want you to create the AI underscore prompts.md. So I need a markdown file to stay updated as I work through this, because this file is going to be the log of what I type into the Vibe Coder. Okay, so also put one section for each problem. And for each of the sections, I want you to include the problem number and title, like we've done before, and at least one prompt that I'm going to type. In my own words, as much as possible, okay? And then the last thing will be one follow-up prompt if needed. And one sentence on what was lacking after the first. So I want you to for that third part, if I have a follow-up prompt, highlight what was lacking from the very first one.

**Follow-up prompt:** *(none yet)*

---

## Problem 2 — Study the Campus Customs Database

**Prompt:**

> Okay, this is problem two. I want you to study the campus custom database. So that's the title of this. And what I need you to do, I need you to open datacampus_customs.bd. And I want you to look through every table and its fields. And I want you to copy the original file to another thing called data/campus_customs_new.db. Later problems will update that working copy, okay? So for that particular one, they're gonna be later problems. So I want you to study the three open tickets so you can see how they link to other tables. And then I want you to start the output /harness markdown file. For each table, list the fields in one short line on why that table matters for the agents.

**Question while checking the output:**

> I see the three tickets. I just want to make sure the amounts are right... for ticket 101 is $840 for a full stock or one t-shirt.... Also

**Follow-up prompt:** *(none yet)*

---

## Problem 3 — Build the MCP Server

**Prompt** (sent in two parts: my message cut off at "only use information in", and I finished the sentence when asked):

> We are good for this. Question 3. build the mcp server... write an mcp server in mcp_server/ using FASTMCP.... make it talk to data/campus_customs_new.db. dont worry about connecting it or running right now. Also, every agent in this homework, uses the tools in this MCP server. So we will add more tools to it later, but for right now, just write 3 tools you know you will need for the tickets in the database. Keep the names clear, never invent the data, and only use information in

> Yes, the database

**Follow-up prompt:**

> I'm still on problem 3. Because I want you to go to the output/harness markdown file and list each of the 3 MCP tools. And for every tool, include which table it reads, which ticket it helps unlock, and 1 sentence on why the tool is the right one for that ticket. Please don't be vague in your responses, because vague lines like, reads inventory, don't get a high score. So this is why I want you to tie the tool to the ticket and give me a descriptive sentence as to why that is the right tool. Also, I want you to add a short MCP _server/readme markdown file. That explains what the MCP server is for and which database file it uses and the 3 tools it has.

---

## Problem 4 — Add MCP Server to the Vibe Coder and Test Each Tool

**Prompt:**

> All right, so on problem 4, the title is Add MCP Server to the Live Coder and Test Each Tool.
>
> in claude code, add the mcp server to this project so claude can call the tool. Save this connection json text in .mcp.json at the project root or howerver cluaude saves local mcp server lists. one the claude is connected test each of the three mcp tools. save the evicence in output/mcp_smoke.json. for each tool icnlude the prompt asked of claude, the tool's name, and tool's output (much match values in data/campus_customs_new.db)

**Follow-up prompt:** *(none yet)*

---

## Problem 5 — Build the Agent Team and Grow the MCP Tools

**Prompt:**

> Okay, for problem five, I want to build the agent team and grow the MCP tools. Okay, so I want you to build the agentic team for campus customs using pedantic AI. I need boss, inventory, accountant, facilities, and customer service. I want you to include prompts, models, and agent loops so they can delegate work to each other. With full connectivity. Put the agent prompts in backend /prompt/. One file per agent. Put data types in backend /models.py. And the agent files under backend /. Use the port key and only GPT-6 Luna for every agent. I want you to write the prompts that I give you with the shop rules that the agent needs, okay? More detailed prompts that cover all aspects of the agent's work and scope will score higher than the generic prompt, so I need you to be very descriptive in this. So add any tools the agents need to the MCP server so that they can work on the open tickets. The shop facts will come from the MCP server over data/campus_customs_new.db. So I'm not asking you to invent a second shop tools layer that bypasses it. Okay, so do not do that. Then we're gonna wire the agent so that they append to the output/audit trail which is a JSON file as they run. And for every agent loop step, record enough to audit later. And append to this file. Do not wipe it each run. In the output /harness markdown file, I want you to list every agent and each of the MCP tools including any that get added along with which table the tool uses. Also, we're going to add a safety section so that there are some guardrails that a real business will use with its employees and real money. Plus, we're going to limit the amount of tokens that we're using in the chat, okay? Then I want you to update the MCP _server/readme markdown file so that the tool list match what you have now.

**Follow-up prompt:**

> Can you make sure the boss agent oversees everything and touch basis with the invtory specialist when inventory is low or hasn't sold. ensure that accounting pays the bills and makes sure we don't overspend so that we are not late on our bills. Also the boss should get a report when the bills are due within 24 hours so he can ensure there are not late bills. Make sure the facilities team keeps the store clean, free of spills, not hangers on the floor, trash cans for trash. make sure our customer service team is available for our customers and that we reach out when we run low on inventory.

---

## Problem 6 — Expected Ticket Flows (output/desk_tickets.html)

**Prompt:**

> Okay, before I wire the back end, I'm writing down what I expect each team to do with the open tickets. And so I want those open tickets to be addressed. I want them to work with their other counterparts, their coworkers, work with the boss, work with the accountant to make sure that whatever the open tickets are, every aspect of those tickets are covered, whether it's a lack of inventory, whether it's a bill that needs to be paid, whatever the issue is, I want you all to work. I want the team to work together to solve it. Then I want to build output/desk_tickets.html. And I want this to be a page where I can double click with one tab per ticket. Okay. Also add an empty cache and reflection tab. We're going to come back to those later. But on each ticket tab, fill in the expected section only. Leave room for the actual section after I have run the agents. And then for each of the tickets expected session, I'm going to give you what I want you to do. Let me know who the boss should call first. Should they call the accountant first? Should they call inventory first? And tell us why. Then I don't want the boss to necessarily call everyone, because the boss should, basically, the boss can delegate. So if we open a ticket and we find that the reason the inventory has not been sent is because a bill needs to be paid, the boss can call the accountant. The accountant can pay the bill. Once they pay the bill, then they need to call the inventory and say that. If a customer has a problem, they can reach out to customer service. Customer service then reaches out to inventory to determine if it's there or not. So I don't want the boss to call everyone. I want to make sure that each agent is working in sync with each other. They should be in a flow. And so, of course, you know, I want all of the tools to be at work here. So again, I don't want you to send everything to everybody. I only want you to send it to the first person that had the issue. I've given you some examples. Once that person resolves it, I need you to determine who it goes to next. I've already told you what role each person plays.

**Follow-up prompt:** *(none yet)*

---

## Problem 7 — Backend Routes

**Prompt:**

> Okay, I'm on problem 7, backend routes, because now I have my React front-end dashboard that's good, but now it needs a back-end that it can call. So in the backend/main.py, I want you to use fast API and add routes to do the following. First route, return the 3 tickets and whether each ticket is open or resolved. Then take the ticket ID and run the agent team on that ticket. Then return recent agent events, i.e. what each agent said and which tools they use. So the board can refresh. Approve a payment or purchase after a human clicks approve. Agents only prepare the pay. This route is what actually changes the cash. Return the current check-in balance from cash_accounts and then reset the database to the original values when you want to try a fresh run, okay? So from the backend, /folder, I want you to start that server with, I'm gonna give you that, and then this will turn the backend into a local host (8000), so the front-end dashboard can call those routes.
> uvicorn main:app --reload --port 8000

**Follow-up prompt:** *(none yet)*

---

## Problem 8 — Agent Dashboard (React + Vite + TypeScript)

**Prompt:**

> Okay, so we're about to get to the agent dashboard here for problem 8. And in this problem, I do want to build the front-end dashboard in front-end slash. And I want to use the React and vite and typescript. the page should call the routes in problem solving. And at a minimum, I want you to include all the tickets, all three tickets, I want you to pick one ticket and start with the agent team on it. And show each agent and what they're saying and doing while the ticket runs. Mark the ticket resolved when the run finishes. And I want you to show a short summary of what each agent did in terms of that ticket. And then let the human approve a pay or purchase when asked. Then show the checking account balance after the pay gets approved by the human. Make my dashboard look good. I lack since we're still doing campus customs, I want to make sure that it still uses the blue, the yellow, the grays. And I also lack for my dashboard to have movement in it. Okay. I still have more, but let's get started

**Follow-up prompt:**

> I need the front end to talk to the back end, which is the localhost 8000 on the back end. Allow the VITE page origin which is usually a localhost 5173. I saw that on the file. So that it's allowed to call those. I'm going to now put something here that should go into the terminal. But this will open the React desk in the browser so that I can pick the tickets and watch the agents. I want you to write /output/design in a markdown file with what the dashboard looks like, what I told you. How resolve tickets and cash flow show up and why and then also include the creative choices that made this thing feel special.
> npm run dev
>
> *(attached a screenshot of the assignment's instructions: tell the front end to talk to the backend at http://localhost:8000, and on the backend allow the Vite page origin, usually http://localhost:5173)*

---

## Setup (between Problems 8 and 9)

Not part of any problem: the project lived in OneDrive, where installs and file reads kept timing out, so I asked to move it to the local disk (`~/Developer/hw5-multi-agent`).

**Prompt:**

> also, move this to a local drive so we dont have to wait on one drive.

---

## Problem 9 — Resolve the Tickets

**Prompt:**

> Okay, that concluded number 8. We're going to problem 9, which is resolve the tickets. So before I test the agents on a full run over all the tickets, I've already reset the database on the site, data/campus_customs_new.db. So that it should be a clean start, okay? The check-in balance is back up to 34 tickets. But I do want to run all 3 tickets on the board until each are resolved, okay? But I want you to open output/desk_tickets.html from problem 6. And on each ticket tab, I want you to fill the actual section from this run. I want to know which agents did the work, what they delegated, and which tools they used. And I want you to keep the expected session so you can compare the expected and the actual. And then on the cache tab of the same output/desk_tickets.html, I want you to itemize the money. Starting check-in balance, so I've already reset it, so you have the starting check-in balance. And then for each ticket, I want to know how cash changed when the ticket was resolved and why. So in other words, which pay/purchase a dollar amount. Then I want the ending check-in balance, and it must match the file cash_accounts in the working database. If there's any wrong cash math, I would lose points, even if the board shows that every ticket was resolved. So I don't want to lose any points. Also, I want you to save this in the output/resolved_tickets.json file. For each ticket, give the ID, the final status, the short outcome, what each agent contributed, and any human approvals. Also, in the output/resolved_board.html, I want there to be a page you can double click with a screenshot of your React board for each resolved ticket. Then append the real runs to the output/audit_trail, which is a JSON file, and then finish it in the output/harnet markdown file so that it covers the tables, the MCP tools, the 5 agents, the API routes, the dashboard, and the safety rules.

My answers during that first run (when asked whether to change Boss's resolved rule, and when I finished approving):

> Yes, update Boss
>
> i'm done

That first run (Nov 2) left ticket 103 in progress. On Nov 3 I reset the database and re-ran Problem 9: once at 09:26, then again at 10:04 so ticket 103 would use the new from-stock rule. The 10:04 run is the final result.

**Follow-up prompt** (the Nov 3 re-runs, in order):

> Hey I want to try work on resolving all three tickets. I'm going to reset the dashboard.
>
> Yes, from stock
>
> I've found a way to resolve all tickets. Now I need to update the resolved board and desk tickets so that I can update my reflections.
>
> Yes, plus make sure we re run problem 9 that will be important for my reflection.
>
> Run it again
>
> Approved, go on

---

## Problem 10 — Reflection

**Prompt** (sent in four parts, as I added to my reflection):

> Hello, I'm going to make updates to my reflection tab. So I'm kind of going to rewrite this. So you may have to pull it out because I've made some changes to the tickets. But in terms of the agents, I do think that the agents did a great job of following the flow. That was described for their roles. That the boss sent it to a person versus the person, sending it to everyone. So the boss sent it to one person, then it kind of flowed so just looking at the tickets going to inventory and different inventory, it might come to customer service, then it goes to the customer, then maybe to accounting. And so I think that in terms of the agents, they did a great job. We needed human interaction. At least one time on ticket 101, 102. And 0 times on uh, 103. But in terms of the performance, I think that on ticket 101, the agents it started with the boss and kind of went to accounting, inventory, customer service, boss, then Cedric approved it. I approved it. And I think in terms of matching up the expected versus actual, for ticket 101, the expected was that it would go to accounting, but in order for us to resolve this, it actually went to inventory first because invoice 501 was already paid. And then it took us 2 runs to resolve this ticket. Although it was expected that it would go from accounting to inventory to customer service. There was an extra request so the invoice 501 was paid via ticket 103 and so there was no duplicate there and then it differed in terms of purchase orders on this ticket the only place where it matched was the customer draft in draft 3 was a match and then also it matched around the fact that 9, September 5th it was expected to not be promised and the actual was that on September 5th it was not guaranteed but there was then an extra step in terms of the status so there was it was expected that it'll be waiting on approval for the human being to approve it but in it went to in progress first then there was approval and then it was resolved so that was ticket 101 but for ticket 102 I think that the agent performed well. It went from the boss to facilities. And so it was kind of resolved in a very quick manner. In terms of the expected, it matched in terms of what the first call was to facilities. In terms of the chain, got shorter. So I went from facilities directly into accounting. Because accounting had already filed for the rent. It matched like I said earlier on in terms of requests, it matched with the landlord's draft the place where it differed was between the waiting on approval and resolve because again a human being had to go in and press the approval so it had a low ticket run and then in terms of ticket 3 I would say that the agent was able to resolve it there was a few steps that actually happened. There were a couple runs in terms of the first call those matched but in terms of the chain the actual chain was much longer than the expected chain it had the same core chain but it took 2 extra runs and extra accounting and customer service calls so that went longer the request differed because it was expected that there will be no purchase order there was no purchase order, but the rent and invoice 501 was filed here by like bill priority. In terms of price, it was expected to be above $22. About 52 dollars. But it was actually $40. So 31% off. And it was checked with a check discount. So they got a deeper discount in the actual run. There was an extra draft. And then in terms of the status on this particular ticket, it got resolved. And so the offer was made from what we had in stock. But in terms of tokens, we did hit our limit. And I think they had to rerun it. So there were the agents definitely ran. The actual and expected was slightly different. I'm going to come back and add some

> All right, now I'm adding because they're asking about what has been what would have been simpler as one agent with tools and why. And ticket 102 was expected to go from the boss to the agent to accounting, but it actually only went from the boss to facilities. And then it went back to the boss because accounting had already filed it as a part of another ticket. And so it did not necessarily have to wait on approval. It was resolved because the rent was already paid. And so that was like the single agent. And so that was a simple ticket. So then in terms of describing the new problems, I think we can continue to keep the problems that I listed there. As well as describing the three new problems. So I don't want to necessarily make any changes to that.

> I do want to remove the convener from the actual portion that asks about the single agent. So I want to remove that. But I do think maybe there is adding a convener in terms of describing the three new problems that there wasn't a role that played as the convener. And perhaps it's not about adding a new role for the convener. Perhaps maybe the boss could play the convener role so that we could prioritize these things in one session versus trying to solve them one by one. Because that's essentially what allowed me to resolve all three tickets, is that I had enough information to know that perhaps I should resolve ticket 103 first before trying to resolve the other tickets.

> you know, in terms of rating each of the agents, I would definitely rate the boss as an agent that perhaps needs to provide more guidance. So this is where I would probably want to mark them as needing some support. I think in terms of inventory, I think the inventory agent did its job. Certainly the customer service agency did a great job. I think the accounting agent they required human interaction, and I wonder if there needs to be any support there. That could automate their process. And then I think facilities were more prepared, but I think when I look at the actual versus the expected outcomes, challenges fell short or differed often in terms of the accounting role. And so we'd want to maybe rate them as needing some improvement.

**Follow-up prompt:** *(none)*

---

## Problem 11 — Submit to GitHub

**Prompt:**

> Okay, now I'm on problem 11, which is the last one. I need to submit this to GitHub. So I've got to push my code to a public GitHub repository. So graders can clone it. So I'm going to submit the repo URL to Canvas and also put it in the output/GitHub_URL .txt. I will not push the real env to the GitHub repo. And do include both database files under data. The original and the working copy, so that graders can run the app easily. I'm going to give you how this
>
> *(attached a screenshot of the assignment's expected file layout for hw5/, and the README requirements: copy the original DB to the working copy for a clean run, start the MCP server, start the FastAPI backend, start the React board, reset the DB before a full three-ticket run)*

**Follow-up prompt:**

> *(chose the repo name in a question prompt: github.com/cedricthompson/HW5)*

---
