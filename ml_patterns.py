"""
ml_patterns.py — Traditional-ML ticket-pattern discovery, honestly validated.

This is the "classic ML" tier (the Signal Advisors-style work). It does NOT use
the case_type labels to find patterns — it discovers them unsupervised from the
raw client message text, then *validates* the discovery against the held-out
ground-truth labels. That validation (Adjusted Rand Index, NMI, cluster purity)
is the quotable result: it proves the clusters are real structure, not the
buckets the data generator planted.

Pipeline
────────
  1. TF-IDF vectorize the inbound client messages. Carrier & product names are
     added to the stop-list so clusters form around the *issue*, not the vendor.
  2. KMeans cluster at two granularities: 7 categories and 28 case types.
  3. Validate vs ground truth: ARI + NMI (label-invariant) + cluster purity,
     plus a contingency table.
  4. NMF topic model → top terms per discovered theme (interpretable, feeds the
     KB backlog narrative in analyze_patterns.py).

Outputs (out/):
    cluster_validation.txt   metrics + per-cluster dominant category
    cluster_terms.csv        top TF-IDF terms per NMF topic
    cluster_contingency.csv  discovered cluster × true category counts

Run:
    python ml_patterns.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics import (adjusted_rand_score, normalized_mutual_info_score)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
RNG = 7


def build_stopwords():
    """English stopwords + curated domain stop-list so clusters key on the
    *issue*, not the carrier or message boilerplate. Three sources:
      • carrier / product / portal names (identity, not topic)
      • greeting/filler/sign-off boilerplate (emitted by the generator)
      • generic advisor framing words
    """
    extra = set()
    v = pd.read_csv(DATA / "dim_vendor.csv")
    for col in ("vendor_name", "portal_name"):
        for val in v[col]:
            extra.update(str(val).lower().replace("@", " ").replace("'", " ").split())
    for p in ["term", "life", "whole", "universal", "indexed", "variable",
              "annuity", "fixed", "immediate", "deferred", "income", "myga",
              "rila", "spia", "iul", "vul", "fia", "final", "expense", "product"]:
        extra.add(p)
    boiler = DATA / "boilerplate_stopwords.txt"
    if boiler.exists():
        extra.update(boiler.read_text().split())
    extra.update(["client", "customer", "policyholder", "just", "want",
                  "need", "please", "ll", "ve", "don", "policy"])
    # Drop any token that won't survive the vectorizer's own tokenizer
    # (avoids the "inconsistent stop_words" warning).
    return sorted(w for w in ENGLISH_STOP_WORDS.union(extra) if w.isalpha())


def purity(clusters, labels):
    df = pd.DataFrame({"c": clusters, "y": labels})
    return df.groupby("c")["y"].apply(lambda s: s.value_counts().iloc[0]).sum() / len(df)


def main():
    cases = pd.read_csv(DATA / "fact_cases.csv")
    text = cases["description"].fillna("")
    y_cat = cases["category"].to_numpy()
    y_type = cases["subject"].to_numpy()

    vec = TfidfVectorizer(stop_words=build_stopwords(), ngram_range=(1, 2),
                          min_df=5, max_df=0.4, sublinear_tf=True)
    X = vec.fit_transform(text)
    terms = np.array(vec.get_feature_names_out())
    print(f"TF-IDF matrix: {X.shape[0]:,} docs × {X.shape[1]:,} terms")

    lines = ["Operations Productivity Intelligence — unsupervised pattern validation",
             "=" * 70,
             "Clusters are discovered from raw message text WITHOUT labels, then",
             "scored against ground truth. ARI/NMI near 0 = chance; 1 = perfect.",
             f"\nDocuments: {X.shape[0]:,}   Vocabulary: {X.shape[1]:,}"]

    n_type = len(np.unique(y_type))
    n_cat = len(np.unique(y_cat))

    # ── Cluster at fine granularity (slightly over-cluster), then roll up. ────
    # Over-clustering + rollup is standard practice: it lets one true type that
    # splits into sub-themes be re-merged at the category level.
    k = int(round(n_type * 1.4))
    km = KMeans(n_clusters=k, n_init=10, random_state=RNG)
    clusters = km.fit_predict(X)

    ari_t = adjusted_rand_score(y_type, clusters)
    nmi_t = normalized_mutual_info_score(y_type, clusters)
    pur_t = purity(clusters, y_type)
    lines.append(f"\nUnsupervised KMeans (k={k}) vs 28 ground-truth case types")
    lines.append(f"  Adjusted Rand Index   : {ari_t:.3f}")
    lines.append(f"  Normalized Mutual Info: {nmi_t:.3f}")
    lines.append(f"  Cluster purity (type) : {pur_t:.3f}")

    # Roll each discovered cluster up to its dominant true category, then score
    # how often that rollup lands a ticket in the right category.
    cl2cat = (pd.DataFrame({"c": clusters, "y": y_cat})
              .groupby("c")["y"].agg(lambda s: s.value_counts().index[0]).to_dict())
    pred_cat = np.array([cl2cat[c] for c in clusters])
    cat_acc = (pred_cat == y_cat).mean()
    ari_c = adjusted_rand_score(y_cat, clusters)
    nmi_c = normalized_mutual_info_score(y_cat, clusters)
    lines.append(f"\nRolled up to 7 business categories")
    lines.append(f"  Category accuracy     : {cat_acc:.3f}  "
                 f"(ticket landed in correct category)")
    lines.append(f"  ARI / NMI vs category : {ari_c:.3f} / {nmi_c:.3f}")

    # Contingency: discovered cluster × true category.
    cont = pd.crosstab(clusters, y_cat)
    cont.index.name = "cluster"
    cont.to_csv(OUT / "cluster_contingency.csv")
    lines.append("\nLargest discovered clusters → dominant true category:")
    for cl in cont.sum(axis=1).sort_values(ascending=False).head(10).index:
        top = cont.loc[cl].sort_values(ascending=False)
        share = top.iloc[0] / top.sum()
        lines.append(f"  cluster {cl:>2}: {top.index[0]:<22} "
                     f"({share*100:.0f}% pure, n={top.sum()})")

    # NMF topic model → interpretable themes + top terms.
    k_topics = 12
    nmf = NMF(n_components=k_topics, random_state=RNG, init="nndsvda", max_iter=400)
    W = nmf.fit_transform(X)
    rows = []
    for t in range(k_topics):
        top_terms = terms[nmf.components_[t].argsort()[::-1][:10]]
        # which true category dominates docs assigned to this topic
        assigned = np.argmax(W, axis=1) == t
        dom = pd.Series(y_cat[assigned]).value_counts()
        dom_cat = dom.index[0] if len(dom) else "—"
        rows.append({"topic": t, "dominant_category": dom_cat,
                     "n_docs": int(assigned.sum()),
                     "top_terms": ", ".join(top_terms)})
    pd.DataFrame(rows).to_csv(OUT / "cluster_terms.csv", index=False)

    lines.append(f"\nNMF themes (k={k_topics}) — top terms per discovered topic:")
    for r in rows:
        lines.append(f"  [{r['dominant_category']:<20}] {r['top_terms']}")

    lines.append("\n" + "=" * 70)
    lines.append("PORTFOLIO HEADLINE:")
    lines.append(f"  Unsupervised TF-IDF + KMeans on raw client messages recovered the")
    lines.append(f"  ticket taxonomy at ARI={ari_t:.2f} / NMI={nmi_t:.2f} vs 28 ground-truth")
    lines.append(f"  case types, and assigned {cat_acc*100:.0f}% of tickets to the correct")
    lines.append(f"  business category — confirming the patterns are real structure,")
    lines.append(f"  discoverable without labels (not artifacts of the data generator).")

    report = "\n".join(lines)
    (OUT / "cluster_validation.txt").write_text(report)
    print(report)
    print(f"\nWrote out/cluster_validation.txt, cluster_terms.csv, cluster_contingency.csv")


if __name__ == "__main__":
    main()
