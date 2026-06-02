# Metrics Dictionary — Single Source of Truth

Every KPI in the Operations Productivity Intelligence dashboard is **defined once,
here**. Tiles in Data Studio, ad-hoc SQL, and exec decks must all use these exact
definitions and populations. This is what keeps Leadership, Ops, and Finance looking
at the *same* number.

**The most common source of metric drift is the denominator.** Each KPI below pins its
population explicitly — note that quality metrics (AHT, SLA, FCR, CSAT) are over **closed**
cases, while volume and mis-tag are over **all** cases. Pin the population and the
"why doesn't my number match the dashboard" conversations stop.

> All figures below are from the current synthetic dataset (`seed = 7`, 7,500 cases).
> Source of truth for the *calculation* is the dbt mart noted in each row.

---

## KPI definitions

| # | KPI | Plain-English definition | Calculation | Population (grain) | Current | Target | Owner |
|---|-----|--------------------------|-------------|--------------------|---------|--------|-------|
| 1 | **Case Volume** | Number of support cases. | `COUNT(case_number)` | All cases (case) | 7,500 | trend | Ops Lead |
| 2 | **Avg Handle Time (AHT)** | Mean active agent **touch time** per case, in minutes (not calendar time). | `AVG(handle_time_minutes)` | Closed cases | **26.4 min** | ≤ 24 | Ops Lead |
| 3 | **First Response Time (FRT)** | Mean business-hours minutes from case creation to first agent touch. | `AVG(first_response_minutes)` | Cases with a first response | 373 min | ≤ 240 (4 bus-hrs) | Ops Lead |
| 4 | **Resolution Time** | Mean business hours from creation to close. | `AVG(resolution_time_hours)` | Closed cases | 15.5 hrs | within SLA | Ops Lead |
| 5 | **SLA Met %** | Share of closed cases resolved within their case-type SLA target. | `AVG(IF(sla_met, 1, 0))` where `sla_met = resolution_time_hours ≤ sla_target_hours` | Closed cases | **79.4%** | 85% | Ops Lead |
| 6 | **First-Contact Resolution (FCR) %** | Share resolved on first contact — no reopen, no escalation. | `AVG(IF(is_first_contact_resolution, 1, 0))` | Closed cases | **60.5%** | 65% | Ops Lead |
| 7 | **Reopen %** | Share of closed cases reopened at least once. | `AVG(IF(reopened_count > 0, 1, 0))` | Closed cases | 9.9% | < 10% | Ops Lead |
| 8 | **CSAT** | Mean post-resolution satisfaction, 1–5. | `AVG(csat_score)` | Closed **and surveyed** (≈59% response) | **4.38** | ≥ 4.5 | CX Lead |
| 9 | **Escalation %** | Share of cases escalated beyond first owner. | `AVG(IF(escalated, 1, 0))` | Closed cases | 6.1% | < 8% | Ops Lead |
| 10 | **Intake Mis-tag %** | Share of cases whose **recorded** category differs from the **true** category. | `AVG(IF(category_tagged <> category, 1, 0))` (= `AVG(IF(is_mistagged,1,0))`) | All cases | **12.3%** | < 5% | Intake / Ops |
| 11 | **KB Handle-Time Reduction** | % drop in AHT for KB-addressable cases, pre vs post the 2025-09-01 KB launch. | `1 − AVG(handle_min ∣ post & kb_addressable) / AVG(handle_min ∣ pre & kb_addressable)` | Closed, `kb_addressable = true` | **−24%** (26.0→19.7) | sustain | Enablement |
| 12 | **KB-Deflectable Hours / Month** | Modeled agent-hours/month recoverable by building the prioritized KB backlog. | volume × deflection rate × AHT ÷ 60 (see `analyze_patterns.py`) | Top KB backlog | ≈ 22 hrs/mo | grow | Enablement |

**Source marts:** rows 1–9, 11 → `fct_cases`; monthly trend of 2/5/6 → `kb_impact_monthly`;
row 10 → `mistag_routing` / `fct_cases`; row 12 → `pattern_pareto` → `out/kb_backlog.csv`.

---

## Population rules (read once, avoid 90% of disputes)

- **"Closed cases"** = `status = 'Closed'` (7,469 of 7,500). Quality/timing metrics exclude
  the ~0.4% still open, because an open case has no resolution time or CSAT.
- **CSAT** additionally requires a survey response (`csat_score IS NOT NULL`, ≈59% of closed).
  Report the response rate alongside the score — it is subject to response bias.
- **Volume** and **Mis-tag %** are over **all** cases (open + closed), because they don't
  depend on resolution.
- **Rates are 0–1 in the warehouse**; format as **percent** in the BI tool (do not display
  the raw 0.79 as an integer — that's the "shows 1 or 0" bug).
- **AHT is touch time** (`handle_time_minutes`), distinct from **Resolution Time** (calendar/
  business hours, creation→close). Don't conflate them.

---

## Definitions page (dashboard spec)

To make this dictionary the *operational* source of truth — not just a doc — surface it
inside the report so end-users see definitions in context.

1. **Definitions live in the warehouse.** Load `dbt/seeds/metric_definitions.csv` via
   `dbt seed`; it lands as table `ops_intel.metric_definitions`. The doc and the dashboard
   then read from the same place.
2. **Add a "Definitions" page** to the Data Studio report:
   - **Table tile**, source `metric_definitions`: columns *KPI · Definition · Calculation ·
     Population · Target*. Sort by KPI. This is the page you send anyone who asks "how is X
     calculated?"
   - A short header: *"One definition per KPI. Every tile in this report uses these."*
3. **In-context tooltips.** On each scorecard/chart elsewhere, set the metric field's
   **Description** (Data Studio → Resource → field → Description) to its one-line definition.
   Data Studio shows it on hover — definition travels with the number.
4. **Nav:** add a small **ⓘ Definitions** link on every page pointing to the Definitions page.

This closes the loop: `METRICS.md` (human-readable) → `metric_definitions` seed (warehouse)
→ Definitions page + tooltips (in-product) — one definition, surfaced everywhere.
