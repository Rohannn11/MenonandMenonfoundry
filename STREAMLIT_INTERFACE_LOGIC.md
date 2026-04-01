# Menon Foundry Streamlit Interface: Features and Logic

This document explains the Streamlit dashboard in `dashboard.py`, including:
- Interface structure and user workflows
- Data retrieval and refresh behavior
- KPI and analytics calculations
- Fallback and resiliency logic
- CAPA persistence and update flow

---

## 1. Interface Overview

The UI is split into two main tabs:

1. **LIVE OPERATIONS (SCADA)**
- Real-time operational visibility
- KPI monitoring
- Control tower and scheduling insights
- Traceability and CAPA workflow
- Maintenance and OTIF
- Inventory reorder intelligence
- Pipeline status grid and event logs

2. **INTELLIGENCE AGENT**
- Chat-style assistant powered by `core.brain.AgentBrain`
- Query support for prices, news, SOP knowledge, and combined intents

The page uses a dark SCADA theme with custom CSS and renders in a wide layout.

---

## 2. Data and Dependency Flow

### 2.1 PostgreSQL connection

`get_db_connection()` builds a `psycopg2` connection from environment variables:
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_PORT`

If connection fails, SCADA tab shows a DB error message.

### 2.2 Pipeline metadata

`PIPELINES` defines 11 logical pipeline blocks, each with:
- Display name
- Source table
- Primary key
- Key columns shown on cards
- Status column + critical values for alerting

### 2.3 Table fallback resolution

`TABLE_FALLBACKS` handles alternative table names. Example:
- `heat_treatment` can fallback to `heat_treatments`

`_safe_resolve_table()` checks existence via `to_regclass` and chooses the first available table.

---

## 3. Refresh and Session Behavior

### 3.1 Live toggles

Top controls in SCADA:
- `LIVE REFRESH` (`live_mode` in session state)
- `AUTO REFRESH` (`auto_refresh` in session state)

### 3.2 Auto rerun

At the bottom of the script:
- If `live_mode` and `auto_refresh` are enabled, app sleeps for `SCADA_REFRESH_SECONDS` (default 5s)
- Then calls `st.rerun()`

### 3.3 Stateful values

Session state keys maintain continuity:
- `prev_total` for velocity calculation
- `console_logs` for system event history
- Multiple CAPA form and register keys
- Chat `messages`

---

## 4. SCADA Tab: Sub-Tabs and Feature Logic

SCADA has 6 sub-tabs.

## 4.1 KPI and Overview

Displays:
- System status, total records, freshness, alerts, data quality
- Priority alerts
- KPI cards (10 core KPIs)
- Trend deltas
- Freshness and data-source captions

### KPI extraction model

`get_kpi_snapshot(conn)` computes KPI values with resilience:
- Uses `_resolve_kpi_value(value_query, presence_query, fallback)`
- If no data in period, uses baseline value from `KPI_BASELINES`
- Tracks fallback keys and latest success timestamps in `kpi_meta`

### KPI formulas

1. **Yield % (24h)**
- `AVG(casting_records.yield_pct)` over last 24h

2. **Scrap % (24h)**
- `SUM(scrap_castings) * 100 / SUM(expected_castings)` over last 24h

3. **Energy kWh/t (24h)**
- `SUM(energy_kwh) / (SUM(charge_weight_kg) / 1000)` over last 24h

4. **Avg Pour Temp (24h)**
- `AVG(pouring_temperature_c)` over last 24h

5. **Good Castings Today**
- `SUM(good_castings)` where `DATE(casting_date) = CURRENT_DATE`

6. **Melt Approval % (24h)**
- `COUNT(quality_status='APPROVED') * 100 / COUNT(*)` over last 24h

7. **Active Orders**
- `COUNT(*)` where status in `CREATED, RELEASED, IN_PROCESS`

8. **Inventory Issue Qty (24h)**
- `SUM(quantity)` from issue-like movements in last 24h
- Movement filters include `GI%`, `%ISSUE%`, `%SCRAP%`

9. **QC Rejection Rate (7d)**
- `COUNT(overall_decision='REJECT') * 100 / COUNT(*)` over last 7 days

10. **Breakdown Events (7d)**
- `COUNT(*)` from maintenance where type is `BREAKDOWN` in last 7 days

11. **Profit Margin**
- Uses estimated revenue model:
	- Metal price from API (`get_metal_price_usd`) or baseline env fallback
	- `estimated_revenue = total_qty_24h * metal_price * selling_multiplier`
	- `profit_margin = (estimated_revenue - total_cost_24h) / estimated_revenue * 100`
- Falls back to baseline if required inputs unavailable

### KPI status color logic

`_kpi_state()` classifies metric states as green/yellow/red using threshold functions per KPI.

### Trend deltas

`get_trend_snapshot()` computes current-period minus previous-period values:
- Yield delta: last 24h vs previous 24h
- Scrap delta: last 24h vs previous 24h
- Energy delta: last 24h vs previous 24h
- Reject delta: last 7d vs prior 7d window

### Data quality score

Computed in `get_analytics_snapshot()`:
- `fallback_ratio = fallback_kpis / total_kpis`
- `stale_ratio = stale_or_missing_streams / total_streams`
- `quality_score = clamp(100 - (fallback_ratio*60 + stale_ratio*40)*100, 0, 100)`

## 4.2 Control Tower and Scheduling

### Control Tower (`get_control_tower_snapshot`)

Outputs:
- WIP orders
- Delayed orders
- Completed today
- Stage mix (CREATED, RELEASED, IN_PROCESS, COMPLETED, CLOSED)
- Bottleneck stage/load (max among CREATED/RELEASED/IN_PROCESS)
- At-risk order list with age and delay calculations

Fallback:
- If no production orders, uses `CONTROL_TOWER_BASELINES`

### Scheduling (`get_scheduling_snapshot`)

Outputs:
- Due today
- Due next 3 days
- Overdue open
- Planned quantity in next 7-day horizon
- High-priority open orders (priority <= 2)
- Capacity utilization
- Dispatch-priority queue

Capacity utilization:
- `planned_qty_7d / WEEKLY_ORDER_CAPACITY * 100`
- Capped at `180%`

Fallback:
- If no orders or queue unavailable, uses `SCHEDULING_BASELINES`

### Alerts (`get_operational_alerts`)

Rules generate WARN/CRITICAL alerts for:
- Scrap thresholds
- Rejection thresholds
- Melt approval under-threshold
- Delayed orders
- Breakdown spikes
- Capacity overload/tightness
- Stale or missing freshness streams

Alerts are sorted by severity rank: `CRITICAL -> WARN -> INFO`.

## 4.3 Traceability and CAPA

### Traceability (`get_traceability_snapshot`)

Builds order trace chains by joining:
- `production_orders`
- `casting_records`
- `heat_treatment`
- Latest `machining_operations` by production order
- Latest `quality_inspections` by production order

Calculated fields:
- Chain completeness (`COMPLETE` vs `MISSING_LINKS`)
- Coverage %
- Linked orders count
- Missing links count
- Quality holds (reject/conditional/fail/rework signals)

Fallback:
- Uses `TRACEABILITY_BASELINES` if query fails or no data.

### CAPA workflow

State initialization:
- `_init_capa_state()` seeds defaults in session state
- On first load, hydrates from PostgreSQL table `capa_input`

Create CAPA:
- User creates from manual entry or linked alert
- ID format: `CAPA-XXXX` using `capa_seq`
- Row stored in session register and persisted with `_save_capa_to_db()`

Update CAPA:
- User selects existing ID
- Updates `status` and `closure_notes`
- Persists via `_update_capa_in_db()`

Form reset behavior:
- `_flush_capa_reset()` clears create-form fields on next render after successful create.

## 4.4 Maintenance and OTIF

### Maintenance (`get_maintenance_snapshot`)

KPIs:
- Open work orders
- Overdue preventive maintenance
- Upcoming PM in 7 days
- Open breakdowns
- MTTR from completed/closed breakdowns in last 30 days
- Total downtime in last 7 days (breakdown + corrective)

Also returns prioritized open work order table.

Fallback:
- Uses `MAINTENANCE_BASELINES` if no open data or query failure.

### OTIF (`get_otif_snapshot`)

For completed/closed orders in last 30 days:
- On-time %
- In-full % (`confirmed_quantity / order_quantity >= 0.95`)
- OTIF %
- Counts of completed, late, under-fill
- Recent completions table

OTIF handling:
- A preliminary expression is assigned, then overridden by a multiplicative model:
	- `OTIF = on_time_pct * in_full_pct / 100`

Fallback:
- Uses `OTIF_BASELINES` if no qualifying completed orders.

## 4.5 Inventory Reorder

`get_inventory_reorder_snapshot()` computes reorder intelligence by combining:
- Latest stock per material
- 30-day issue quantity

Suggested reorder formula:
- `max(0, safety_stock + avg_daily_issue * lead_time_days - current_stock)`

Outputs:
- Reorder items count
- Critical items count (`current_stock < 50% of safety_stock`)
- Candidate list with stock, issue velocity, and suggested reorder quantity

Fallback:
- Uses `INVENTORY_REORDER_BASELINES` if data unavailable.

## 4.6 Pipeline Grid and Logs

`fetch_live_data(conn)` gathers for each pipeline:
- Total row count
- Latest row by primary key descending

Card status logic:
- `status-crit` if status column value is in critical list
- `status-ok` if velocity > 0
- `status-idle` otherwise

Event logs:
- Adds INFO log when new records arrive (`velocity > 0`)
- Adds ALERT log for critical row status transitions
- Keeps only last 15 entries

---

## 5. Freshness Monitoring Logic

`get_freshness_snapshot(conn)` checks latest timestamp by stream using `FRESHNESS_CONFIG`.

For each stream:
- Latest timestamp lookup (`MAX(time_col)`)
- Age in hours via `_age_hours()`
- SLA-based state via `_freshness_state()`

State mapping:
- `fresh`: age <= green threshold
- `warn`: age <= warn threshold
- `stale`: beyond warn threshold
- `missing`: no timestamp

Thresholds come from `FRESHNESS_SLA_HOURS`, with maintenance allowing longer windows.

---

## 6. AI Agent Tab Logic

The second tab provides conversational interaction.

Flow:
1. `get_agent()` initializes a cached `AgentBrain` instance (`@st.cache_resource`)
2. Chat history is retained in `st.session_state.messages`
3. New prompt is appended and rendered
4. `agent.ask(prompt)` runs inside spinner
5. Assistant response is displayed and stored

Failure handling:
- If agent initialization fails, UI shows unavailable/error state.

---

## 7. Caching Strategy

Current cache usage:
- `@st.cache_data(ttl=45)` on `get_metal_price_usd`
	- Avoids repeated API calls for metal spot prices
- `@st.cache_resource` on `get_agent`
	- Keeps a persistent agent instance across reruns

---

## 8. Error Handling Philosophy

The dashboard heavily uses safe wrappers and broad exception catches to preserve availability:
- `_safe_scalar`, `_safe_count`, `_safe_latest_timestamp`
- Baseline datasets for major modules
- Graceful UI degradation instead of hard failure

Operational impact:
- Dashboard remains live even with partial DB/API outages
- Reference values are explicitly flagged as fallbacks in captions and meta indicators

---

## 9. Environment Variables Used by UI Logic

Core DB:
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_PORT`

KPI and analytics:
- `KPI_METAL` (default `copper`)
- `KPI_METAL_BASELINE` (default `4.25`)
- `KPI_SELLING_MULTIPLIER` (default `1.35`)
- `WEEKLY_ORDER_CAPACITY` (default `1200`)

Refresh and integration:
- `SCADA_REFRESH_SECONDS` (default `5`)
- `METAL_PRICE` (API key)

---

## 10. Practical Notes

1. Most cards and tables are computed from live DB state each rerun.
2. Where data is sparse or missing, baseline references ensure continuity.
3. CAPA is both session-visible and persisted to PostgreSQL for durability.
4. The UI prioritizes operator continuity over strict failure surfacing.

