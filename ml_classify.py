"""
ml_classify.py — Ticket triage bake-off: classic ML vs. Claude.

The same task, two ways, scored identically against ground truth:
routing an inbound client message to the correct ops queue (7 business
categories). This is the portfolio centerpiece — it shows *judgment* about
when an LLM earns its cost vs. a cheap trained classifier.

  Tier 1  TF-IDF + Logistic Regression
          Trains on 80% of cases, predicts the 20% test split.
          Needs labeled training data; ~instant; ~free.

  Tier 2  Claude zero-shot (structured-output classification)
          No training data. Reads the taxonomy + the message, returns a
          category. Costs per call; scored on a small test SAMPLE so the
          comparison is apples-to-apples and the bill stays tiny.

  --draft  Bonus: Claude drafts a first-response reply for a few tickets
           (demo of the assist layer, not a measured claim).

Outputs (out/):
    classify_report.txt      side-by-side macro-F1 / accuracy + per-class table
    draft_replies.md         (with --draft) sample Claude-drafted replies

Run:
    python ml_classify.py                 # sklearn only (no API key needed)
    export ANTHROPIC_API_KEY=...
    python ml_classify.py --claude        # add the Claude head-to-head
    python ml_classify.py --claude --sample 200 --draft
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

from ml_patterns import build_stopwords   # reuse the curated domain stop-list

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
RNG = 7

MODEL = os.getenv("OPS_LLM_MODEL", "claude-opus-4-8")  # override e.g. claude-haiku-4-5

# 7 business categories = the ops routing queues.
CATEGORIES = [
    "Product Information", "New Business", "Documents", "Policy Servicing",
    "Process", "Claims & Maturity", "Technical",
]
_CATEGORY_HINTS = {
    "Product Information": "product features, riders, rates/crediting, comparisons, suitability/illustrations",
    "New Business":        "applications, NIGO/missing info, e-signature, portal submission, status checks, underwriting",
    "Documents":           "forms/checklist requests, wrong form version, upload failures, 1035 exchange paperwork",
    "Policy Servicing":    "beneficiary/address changes, billing, cash value, loans/withdrawals, annuity growth questions",
    "Process":             "commission/comp, carrier appointment/licensing, general how-to/workflow",
    "Claims & Maturity":   "death claims, annuitization/maturity, surrender requests",
    "Technical":           "portal login/access issues, book-of-business data/report requests",
}


# ══════════════════════════════════════════════════════════════════════════════
def load_split():
    cases = pd.read_csv(DATA / "fact_cases.csv")
    X = cases["description"].fillna("").to_numpy()
    y = cases["category_tagged"].to_numpy()   # the RECORDED label (carries intake noise)
    y_true = cases["category"].to_numpy()      # the TRUE intent (gold)
    return train_test_split(X, y, y_true, test_size=0.2, random_state=RNG, stratify=y)


def run_sklearn(Xtr, Xte, ytr, yte):
    vec = TfidfVectorizer(stop_words=build_stopwords(), ngram_range=(1, 2),
                          min_df=5, max_df=0.4, sublinear_tf=True)
    Xtr_v = vec.fit_transform(Xtr)
    Xte_v = vec.transform(Xte)
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")
    clf.fit(Xtr_v, ytr)
    pred = clf.predict(Xte_v)
    return pred, clf, vec


# ── Claude tier ───────────────────────────────────────────────────────────────
def _claude_client():
    try:
        import anthropic
    except ImportError:
        raise SystemExit("pip install anthropic  (and set ANTHROPIC_API_KEY) to use --claude")
    return anthropic.Anthropic()


def _system_prompt():
    lines = ["You are an operations triage assistant for a financial-products "
             "(life insurance & annuity) client-services team. Classify each inbound "
             "advisor message into exactly ONE routing category:\n"]
    for c in CATEGORIES:
        lines.append(f"- {c}: {_CATEGORY_HINTS[c]}")
    lines.append("\nReturn only the category. Choose the single best fit.")
    return "\n".join(lines)


def claude_classify(client, messages):
    """Zero-shot classify a list of message strings → list of category labels."""
    system = [{"type": "text", "text": _system_prompt(),
               "cache_control": {"type": "ephemeral"}}]  # stable taxonomy → cache
    schema = {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": CATEGORIES}},
        "required": ["category"], "additionalProperties": False,
    }
    preds, cache_reads = [], 0
    for i, msg in enumerate(messages, 1):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=64, system=system,
                messages=[{"role": "user", "content": f"Message:\n{msg}"}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
            text = next(b.text for b in resp.content if b.type == "text")
            preds.append(json.loads(text)["category"])
            cache_reads += getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        except Exception as e:
            print(f"   ⚠️  classify call {i} failed: {e}")
            preds.append("New Business")  # fallback to modal class
        if i % 25 == 0:
            print(f"   …classified {i}/{len(messages)}")
    if cache_reads:
        print(f"   (prompt-cache reads: {cache_reads:,} tokens)")
    return preds


def draft_replies(client, rows, path):
    system = ("You are a senior operations specialist drafting a first-response "
              "reply to a financial advisor's request about a life-insurance or "
              "annuity case. Be concise, professional, and specific: acknowledge, "
              "state the concrete next step or info needed, and set an expectation. "
              "5 sentences max. Do not invent policy numbers, rates, or carrier specifics.")
    out = ["# Claude-drafted first-response replies (demo)\n",
           "> Generated by ml_classify.py --draft. Review before sending.\n"]
    for r in rows:
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=300,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content":
                           f"Category: {r['category']}\nClient message:\n{r['description']}"}],
            )
            reply = next(b.text for b in resp.content if b.type == "text")
        except Exception as e:
            reply = f"_(draft failed: {e})_"
        out.append(f"### [{r['category']}] {r['subject']}\n**Client:** {r['description']}\n\n"
                   f"**Draft reply:**\n{reply}\n\n---\n")
    path.write_text("\n".join(out))
    print(f"   → wrote {path}")


# ══════════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude", action="store_true", help="add the Claude zero-shot head-to-head")
    ap.add_argument("--sample", type=int, default=150,
                    help="test tickets to score Claude on (kept small for cost)")
    ap.add_argument("--draft", action="store_true", help="also draft sample first-response replies")
    args = ap.parse_args()

    Xtr, Xte, ytr, yte, _gtr, gte = load_split()
    mis = (yte != gte)   # test tickets whose recorded label ≠ true intent
    print(f"Train: {len(Xtr):,}   Test: {len(Xte):,}   Classes: {len(CATEGORIES)}")
    print(f"Intake mis-tag rate in test set: {mis.mean()*100:.1f}%  "
          f"(this caps agreement with recorded labels)")

    sk_pred, _, _ = run_sklearn(Xtr, Xte, ytr, yte)
    sk_f1 = f1_score(yte, sk_pred, average="macro")
    sk_acc = accuracy_score(yte, sk_pred)

    lines = ["Ticket Triage Bake-off — classic ML vs. Claude",
             "=" * 64,
             f"Task: route inbound message → 1 of {len(CATEGORIES)} ops queues.",
             f"Labels carry realistic intake noise — {mis.mean()*100:.0f}% of test tickets",
             "are mis-tagged at intake, so ~1.0 agreement is impossible and unwanted.",
             f"Train: {len(Xtr):,}   Test: {len(Xte):,}\n",
             "TF-IDF + Logistic Regression vs. RECORDED label (full test split)",
             f"  macro-F1 : {sk_f1:.3f}",
             f"  accuracy : {sk_acc:.3f}",
             "\nPer-class (classic ML):",
             classification_report(yte, sk_pred, digits=3)]
    print("\n".join(lines[:9]))

    if args.claude:
        # Score BOTH models on the same random sample for a fair comparison.
        rng = np.random.default_rng(RNG)
        idx = rng.choice(len(Xte), size=min(args.sample, len(Xte)), replace=False)
        Xs, ys, gs, ms = Xte[idx], yte[idx], gte[idx], mis[idx]
        print(f"\nClaude zero-shot on {len(Xs)} sampled test tickets (model={MODEL})…")
        client = _claude_client()
        cl_pred = np.array(claude_classify(client, list(Xs)))
        sk_sample = sk_pred[idx]

        def scores(pred):
            return (f1_score(ys, pred, average="macro"), accuracy_score(ys, pred),
                    accuracy_score(gs, pred),                       # vs TRUE intent
                    accuracy_score(gs[ms], pred[ms]) if ms.any() else float("nan"))

        sk_f1s, sk_accs, sk_true, sk_rec = scores(sk_sample)
        cl_f1s, cl_accs, cl_true, cl_rec = scores(cl_pred)

        lines += [
            "\n" + "=" * 64,
            f"HEAD-TO-HEAD on the same {len(Xs)} test tickets",
            f"  {'model':<26}{'macroF1':>9}{'acc':>7}{'vs-true':>9}{'train':>8}",
            "  (acc = agreement w/ recorded label;  vs-true = agreement w/ true intent)",
            f"  {'TF-IDF + LogReg':<26}{sk_f1s:>9.3f}{sk_accs:>7.3f}{sk_true:>9.3f}{f'{len(Xtr)//1000}k':>8}",
            f"  {'Claude 0-shot':<26}{cl_f1s:>9.3f}{cl_accs:>7.3f}{cl_true:>9.3f}{'none':>8}",
            f"\nMis-routed-ticket recovery (correct TRUE queue on the {int(ms.sum())} "
            "intake-mislabeled tickets):",
            f"  TF-IDF + LogReg : {sk_rec*100:5.1f}%",
            f"  Claude 0-shot   : {cl_rec*100:5.1f}%",
            "\nClaude per-class (vs recorded label):",
            classification_report(ys, cl_pred, digits=3),
        ]
        print("\n".join(lines[-12:]))

        if args.draft:
            cases = pd.read_csv(DATA / "fact_cases.csv")
            sample_rows = cases.sample(5, random_state=RNG)[
                ["category", "subject", "description"]].to_dict("records")
            print("\nDrafting sample first-response replies…")
            draft_replies(client, sample_rows, OUT / "draft_replies.md")

    (OUT / "classify_report.txt").write_text("\n".join(lines))
    print(f"\nWrote {OUT / 'classify_report.txt'}")


if __name__ == "__main__":
    main()
