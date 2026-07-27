"""
fuzzy_engine.py — Stage 2 core computation logic.

Implements:
  - Triangular Fuzzy Number (TFN) linguistic scale
  - Chang's (1992) Fuzzy Extent Analysis for dimension weighting
  - Fuzzy TOPSIS for per-question scoring
  - Sensitivity analysis (robustness check)
  - Rule-based diagnostic flag generation

This module has NO external dependencies beyond numpy — it can be
imported and tested independently of the Streamlit app or the LLM layer.

Academic basis: Naseem, Yang, Zhang & Alam (2023). Sustainability, 15(10), 7961.

IMPORTANT — Academic honesty note:
The PAIRWISE_TFN matrix below is a RESEARCHER-CONSTRUCTED SEED matrix,
built to reflect the ORDINAL importance ranking reported in Naseem et al.
(2023): Economic > Organizational > Technological > Regulatory. No
published study has conducted a formal Fuzzy AHP pairwise comparison at
this exact 4-dimension level — this is a provisional starting point,
to be replaced with primary expert pairwise comparison data collected
during Expert Validation (see questions.py, EXPERT_AHP_QUESTIONS).
"""

import numpy as np
from questions import DIMENSIONS, DIM_ORDER

# ============================================================
# TFN Scale (Chang's Extent Analysis standard linguistic scale)
# ============================================================
TFN_SCALE = {
    "Very Low": (1, 1, 3),
    "Low": (1, 3, 5),
    "Moderate": (3, 5, 7),
    "High": (5, 7, 9),
    "Very High": (7, 9, 9),
}
FUZZY_POSITIVE_IDEAL = (7, 9, 9)  # equivalent to "Very High"
FUZZY_NEGATIVE_IDEAL = (1, 1, 3)  # equivalent to "Very Low"


def linguistic_to_tfn(label: str) -> tuple:
    return TFN_SCALE[label]


# ============================================================
# Provisional pairwise comparison matrix (seed values — see module docstring)
# ============================================================
PAIRWISE_TFN = {
    ("Economic", "Organizational"): (1, 1, 2),
    ("Economic", "Technological"): (1, 2, 3),
    ("Economic", "Regulatory"): (2, 3, 4),
    ("Organizational", "Technological"): (1, 1, 2),
    ("Organizational", "Regulatory"): (1, 2, 3),
    ("Technological", "Regulatory"): (1, 1, 2),
}


def build_comparison_matrix():
    """Builds the full n×n fuzzy pairwise comparison matrix with a safety check."""
    n = len(DIM_ORDER)
    M = [[None] * n for _ in range(n)]
    for i, di in enumerate(DIM_ORDER):
        for j, dj in enumerate(DIM_ORDER):
            if i == j:
                M[i][j] = (1, 1, 1)
            elif (di, dj) in PAIRWISE_TFN:
                M[i][j] = PAIRWISE_TFN[(di, dj)]
            elif (dj, di) in PAIRWISE_TFN:
                l, m, u = PAIRWISE_TFN[(dj, di)]
                M[i][j] = (1 / u, 1 / m, 1 / l)
    for i, di in enumerate(DIM_ORDER):
        for j, dj in enumerate(DIM_ORDER):
            assert M[i][j] is not None, f"Pairwise matrix cell ({di}, {dj}) is undefined."
    return M


def chang_extent_analysis(M):
    """
    Chang's (1992) Fuzzy Extent Analysis, as applied in Naseem et al. (2023).
    Returns normalised crisp weights for each dimension.

    Note on Consistency Ratio (CR): not computed here, since this matrix is
    researcher-constructed rather than elicited from a human respondent.
    CR will be meaningful once real expert pairwise data is collected.
    """
    n = len(M)
    row_sums = []
    for row in M:
        l = sum(x[0] for x in row)
        m = sum(x[1] for x in row)
        u = sum(x[2] for x in row)
        row_sums.append((l, m, u))
    total_l = sum(r[0] for r in row_sums)
    total_m = sum(r[1] for r in row_sums)
    total_u = sum(r[2] for r in row_sums)
    S = [(l / total_u, m / total_m, u / total_l) for (l, m, u) in row_sums]

    def degree_possibility(s1, s2):
        l1, m1, u1 = s1
        l2, m2, u2 = s2
        if m1 >= m2:
            return 1
        elif l2 >= u1:
            return 0
        else:
            return (l2 - u1) / ((m1 - u1) - (m2 - l2))

    min_degrees = []
    for i in range(n):
        degrees = [degree_possibility(S[i], S[j]) for j in range(n) if j != i]
        min_degrees.append(min(degrees))
    total = sum(min_degrees)
    weights = [d / total for d in min_degrees]
    return dict(zip(DIM_ORDER, weights))


def get_default_weights():
    """Convenience function: builds matrix and returns dimension weights."""
    M = build_comparison_matrix()
    return chang_extent_analysis(M)


# ============================================================
# Fuzzy TOPSIS scoring
# ============================================================
def fuzzy_distance(a, b):
    """Vertex distance between two TFNs."""
    return np.sqrt((1 / 3) * sum((a[k] - b[k]) ** 2 for k in range(3)))


