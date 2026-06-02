# Decision Brief — Client Services Operations

**Audience:** VP Operations / Leadership · **Prepared by:** Analytics · **Basis:** 7,500
cases (18 months), Client Services desk supporting advisors on life & annuity products.
*Synthetic demonstration data — figures illustrate the analysis, not a real company.*

---

## Bottom line (4 decisions)

| # | Decision | Why now | Expected impact | Owner |
|---|----------|---------|-----------------|-------|
| 1 | **Build the NIGO knowledge-base article + add intake validation** | NIGO is the #1 recurring ticket and advisors can't self-resolve it (34.6% FCR). | Top KB deflection target; reduces the most common rework. | Enablement |
| 2 | **Auto-classify tickets at intake** (LLM/ML triage) | 12.3% of cases (~920) are routed to the wrong queue at intake. | A trained classifier recovers the correct queue **94.7%** of the time → faster routing, less rework, better SLA. | Ops + Analytics |
| 3 | **Give Claims & Maturity dedicated capacity + a realistic SLA** | It's the service outlier: **52% SLA** (vs 79% overall), **40.5 min** handle — the slowest, most-missed category. | Stops the category dragging the whole desk's SLA; sets honest expectations. | Ops Lead |
| 4 | **Fund the prioritized KB backlog** | The KB program already works (see below); coverage is the constraint. | ≈ **22 agent-hours/month** deflectable (≈ $10–11k/yr at a $40/hr loaded rate). | Enablement |

---

## What the data says

**The KB program is working — this is the proof, not a projection.** On knowledge-base-
addressable tickets, average handle time fell **24% (26.0 → 19.7 min)** and first-contact
resolution rose **+6.8 pts (63% → 70%)** in the 6 months after the 2025-09-01 launch — while
a **control group** of non-addressable tickets stayed flat (~41 min, ~36% FCR). The gain is
attributable to the KB, not a general trend. **Decision 4** simply extends what's proven.

**Where the work concentrates (and where it's fixable).** The top recurring tickets are
NIGO (489), application-status checks (464), application-form help (414), and product/rider
questions (377). NIGO stands out: high volume **and** the lowest self-resolution rate
(34.6% FCR) — i.e., advisors keep coming back because they can't fix it themselves. That's
the textbook profile for a self-serve article + an upstream validation step (**Decision 1**).

**Routing quality is the hidden tax.** 12.3% of tickets are mis-categorized at intake
(~920 cases) — adjacent-category confusion, e.g. NIGO logged as "Documents." Mis-routed
tickets bounce between queues before reaching the right specialist, inflating response and
resolution time. A triage classifier trained on history recovers the true queue **94.7%** of
the time (vs 84.2% for a zero-shot LLM with no training) — strong enough to assist intake
today (**Decision 2**). *Note: route triage to the cheap trained model; reserve the LLM for
drafting KB content and first-response replies, where it adds the most value per dollar.*

**Not everything is a KB problem.** Claims & Maturity has the worst SLA (52%) and longest
handle time (40.5 min), but it's **low-volume, high-complexity** work — death claims,
annuitization, surrenders. Self-serve content won't move it; **capacity and a category-
specific SLA** will (**Decision 3**). Calling this out *prevents* the wrong fix.

---

## Targets vs. current (for the QBR)

| KPI | Current | Target | Gap |
|-----|---------|--------|-----|
| SLA met % | 79% | 85% | −6 pts |
| First-contact resolution | 60% | 65% | −5 pts |
| Avg handle time | 26.4 min | ≤ 24 min | closing (KB) |
| Reopen % | 9.9% | < 10% | at target |
| Intake mis-tag % | 12.3% | < 5% | −7 pts (Decision 2) |

*Definitions for every metric above: [`METRICS.md`](METRICS.md) — one source of truth.*
