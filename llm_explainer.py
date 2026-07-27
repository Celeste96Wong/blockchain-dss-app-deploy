"""
llm_explainer.py — Stage 3: Grounded LLM Explanation Layer.

CRITICAL DESIGN PRINCIPLE:
The LLM receives only pre-computed, structured results (dimension scores +
diagnostic flags + tier) — NEVER raw question answers. It is explicitly
instructed not to introduce new judgments. This ensures the LLM functions
as a grounded Natural Language Generator (NLG), not an independent
reasoning engine — directly addressing the explanation-understanding gap
(Salimparsa et al., 2025).

Requires OPENAI_API_KEY to be set in a .env file (see .env.example).
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client() -> OpenAI:
    """Lazily initialises the OpenAI client so import doesn't fail without a key."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def build_grounded_prompt(dim_scores: dict, weights: dict, tier: str, overall_score: float, flags: list) -> str:
    """Constructs the grounded prompt. All content is pre-computed and explicitly labelled as such."""
    from questions import DIM_ORDER

    dim_lines = "\n".join(
        f"- {dim}: score={round(dim_scores[dim], 3)} (importance weight={round(weights[dim], 3)})"
        for dim in DIM_ORDER
    )
    rule_lines = "\n".join(f"- {f}" for f in flags)

    prompt = f"""You are a neutral explanation assistant for a blockchain adoption readiness
assessment tool designed for non-technical SME business owners.

Your task: write a plain-language explanation of the assessment results provided below.
Rules you MUST follow:
- Do NOT introduce new judgments, scores, or recommendations beyond what is provided.
- Do NOT mention technical terms like "fuzzy logic", "TOPSIS", "AHP", or "weights".
- Write in clear, supportive, professional English for a business owner with no technical background.
- Length: 150-200 words.
- Do NOT recalculate or second-guess the results below.

ASSESSMENT RESULTS (all pre-computed — your role is to explain, not to re-evaluate):

Overall Readiness Score: {round(overall_score * 100, 1)} / 100
Readiness Tier: {tier}

Dimension Scores:
{dim_lines}

Diagnostic Flags (pre-computed — explain these to the user in plain language):
{rule_lines}

Write the explanation now."""
    return prompt


def generate_llm_explanation(dim_scores: dict, weights: dict, tier: str, overall_score: float, flags: list) -> str:
    """Calls the OpenAI API with the grounded prompt. This is the ONLY function that uses API tokens."""
    client = get_client()
    prompt = build_grounded_prompt(dim_scores, weights, tier, overall_score, flags)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=350,
        temperature=0.4,  # low temperature = consistent, grounded output
    )
    return response.choices[0].message.content


def check_llm_faithfulness(explanation_text: str, diagnostic_flags: list) -> dict:
    """
    Lightweight faithfulness check: verifies that key dimension terms
    identified in the Diagnostic Flags actually appear in the LLM-generated
    explanation. A coverage ratio >= 0.5 is treated as PASS. This is a
    keyword-coverage proxy, not a full semantic entailment check, but is
    sufficient to detect gross hallucination (i.e. the LLM ignoring the
    provided flags entirely).
    """
    key_terms = []
    for flag in diagnostic_flags:
        for dim in ["Economic", "Organizational", "Technological", "Regulatory"]:
            if dim in flag and dim not in key_terms:
                key_terms.append(dim)

    found = [t for t in key_terms if t.lower() in explanation_text.lower()]
    coverage = len(found) / len(key_terms) if key_terms else 1.0

    return {
        "key_terms_from_flags": key_terms,
        "found_in_explanation": found,
        "missing_from_explanation": [t for t in key_terms if t not in found],
        "coverage_ratio": round(coverage, 3),
        "faithfulness_status": "PASS" if coverage >= 0.5 else "WARNING — low grounding coverage",
    }