def fuzzy_topsis_score(answer_label: str) -> float:
    """
    Fuzzy TOPSIS Closeness Coefficient (CC) for a single criterion answer,
    relative to the fuzzy positive-ideal (Very High) and negative-ideal
    (Very Low) solutions. CC closer to 1 = closer to positive ideal.
    """
    tfn = linguistic_to_tfn(answer_label)
    d_pos = fuzzy_distance(tfn, FUZZY_POSITIVE_IDEAL)
    d_neg = fuzzy_distance(tfn, FUZZY_NEGATIVE_IDEAL)
    return d_neg / (d_pos + d_neg) if (d_pos + d_neg) != 0 else 0


def evaluate_stage2(answers: dict, weights: dict):
    """
    Computes per-dimension scores and the final weighted readiness score.

    answers: dict mapping question key -> linguistic label (e.g. "High")
    weights: dict mapping dimension name -> weight (from chang_extent_analysis)
    """
    dim_scores = {}
    for dim, qs in DIMENSIONS.items():
        ccs = [fuzzy_topsis_score(answers[q]) for q in qs]
        dim_scores[dim] = float(np.mean(ccs))
    overall = sum(dim_scores[d] * weights[d] for d in DIM_ORDER)
    return dim_scores, overall


def score_to_tier(score_0_to_1: float) -> str:
    """
    Maps continuous overall readiness score to a discrete Tier classification.

    PROVISIONAL DESIGN — equal-width quartile bands (0.25 each). No
    literature-derived empirical cut-points exist for this specific scoring
    scheme; these thresholds should be recalibrated using real sample data
    once Expert Validation / SME User Testing data is collected.
    """
    if score_0_to_1 < 0.25:
        return "Tier 1 — Not Ready"
    elif score_0_to_1 < 0.50:
        return "Tier 2 — Emerging Readiness"
    elif score_0_to_1 < 0.75:
        return "Tier 3 — Ready"
    else:
        return "Tier 4 — Highly Ready"


# ============================================================
# Sensitivity analysis (robustness check)
# ============================================================
def sensitivity_analysis(dim_scores: dict, base_weights: dict, perturbation: float = 0.10):
    """Perturbs each dimension weight by ±10%, re-normalises, and recomputes the overall score."""
    results = {}
    for target_dim in base_weights:
        for direction, sign in [("increase", +1), ("decrease", -1)]:
            perturbed = dict(base_weights)
            perturbed[target_dim] = max(0, perturbed[target_dim] * (1 + sign * perturbation))
            total = sum(perturbed.values())
            perturbed = {k: v / total for k, v in perturbed.items()}
            new_score = sum(dim_scores[d] * perturbed[d] for d in DIM_ORDER)
            results[f"{target_dim}_{direction}_10pct"] = round(new_score, 4)
    return results


# ============================================================
# Diagnostic rule layer
# ============================================================
def generate_diagnostic_flags(dim_scores: dict, weights: dict) -> list:
    """
    Generates plain-language diagnostic labels based on pre-computed Fuzzy
    scores. These labels — NOT the raw scores — are what gets passed to the
    LLM, enforcing the Grounded Generation principle (see llm_explainer.py).
    """
    flags = []
    strongest_dim = max(dim_scores, key=dim_scores.get)
    weakest_dim = min(dim_scores, key=dim_scores.get)
    flags.append(f"Strongest dimension: {strongest_dim} (score={round(dim_scores[strongest_dim], 3)})")
    flags.append(f"Weakest dimension: {weakest_dim} (score={round(dim_scores[weakest_dim], 3)})")

    for dim in DIM_ORDER:
        if dim_scores[dim] < 0.4 and weights[dim] > 0.20:
            flags.append(f"RULE: {dim} is heavily weighted AND scored low — this is a primary barrier.")
    for dim in DIM_ORDER:
        if dim_scores[dim] > 0.6 and weights[dim] < 0.15:
            flags.append(f"RULE: {dim} scored well but carries low weight — limited impact on overall readiness.")

    score_spread = max(dim_scores.values()) - min(dim_scores.values())
    if score_spread > 0.4:
        flags.append("RULE: Large disparity between strongest and weakest dimensions — uneven readiness profile.")
    else:
        flags.append("RULE: Readiness is relatively balanced across all dimensions.")
    return flags


# ============================================================
# Stage 1 gate logic
# ============================================================
def evaluate_stage1(answers: dict, threshold: float = 0.70) -> dict:
    """
    Binary suitability screening gate.
    Threshold of 0.70 follows the three-tier judgment pattern observed in
    the US Federal Blockchain Playbook scoring bands, adapted to this
    11-question binary structure.
    """
    yes_count = sum(1 for v in answers.values() if v == "Yes")
    total = len(answers)
    ratio = yes_count / total
    if ratio >= threshold:
        decision = "PROCEED"
        message = "Your business context appears structurally suitable for blockchain consideration."
    else:
        decision = "STOP"
        message = (
            "Based on your responses, blockchain technology does not appear well-suited to your "
            "current business context. A traditional centralised database or system may better "
            "meet your needs with lower complexity and cost."
        )
    return {
        "yes_count": yes_count,
        "total_questions": total,
        "ratio": round(ratio, 3),
        "gate_decision": decision,
        "message": message,
    }
