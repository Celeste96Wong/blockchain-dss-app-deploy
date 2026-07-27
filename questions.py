"""
questions.py — All question banks used across the system.

Kept in one file, separate from app logic, so that questions can be
reviewed and edited (e.g. after supervisor feedback) without touching
any application or calculation code.
"""

# ============================================================
# CONSENT — granular consent (3 questions) + identifying info
# ============================================================
# Academic basis for minimal identifying-info collection: standard
# research ethics practice (e.g. Tilburg University informed consent
# guidelines; ICPSR recommended consent language) recommends collecting
# only Name + Email as the minimal identifying information needed to
# contact participants, stored separately from response data and never
# published — responses are reported/quoted anonymously regardless.
CONSENT_IDENTITY_FIELDS = {
    "full_name": {"label": "Full Name", "required": True},
    "email": {"label": "Email Address", "required": True},
    "affiliation": {"label": "Organisation / Affiliation (optional)", "required": False},
}

CONSENT_QUESTIONS = {
    "C1_participate": {
        "text": "Do you agree to participate in this academic research study by completing this assessment?",
        "options": ["Yes, I agree to participate", "No, I do not wish to participate"],
    },
    "C2_quote_feedback": {
        "text": "May we quote your feedback (anonymously, without identifying your name or company) in the research paper, presentations, or competition entries?",
        "options": ["Yes, anonymous quotes are okay", "No, please do not quote my feedback"],
    },
    "C3_future_contact": {
        "text": "May we contact you again for related future research?",
        "options": ["Yes, you may contact me again", "No, please do not contact me again"],
    },
}

CONSENT_PRIVACY_NOTE = (
    "We collect your name and email address so we can contact you regarding this "
    "research (e.g. to share results or ask follow-up questions). Your identifying "
    "information is stored separately from your responses and is never published. "
    "Any quotes or findings shared publicly will be fully anonymised — your name and "
    "company will not be disclosed."
)

# ============================================================
# STAGE 0 -> now just "Profile" (auxiliary; not used in Fuzzy computation)
# Renamed per supervisor discussion: the official Proposal document only
# defines Stage 1/2/3 — "Stage 0" was an internal working name used during
# development and should not appear in the user-facing system.
# ============================================================
PROFILE_QUESTIONS = {
    "P1_industry_sector": {
        "text": "Which industry best describes your business?",
        "options": [
            "Retail / Trading", "Professional / Business Services", "Food & Beverage",
            "Construction", "Manufacturing", "Logistics & Supply Chain",
            "Financial Services", "Agriculture", "Others",
        ],
    },
    "P2_company_size": {
        "text": "How many employees does your business have?",
        "options": ["Less than 5 employees", "5 - 29 employees", "30 - 75 employees", "76 - 200 employees"],
    },
    "P3_years_operation": {
        "text": "How many years has your business been operating?",
        "options": ["Less than 2 years", "2 - 5 years", "6 - 10 years", "More than 10 years"],
    },
}


def map_to_official_sme_class(industry: str, size_range: str) -> str:
    """
    Maps simplified employee-count ranges to the official SME Corp Malaysia
    classification. Thresholds differ between manufacturing and other sectors.
    Auxiliary / informational only — does not feed into the Fuzzy computation.
    """
    is_manufacturing = industry == "Manufacturing"
    mapping_manu = {
        "Less than 5 employees": "Micro",
        "5 - 29 employees": "Small",
        "30 - 75 employees": "Small",
        "76 - 200 employees": "Medium",
    }
    mapping_other = {
        "Less than 5 employees": "Micro",
        "5 - 29 employees": "Small",
        "30 - 75 employees": "Medium",
        "76 - 200 employees": "Medium",
    }
    table = mapping_manu if is_manufacturing else mapping_other
    return table.get(size_range, "Unknown")


# ============================================================
# STAGE 1 — Business Suitability Screening
# (Capocasale & Perboli, 2022 — 11 binary questions)
# ============================================================
STAGE1_QUESTIONS = {
    "Q1_multiple_decision_power": "Does your business decision require multiple partners/departments to agree, rather than one person deciding alone?",
    "Q2_trust_third_party": "Is there a trusted third party that all parties are comfortable delegating data management to?",
    "Q3_trust_majority": "Do you trust that the majority of your business partners would not collude against you?",
    "Q4_equal_influence": "Do all parties in your business network have roughly equal bargaining power?",
    "Q5_data_sharing_advantage": "Do you need to share business data (e.g. inventory, logistics, transaction records) with your partners?",
    "Q6_aligned_interests": "Do you and your partners share aligned, cooperative goals on this matter?",
    "Q7_misbehaving_opposed": "If someone tried to cheat, would their interests conflict with other potential cheaters (making collusion unlikely)?",
    "Q8_all_actors_involved": "Are all parties who depend on this data also directly involved in managing the system?",
    "Q9_actors_autonomous": "Are your business partners capable of independently maintaining their own technical systems?",
    "Q10_prevent_retroactive": "Do you need to ensure that past records, once written, cannot be altered (e.g. for audit purposes)?",
    "Q11_prevent_proactive": "Is the original source of your data (e.g. manual entry, sensors) difficult to falsify?",
}

STAGE1_GATE_THRESHOLD = 0.70  # proportion of "Yes" answers required to proceed

