# Distributed Returns Optimization Agent — 15-minute presentation

Planned content is 14 minutes, with 1 minute of buffer. There are 11 slides and 5 speakers.

| # | Slide | Speaker | Time |
|---|---|---|---|
| 1 | Title and objective | Member 1 | 0:30 |
| 2 | The returns problem | Member 1 | 1:00 |
| 3 | A simple use case | Member 1 | 1:00 |
| 4 | System architecture | Member 2 | 1:15 |
| 5 | Privacy-preserving workflow | Member 2 | 1:15 |
| 6 | Four-agent design | Member 3 | 1:15 |
| 7 | Interventions and forecasting | Member 3 | 1:15 |
| 8 | MCP and integrations | Member 4 | 2:00 |
| 9–10 | Live demonstration | Member 5 | 3:00 |
| 11 | Results, limitations, future scope | Member 5 | 1:30 |
| | **Total** | | **14:00** |

---

## Slide 1 — Title and objective (Member 1, 30 s)

**On slide:**
- Distributed Returns Optimization Agent
- *Learn from each other's returns without exposing each other.*
- Team of 5 · one-day capstone · synthetic data

**Speaker notes:**
"Retailers lose money and customers to returns that could have been avoided. Our prototype lets three retailers learn *why* products come back, without sharing customer data, order data or return rates."

---

## Slide 2 — The returns problem (Member 1, 1 min)

**On slide:**
- The same causes come up again and again: fit, compatibility, unclear dimensions, expectation gaps, confusing setup, damage, delays.
- Each retailer only sees its own slice of the problem.
- Retailers can't share customer data, order data, exact rates, weak products or service playbooks.

**Speaker notes:**
"Every retailer learns these lessons alone. Pooling would help, but return rates and weak products are competitively sensitive, and customer data is protected. So we need collective learning that never exposes any one retailer."

---

## Slide 3 — A simple use case (Member 1, 1 min)

**On slide:**
- Local comments (these stay local): "The case does not fit my phone." · "I selected the wrong device model." · "The accessory is incompatible."
- ✅ Shared: "Compatibility is a strong return driver for Electronics across a broad group of retailers."
- ❌ Never shared: "Retailer A has a 25% electronics return rate."

**Speaker notes:**
"Here's our running example. Each retailer's customers complain about compatibility in their own words. The shared platform learns that compatibility is a strong, broad pattern in Electronics, but nobody learns any retailer's numbers. We built a shared taxonomy of nine causes and a transparent keyword classifier so every retailer labels returns the same way."

*Transition:* "Member 2 will show how the data flows without leaking."

---

## Slide 4 — System architecture (Member 2, 1 min 15 s)

**On slide:** the Mermaid diagram from the README. Each retailer node has its CSVs, a local classifier and a local aggregate. The nodes feed the privacy coordinator, which feeds the protected patterns, then the agents, then MCP and the dashboard.

**Speaker notes:**
"Each retailer runs a node that loads only its own files and classifies returns locally. The coordinator *never* opens a CSV. It can only call each node's `get_protected_summary()`. Raw comments never leave the node. A single service layer sits between the agents and both front ends, so the dashboard and MCP share the same logic. In this prototype the nodes are separate objects in one process. In production each would run inside its own retailer's environment."

---

## Slide 5 — Privacy-preserving workflow (Member 2, 1 min 15 s)

**On slide:**
- A: ≥3 local records · B: ≥2 retailers · C: ≥5 combined · D: banded output
- ✅ Electronics · COMPATIBILITY → High · Broad · confidence 0.90 · Approved
- ⛔ Beauty · OTHER (allergy) → Suppressed: insufficient retailer diversity

**Speaker notes:**
"Four rules apply. A retailer contributes a pattern only with at least three records. A pattern is released only if two or more retailers contribute and the combined count reaches five. Even then, we release bands, not numbers: Emerging, Medium or High. Compatibility passes everything. The beauty allergy issue appears only at one retailer, so it's suppressed. Releasing it would reveal that retailer's weakness. Every decision is written to an audit log that contains no counts and no identities. To be clear, this is threshold-based disclosure control, not production differential privacy."

*Transition:* "Member 3 will show what we do with the approved patterns."

---

## Slide 6 — Four-agent design (Member 3, 1 min 15 s)

**On slide:**
- **Pattern Analysis:** approved patterns, ranked by bands, with an explanation.
- **Pre-Purchase:** fixes on the product page and at checkout.
- **Post-Purchase:** support actions, always drafts that need human approval.
- **Returns Intelligence:** the JSON knowledge base: causes, interventions, forecasts, experiments, risks.

