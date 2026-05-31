"""
analyze_patterns.py — Surface the most common ticket patterns and turn them into
a prioritized knowledge-base (KB) backlog.

This is the "LLM analysis" layer of the project. It works in two passes:

  1. DETERMINISTIC pattern mining (pure pandas, always runs):
     Ranks case types by a KB-opportunity score that rewards high volume,
     high handle time, low first-contact-resolution, and high reopen rate —
     i.e. the tickets that cost the most and are most fixable with self-serve
     content. Writes out/ticket_patterns.csv and out/kb_backlog.csv.

  2. OPTIONAL LLM drafting (--llm):
     For the top-N patterns, drafts a targeted KB article (title, summary,
     step-by-step answer, tags) from representative client messages. Uses
     Gemini via google-genai if GOOGLE_API_KEY / Vertex creds are present;
     otherwise falls back to a deterministic template so the pipeline always
     produces output. Writes out/kb_articles.md.

Run:
    python analyze_patterns.py            # pattern mining + KB backlog
    python analyze_patterns.py --llm      # also draft KB articles with an LLM
    python analyze_patterns.py --llm --top 8
"""

import argparse
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
def load():
    cases = pd.read_csv(DATA / "fact_cases.csv")
    comments = pd.read_csv(DATA / "fact_case_comments.csv")
    return cases, comments


