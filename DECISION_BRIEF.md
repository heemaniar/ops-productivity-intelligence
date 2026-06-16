# Decision Brief — Client Services Operations

**Audience:** VP Operations / Leadership · **Prepared by:** Analytics · **Basis:** 7,500
cases (18 months), Client Services desk supporting advisors on life & annuity products.
*Synthetic demonstration data — figures illustrate the analysis, not a real company.*

**Bottom line:** The desk's biggest avoidable cost is **rework from a few high-volume,
low-self-resolution ticket types** — and the knowledge-base program already *proves* the
fix works. Four decisions below.

## Decisions at a glance

| # | Decision | Why now | Expected impact | Owner |
|---|----------|---------|-----------------|-------|
| 1 | **Build the NIGO KB article + intake validation** | NIGO is the #1 recurring ticket and advisors can't self-resolve it (34.6% FCR). | Top KB deflection target; cuts the most common rework. | Enablement |
| 2 | **Auto-classify tickets at intake** (ML triage) | 12.3% of cases (~920) are routed to the wrong queue at intake. | Trained classifier recovers the correct queue **94.7%** of the time → faster routing, better SLA. | Ops + Analytics |
| 3 | **Give Claims & Maturity dedicated capacity + a realistic SLA** | Service outlier: **52% SLA** (vs 79%), **40.5 min** handle. | Stops one category dragging the whole desk's SLA. | Ops Lead |
| 4 | **Fund the prioritized KB backlog** | The KB program already works; coverage is the constraint. | ≈ **22 agent-hours/month** deflectable (≈ $10–11k/yr). | Enablement |

## The evidence

### 1. NIGO is the #1 rework driver — and self-serve-fixable
**Evidence.** Top recurring tickets are NIGO (489), application-status checks (464),
application-form help (414), and product/rider questions (377). NIGO stands out: high
volume **and** the lowest self-resolution rate (34.6% FCR) — advisors keep coming back
because they can't fix it themselves.
**Recommendation.** Publish a NIGO self-serve article + an upstream intake-validation step
that catches the common not-in-good-order causes before submission.
**Impact.** The textbook deflection target — highest volume, lowest FCR.

### 2. Routing quality is the hidden tax
**Evidence.** 12.3% of tickets (~920) are mis-categorized at intake — adjacent-category
confusion (e.g. NIGO logged as "Documents"). Mis-routed tickets bounce between queues,
inflating response and resolution time. A classifier trained on history recovers the true
queue **94.7%** of the time, vs **84.2%** for a zero-shot LLM with no training.
**Recommendation.** Assist intake with the trained classifier. Route triage to the cheap
trained model; reserve the LLM for drafting KB content and first-response replies, where it
earns its cost.
**Impact.** Less cross-queue bouncing → faster routing and better SLA.

### 3. Claims & Maturity needs capacity, not content
**Evidence.** Claims & Maturity has the worst SLA (52%) and longest handle time (40.5 min),
but it's **low-volume, high-complexity** work — death claims, annuitization, surrenders.
Self-serve content won't move it.
**Recommendation.** Give it dedicated capacity and a category-specific SLA. Naming this
*prevents* the wrong fix (a KB article that wouldn't help).
**Impact.** Stops the outlier dragging the desk's overall SLA; sets honest expectations.

### 4. The KB program works — fund its coverage
**Evidence.** On KB-addressable tickets, handle time fell **24% (26.0 → 19.7 min)** and
first-contact resolution rose **+6.8 pts (63 → 70%)** in the 6 months after the 2025-09-01
launch — while a **control group** of non-addressable tickets stayed flat (~41 min, ~36%
FCR). The gain is attributable to the KB, not a general trend.
**Recommendation.** Fund the prioritized KB backlog; coverage is the only constraint.
**Impact.** ≈ **22 agent-hours/month** deflectable (≈ $10–11k/yr at a $40/hr loaded rate).

## Targets vs. current

| KPI | Current | Target | Gap |
|-----|---------|--------|-----|
| SLA met % | 79% | 85% | −6 pts |
| First-contact resolution | 60% | 65% | −5 pts |
| Avg handle time | 26.4 min | ≤ 24 min | closing (KB) |
| Reopen % | 9.9% | < 10% | at target |
| Intake mis-tag % | 12.3% | < 5% | −7 pts (Decision 2) |

---
*All figures reconcile to the governed marts ([`METRICS.md`](METRICS.md)) — one source of
truth; KPI integrity is dbt-tested.*