**Speaker notes:**
"These are four deterministic agents, with no LLM required. Pattern Analysis reads only approved patterns. The Pre- and Post-Purchase agents map a cause to actions. The Intelligence agent owns the knowledge base. A key safety rule: every customer-facing action stays a draft until a human approves it, and nothing may obstruct a legitimate return."

---

## Slide 7 — Interventions and forecasting (Member 3, 1 min 15 s)

**On slide:**
- COMPATIBILITY pre-purchase: compatibility checker · device-model confirmation · supported-model list.
- COMPATIBILITY post-purchase: compatible replacement · one-click exchange · tech-support routing.
- Forecast for 100 affected returns: **Low 12 · Expected 20 · High 25** (prototype assumptions).

**Speaker notes:**
"For compatibility, the planner suggests a checker before add-to-cart, plus a compatible replacement afterwards. Our forecast simply multiplies the volume *you* enter by assumption percentages from the knowledge base, so 100 affected returns gives 12, 20 and 25 prevented. These numbers are demonstration assumptions, not proven results. Every plan therefore recommends a two-week A/B test, with guardrails on conversion, checkout abandonment and satisfaction."

*Transition:* "Member 4 will explain how other tools and assistants get access."

---

## Slide 8 — MCP and integrations (Member 4, 2 min)

**On slide:**
- 8 FastMCP tools: patterns · details · pre · post · forecast · order context · support draft · audit.
- Mock OMS returns only category, delivery status, exchange availability and return started.
- Mock customer service creates DRAFTs; human approval is required and no customer is contacted.
- **MCP standardizes access to tools; privacy is enforced by the application's thresholding and output controls.**

**Speaker notes:**
"MCP gives any compatible assistant or tool a standard way to call our capabilities. But MCP is not the privacy mechanism. Every MCP tool calls the same service layer as the dashboard, so it returns the same banded, approved outputs. Nothing in the MCP server can reach a CSV. The order-system mock exposes only four harmless fields. The customer-service mock only ever creates drafts and states that no customer was contacted."

*Transition:* "Member 5 will show it running."

---

## Slides 9–10 — Live demonstration (Member 5, 3 min)

**Demo flow** (backup: screenshots of each step):

| Step | Action | Time |
|---|---|---|
| 1 | **Overview:** three connected retailer nodes; strongest driver is Electronics · COMPATIBILITY | 0:20 |
| 2 | **Pattern Explorer:** protected table and banded chart | 0:20 |
| 3 | Filter to **Electronics** | 0:15 |
| 4 | **Planner:** select **COMPATIBILITY** | 0:15 |
| 5 | Show pre-purchase interventions | 0:20 |
| 6 | Show post-purchase interventions; generate a plan | 0:25 |
| 7 | **Forecast:** 100 affected returns gives 12 / 20 / 25 with the warning | 0:25 |
| 8 | Create the draft "Recommend compatible replacement": status DRAFT, approval required | 0:20 |
| 9 | **Privacy & MCP Audit:** audit events, blocked Beauty pattern, MCP tools. *If time:* set minimum retailers to 3 in the simulator, and 14 patterns drop to 9 | 0:20 |

**Speaker notes:**
"Notice that no screen shows a count or a retailer's rate. Even the chart uses signal bands. Forecast numbers appear only because I typed in the scenario volume."

---

## Slide 11 — Results, limitations, future scope (Member 5, 1 min 30 s)

**On slide:**

Results:
- 14 approved patterns and 12 suppressed evaluations.
- All 7 planted scenarios behave as designed.
- 71 automated tests pass.
- Extras: portfolio forecasting, policy simulator, Classification Lab, exports, 15 MCP tools.
- Fully offline.

Limitations:
- Synthetic data.
- Rule-based classification.
- Threshold privacy rather than production differential privacy.
- Assumption-based forecasts.
- Mock integrations.
- Simulated nodes in one process.

Future work:
- Federated learning.
- Differential privacy.
- Secure aggregation.
- Real OMS and CRM connectors.
- Authentication and authorisation.
- Feeding experiment results back into the forecasts.
- Local LLM classification after redaction.

**Speaker notes:**
"We've shown that retailers can learn shared return drivers and act on them without exposing each other. We're honest about the limits. It's a prototype on synthetic data, with threshold-based privacy and assumed forecasts. The next steps are real cryptographic privacy, real connectors and closing the loop with experiment results."

**Closing statement:** "Fewer avoidable returns and happier customers, without any retailer giving away its secrets. Thank you. We're happy to take questions."
