# Team Tasks — Distributed Returns Optimization Agent

## Ownership

### Member 1 — Data and Classification
**Owns:**
- `generate_data.py`
- `data/retailer_*/*.csv`
- `knowledge/cause_taxonomy.json`
- `src/classifier.py`
- `tests/test_classifier.py`

**Deliverables:**
- deterministic data (seed 42) with the 7 planted scenarios
- the keyword taxonomy
- confidence rules (0.90 / 0.80 / 0.50)

**Presents:**
- the business problem
- the synthetic data
- the shared return taxonomy

### Member 2 — Privacy and Distributed Analytics
**Owns:**
- `src/retailer_nodes/retailer_node.py`
- `src/privacy/local_privacy.py`
- `src/privacy/coordinator.py`
- `src/audit.py`
- `tests/test_privacy.py`

**Deliverables:**
- rules A–D
- temporary tokens
- the banded public model
- the audit log
- the guarantee that the coordinator never reads CSVs

**Presents:**
- the distributed architecture
- the privacy thresholds
- approved versus suppressed patterns

### Member 3 — Agents and Forecasting
**Owns:**
- `src/agents/*`
- `knowledge/interventions.json`
- `src/forecasting.py`
- intervention planning in `service.build_intervention_plan`
- `tests/test_forecasting.py`

**Deliverables:**
- four agents
- an intervention knowledge base covering every cause
- low/expected/high forecasts with validation

**Presents:**
- the four-agent workflow
- recommendations
- forecast assumptions

### Member 4 — MCP and Integrations
**Owns:**
- `mcp_server.py`
- `src/integrations/mock_oms.py`
- `src/integrations/mock_customer_service.py`
- `tests/test_integrations.py`

**Deliverables:**
- 8 MCP tools with docstrings
- sanitized order context
- support actions that are DRAFT-only

**Presents:**
- the role of MCP
- tool access
- the mock business-system integrations

### Member 5 — Dashboard and Integration
**Owns:**
- `app.py`
- `src/service.py`
- Plotly charts
- `README.md`
- `tests/test_service.py`
- final demo and styling

**Deliverables:**
- 5-tab dashboard
- shared service facade
- docs
- end-to-end demo

**Presents:**
- the live demo
- results
- limitations and future work

## Extended features (stretch goals: build only once the core is green, before the 14:30 freeze)

| Feature | Owner |
|---|---|
| Classification Lab | Member 1 |
| Privacy policy simulator | Member 2 |
| Portfolio forecast and prioritisation matrix | Member 3 |
| Extra MCP tools, resources and prompt | Member 4 |
| Heatmap and exports | Member 5 |

## Shared contracts (agreed at 09:00)

- `LocalPatternSummary` (internal) → `CollectivePattern` (public, 6 fields), defined in `src/models.py`
- Cause codes come from `knowledge/cause_taxonomy.json`
- Service method names are fixed in `src/service.py`, and both the UI and MCP call only those methods

## One-day timeline

| Time | Activity |
|---|---|
| 09:00–09:30 | Agree on contracts (models, service methods, cause codes) and repository structure |
| 09:30–12:00 | Build components in parallel: data and classifier (M1), nodes and privacy (M2), agents and KB (M3), MCP and mocks (M4), dashboard skeleton (M5) |
| 12:00–12:30 | First integration checkpoint: service wires real components; `pytest -q` runs |
| 12:30–14:30 | Finish features and tests; finish the planted scenarios |
| 14:30 | **Feature freeze** |
| 14:30–16:30 | Integration, testing and bug fixes; check the demo scenario end to end |
| 16:30–17:30 | Prepare the presentation (PRESENTATION.md) |
| 17:30–18:15 | Two full rehearsals with timing |