def mine_patterns(cases: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per case type and compute a KB-opportunity score."""
    closed = cases[cases.status == "Closed"].copy()
    closed["sla_met"] = closed["sla_met"].astype(str).str.lower().eq("true")

    g = closed.groupby(["category", "subcategory", "subject", "kb_addressable"], as_index=False).agg(
        volume=("case_number", "count"),
        avg_handle_min=("handle_time_minutes", "mean"),
        avg_first_response_min=("first_response_minutes", "mean"),
        fcr_rate=("is_first_contact_resolution", "mean"),
        reopen_rate=("reopened_count", lambda s: (s > 0).mean()),
        sla_met_rate=("sla_met", "mean"),
        avg_csat=("csat_score", lambda s: pd.to_numeric(s, errors="coerce").mean()),
    )

    total = g["volume"].sum()
    g["volume_share"] = g["volume"] / total

    # KB-opportunity score: high volume × handle cost × (low FCR) × (reopens hurt).
    # Normalize each driver to 0–1 so the score is interpretable.
    def norm(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng else s * 0
    g["kb_opportunity_score"] = (
        0.45 * norm(g["volume"])
        + 0.25 * norm(g["avg_handle_min"])
        + 0.20 * (1 - g["fcr_rate"])
        + 0.10 * norm(g["reopen_rate"])
    ).round(3)

    g = g.sort_values("kb_opportunity_score", ascending=False).reset_index(drop=True)
    for c in ["avg_handle_min", "avg_first_response_min", "avg_csat"]:
        g[c] = g[c].round(1)
    for c in ["fcr_rate", "reopen_rate", "sla_met_rate", "volume_share"]:
        g[c] = (g[c] * 100).round(1)
    return g


def build_backlog(patterns: pd.DataFrame, top: int) -> pd.DataFrame:
    """Turn the top KB-addressable patterns into a prioritized content backlog."""
    cand = patterns[patterns.kb_addressable].head(top).copy()
    # Rough deflection model: a good KB article deflects 25–40% of a pattern's
    # volume, weighted by how repetitive (low-FCR) it is.
    cand["est_deflectable_cases_per_mo"] = (
        cand["volume"] / 18 * (0.25 + 0.15 * (1 - cand["fcr_rate"] / 100))
    ).round(1)
    cand["est_hours_saved_per_mo"] = (
        cand["est_deflectable_cases_per_mo"] * cand["avg_handle_min"] / 60
    ).round(1)
    cand.insert(0, "priority", range(1, len(cand) + 1))
    cols = ["priority", "category", "subcategory", "subject", "volume",
            "avg_handle_min", "fcr_rate", "kb_opportunity_score",
            "est_deflectable_cases_per_mo", "est_hours_saved_per_mo"]
    return cand[cols]


# ──────────────────────────────────────────────────────────────────────────────
MODEL = os.getenv("OPS_LLM_MODEL", "claude-opus-4-8")

_KB_SYSTEM = ("You are a knowledge-base writer for a financial-products operations "
              "team (life insurance & annuities). Given representative inbound advisor "
              "messages for one recurring ticket type, write a concise, self-serve KB "
              "article in markdown: an H3 title, a one-line summary, a numbered "
              "step-by-step answer (4-7 steps), and a short 'Forms / links' line. Keep "
              "it carrier-agnostic where possible. Do not invent specific rates, form "
              "numbers, or policy details.")

def _claude_client():
    """Return an Anthropic client if the SDK + key are present, else None."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic()


def draft_article(row, examples, client):
    """Draft one KB article. Uses Claude when available, else a template."""
    examples_block = "\n".join(f"- {e}" for e in examples[:6])
    if client is not None:
        user = (f'Ticket type: "{row.subject}"  (category: {row.category} / '
                f"{row.subcategory}).\n\nRepresentative advisor messages:\n{examples_block}")
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=600,
                system=[{"type": "text", "text": _KB_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],  # stable → cache
                messages=[{"role": "user", "content": user}],
            )
            return next(b.text for b in resp.content if b.type == "text").strip()
        except Exception as e:
            print(f"   ⚠️  LLM call failed ({e}); using template for '{row.subject}'")

    # Deterministic fallback template (built line-by-line to avoid indent issues).
    return "\n".join([
        f"### {row.subject}",
        f'**Summary:** Self-serve guidance for the most common "{row.subcategory}" '
        f"requests ({int(row.volume)} cases, avg {row.avg_handle_min} min to handle, "
        f"{row.fcr_rate}% first-contact resolution).",
        "",
        "**Steps**",
        "1. Confirm the carrier and product involved.",
        "2. Gather the policy / application number and the advisor's contact on file.",
        "3. Identify the exact requirement or question from the common asks below.",
        "4. Apply the standard resolution and confirm completion with the advisor.",
        f"5. If blocked by the carrier, escalate per the {row.category} playbook.",
        "",
        "**Common client asks**",
        examples_block,
        "",
        "**Forms / links:** _add carrier-specific form numbers and portal links here._",
    ])


def run_llm(patterns, comments, top):
    client = _claude_client()
    where = f"Claude ({MODEL})" if client else "template fallback (no ANTHROPIC_API_KEY)"
    print(f"\n✍️   Drafting KB articles via {where} …")

    # Representative client messages per subject.
    client_msgs = comments[comments.author_type == "Client"]
    cand = patterns[patterns.kb_addressable].head(top)

    cases = pd.read_csv(DATA / "fact_cases.csv")[["case_number", "subject"]]
    msg_by_subject = (client_msgs.merge(cases, on="case_number")
                      .groupby("subject")["body"].apply(list).to_dict())

    articles = ["# Knowledge Base — Auto-drafted from ticket patterns\n",
                "> Generated by analyze_patterns.py. Review before publishing.\n"]
    for _, row in cand.iterrows():
        ex = msg_by_subject.get(row.subject, [row.subject])
        # de-dup similar templated messages
        seen, uniq = set(), []
        for e in ex:
            key = e[:40]
            if key not in seen:
                seen.add(key); uniq.append(e)
        print(f"   • {row.subject}")
        articles.append(draft_article(row, uniq, client))
        articles.append("\n---\n")
    (OUT / "kb_articles.md").write_text("\n".join(articles))
    print(f"   → wrote {OUT / 'kb_articles.md'}")


# ──────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="also draft KB articles with an LLM")
    ap.add_argument("--top", type=int, default=10, help="number of patterns for the KB backlog")
    args = ap.parse_args()

    cases, comments = load()
    patterns = mine_patterns(cases)
    backlog = build_backlog(patterns, args.top)

    patterns.to_csv(OUT / "ticket_patterns.csv", index=False)
    backlog.to_csv(OUT / "kb_backlog.csv", index=False)

    print("📊  Top ticket patterns by KB-opportunity score\n")
    show = patterns.head(args.top)[
        ["subject", "volume", "avg_handle_min", "fcr_rate", "kb_opportunity_score"]]
    print(show.to_string(index=False))
    print(f"\n🧱  KB backlog (top {args.top}) → est. {backlog.est_hours_saved_per_mo.sum():.0f} "
          f"agent-hours/month deflectable")
    print(f"   wrote {OUT / 'ticket_patterns.csv'} and {OUT / 'kb_backlog.csv'}")

    if args.llm:
        run_llm(patterns, comments, args.top)


if __name__ == "__main__":
    main()