# ============================================================
# STAGE 2 — Business Readiness Assessment
# (4 dimensions x 2 questions each = 8 questions)
# ============================================================
STAGE2_QUESTIONS = {
    "Q12_management_support": ("Organizational", "How would you rate your top management's support for adopting new technology like blockchain?"),
    "Q13_staff_resistance": ("Organizational", "How would you rate your staff/partners' openness to changing current workflows? (rate openness, not resistance)"),
    "Q14_infrastructure_compat": ("Technological", "How compatible is your current IT infrastructure with new technology integration?"),
    "Q15_integration_complexity": ("Technological", "How would you rate your internal team's capability to handle technical integration complexity?"),
    "Q16_cost_tolerance": ("Economic", "How tolerant is your business of the upfront installation cost required for new technology?"),
    "Q17_roi_timeline": ("Economic", "How favourable is your expected timeline for seeing return on this investment?"),
    "Q18_regulatory_clarity": ("Regulatory", "How clear is your understanding of the regulatory environment relevant to blockchain (e.g. data protection, financial regulation)?"),
    "Q19_compliance_risk": ("Regulatory", "How willing is your business to tolerate compliance-related uncertainty?"),
}

VALID_STAGE2_OPTIONS = ["Very Low", "Low", "Moderate", "High", "Very High"]

DIMENSIONS = {
    "Organizational": ["Q12_management_support", "Q13_staff_resistance"],
    "Technological": ["Q14_infrastructure_compat", "Q15_integration_complexity"],
    "Economic": ["Q16_cost_tolerance", "Q17_roi_timeline"],
    "Regulatory": ["Q18_regulatory_clarity", "Q19_compliance_risk"],
}
DIM_ORDER = ["Economic", "Organizational", "Technological", "Regulatory"]

# ============================================================
# VALIDATION QUESTIONNAIRES (shown at the end of the flow)
# ============================================================
LIKERT_SCALE = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]

EXPERT_VALIDATION_CLOSED_QUESTIONS = {
    "EQ1_accuracy": "The system's readiness assessment results align with real-world blockchain adoption considerations.",
    "EQ2_practicality": "The questions asked in the assessment are practical and relevant to actual SME decision-making.",
    "EQ3_clarity": "The explanation generated by the system is clear and understandable.",
    "EQ4_trustworthiness": "I would trust this tool's output as a starting point for an SME's blockchain adoption decision.",
    "EQ5_completeness": "The assessment criteria cover the key factors that matter when evaluating blockchain readiness.",
}

# ============================================================
# Fuzzy AHP pairwise comparison — REDESIGNED as choice-based questions
# (previously free-text; changed per supervisor + self-review feedback
# to (a) avoid inconsistent free-text formats, and (b) explicitly show
# the Saaty (1980) Fundamental Scale so industry experts unfamiliar
# with AHP know how to interpret "1" vs "9".)
# ============================================================
SAATY_SCALE_EXPLANATION = (
    "For each comparison below, first choose which factor is more important "
    "(or whether they are equally important), then indicate by how much using "
    "Saaty's (1980) standard scale:\n\n"
    "3 = Moderately more important\n"
    "5 = Strongly more important\n"
    "7 = Very strongly more important\n"
    "9 = Extremely more important\n"
    "(2, 4, 6, 8 = intermediate judgements between these levels)"
)

SAATY_INTENSITY_OPTIONS = [
    "3 - Moderately more important",
    "4",
    "5 - Strongly more important",
    "6",
    "7 - Very strongly more important",
    "8",
    "9 - Extremely more important",
]

EXPERT_AHP_QUESTIONS = {
    "EQ_AHP1": {
        "pair": ("Economic", "Organizational"),
        "context": "Economic factors (e.g. implementation cost, ROI timeline) vs Organizational factors (e.g. management support, staff readiness)",
    },
    "EQ_AHP2": {
        "pair": ("Economic", "Technological"),
        "context": "Economic factors vs Technological factors (e.g. infrastructure compatibility, integration capability)",
    },
    "EQ_AHP3": {
        "pair": ("Economic", "Regulatory"),
        "context": "Economic factors vs Regulatory factors (e.g. regulatory clarity, compliance risk)",
    },
    "EQ_AHP4": {
        "pair": ("Organizational", "Technological"),
        "context": "Organizational factors vs Technological factors",
    },
    "EQ_AHP5": {
        "pair": ("Organizational", "Regulatory"),
        "context": "Organizational factors vs Regulatory factors",
    },
    "EQ_AHP6": {
        "pair": ("Technological", "Regulatory"),
        "context": "Technological factors vs Regulatory factors",
    },
}

EXPERT_DIMENSION_STRUCTURE_QUESTION = {
    "EQ9_dimension_structure": (
        "This assessment uses four dimensions: Economic, Organizational, Technological, and Regulatory. "
        "An alternative is the classic three-dimension TOE framework, where Economic and Regulatory would "
        "be combined into a single 'Environmental' category. For non-technical SME users, which structure "
        "do you find more appropriate?"
    )
}
EXPERT_DIMENSION_STRUCTURE_OPTIONS = [
    "The four-dimension structure (Economic / Organizational / Technological / Regulatory) is more appropriate",
    "The classic three-dimension TOE structure (Technology / Organization / Environment) is more appropriate",
    "No strong preference either way",
]

EXPERT_VALIDATION_OPEN_QUESTIONS = {
    "EQ6_missing_factors": "Are there any important readiness factors that you feel the system did NOT ask about, but should have?",
    "EQ7_improvement": "What would you change or improve about this tool?",
    "EQ8_general_feedback": "Any other comments or feedback you'd like to share?",
}

SME_VALIDATION_CLOSED_QUESTIONS = {
    "SQ1_ease_of_use": "The assessment was easy to complete without needing technical knowledge.",
    "SQ2_understandability": "I understood the explanation the system gave me about my results.",
    "SQ3_usefulness": "This assessment helped me think more clearly about whether blockchain is relevant to my business.",
    "SQ4_would_use_again": "I would consider using a tool like this before making a real business technology decision.",
}

SME_VALIDATION_OPEN_QUESTIONS = {
    "SQ5_open_feedback": "Was there anything confusing or unclear during the assessment?",
}
