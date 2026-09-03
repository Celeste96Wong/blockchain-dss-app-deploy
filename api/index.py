"""
api/index.py — Main Flask application (Vercel entrypoint).

Uses Flask's cookie-based session (client-side, signed) rather than any
server-side session store — this is required because Vercel serverless
functions are stateless between requests (different invocations may run
on different instances), so anything relying on in-memory server state
would break in production. Cookie-based sessions travel with the client,
so they work correctly in this environment.

Local development:
    cd blockchain-dss-app-deploy
    python api/index.py
    (then open http://localhost:5000)

Deployment: this file is automatically detected by Vercel's Python
runtime when deployed with the accompanying vercel.json.
"""

import os
import sys
import json
import secrets

# Allow importing sibling modules (fuzzy_engine.py, llm_explainer.py, etc.)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

from questions import (
    CONSENT_QUESTIONS, CONSENT_IDENTITY_FIELDS, CONSENT_PRIVACY_NOTE, CONSENT_STORY,
    PROFILE_QUESTIONS, PROFILE_EXPERT_NOTE, STAGE_EXPERT_NOTE_EMPLOYMENT,
    STAGE_EXPERT_NOTE_ORGANISATION, RESULTS_TO_VALIDATION_NOTE,
    map_to_official_sme_class,
    STAGE1_QUESTIONS, STAGE2_QUESTIONS, VALID_STAGE2_OPTIONS, DIM_ORDER,
    LIKERT_SCALE, EXPERT_VALIDATION_CLOSED_QUESTIONS, NEGATIVE_LIKERT_RESPONSES,
    SAATY_SCALE_EXPLANATION, SAATY_INTENSITY_OPTIONS, EXPERT_AHP_QUESTIONS,
    EXPERT_DIMENSION_STRUCTURE_QUESTION, EXPERT_DIMENSION_STRUCTURE_OPTIONS,
    EXPERT_VALIDATION_OPEN_QUESTIONS,
    SME_VALIDATION_CLOSED_QUESTIONS, SME_VALIDATION_OPEN_QUESTIONS,
)
from fuzzy_engine import (
    get_default_weights, evaluate_stage1, evaluate_stage2,
    generate_diagnostic_flags, score_to_tier,
)
from llm_explainer import generate_llm_explanation, check_llm_faithfulness
from db import save_session_record, is_using_local_fallback, kv_list_keys, kv_get, kv_delete

load_dotenv()

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))


# ============================================================
# CONSENT
# ============================================================
@app.route("/", methods=["GET", "POST"])
@app.route("/consent", methods=["GET", "POST"])
def consent():
    if request.method == "POST":
        answers = {key: request.form.get(key) for key in CONSENT_QUESTIONS}
        identity = {
            "preferred_name": request.form.get("preferred_name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "organization": request.form.get("organization", "").strip(),
            "position": request.form.get("position", "").strip(),
        }
        if not all(identity.values()):
            flash("Please provide your name, email, organization, and position to continue.", "warning")
            return render_template("consent.html", consent_questions=CONSENT_QUESTIONS,
                                    privacy_note=CONSENT_PRIVACY_NOTE, consent_story=CONSENT_STORY)

        session["consent_answers"] = answers
        session["identity"] = identity

        if not answers["C1_participate"].startswith("Yes"):
            flash("You have chosen not to participate. Thank you for your time.", "warning")
            return render_template("done.html")

        return redirect(url_for("profile"))

    return render_template("consent.html", consent_questions=CONSENT_QUESTIONS,
                            privacy_note=CONSENT_PRIVACY_NOTE, consent_story=CONSENT_STORY)


# ============================================================
# PROFILE
# ============================================================
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "consent_answers" not in session:
        return redirect(url_for("consent"))

    if request.method == "POST":
        answers = {key: request.form.get(key) for key in PROFILE_QUESTIONS}
        if None in answers.values() or "" in answers.values():
            flash("Please answer all profile questions.", "warning")
            return render_template("profile.html", profile_questions=PROFILE_QUESTIONS, expert_note=PROFILE_EXPERT_NOTE)
        session["profile_answers"] = answers
        session["sme_class"] = map_to_official_sme_class(
            answers["P1_industry_sector"], answers["P2_company_size"]
        )
        return redirect(url_for("stage1"))

    return render_template("profile.html", profile_questions=PROFILE_QUESTIONS, expert_note=PROFILE_EXPERT_NOTE)


# ============================================================
# STAGE 1
# ============================================================
@app.route("/stage1", methods=["GET", "POST"])
def stage1():
    if "profile_answers" not in session:
        return redirect(url_for("profile"))

    if request.method == "POST":
        answers = {key: request.form.get(key) for key in STAGE1_QUESTIONS}
        if None in answers.values():
            flash("Please answer all 11 questions.", "warning")
            return render_template("stage1.html", questions=STAGE1_QUESTIONS, expert_note=STAGE_EXPERT_NOTE_EMPLOYMENT)
        session["stage1_answers"] = answers
        session["stage1_result"] = evaluate_stage1(answers)
        return redirect(url_for("stage1_result"))

    return render_template("stage1.html", questions=STAGE1_QUESTIONS, expert_note=STAGE_EXPERT_NOTE_EMPLOYMENT)


@app.route("/stage1_result")
def stage1_result():
    if "stage1_result" not in session:
        return redirect(url_for("stage1"))
    return render_template("stage1_result.html", result=session["stage1_result"])


# ============================================================
# STAGE 2 (+ Fuzzy Engine + LLM call happen on submit)
# ============================================================
@app.route("/stage2", methods=["GET", "POST"])
def stage2():
    if "stage1_result" not in session:
        return redirect(url_for("stage1"))

    if request.method == "POST":
        answers = {key: request.form.get(key) for key in STAGE2_QUESTIONS}
        if None in answers.values():
            flash("Please answer all 8 questions.", "warning")
            return render_template("stage2.html", questions=STAGE2_QUESTIONS, valid_options=VALID_STAGE2_OPTIONS, expert_note=STAGE_EXPERT_NOTE_ORGANISATION)

        session["stage2_answers"] = answers

        weights = get_default_weights()
        dim_scores, overall = evaluate_stage2(answers, weights)
        tier = score_to_tier(overall)
        flags = generate_diagnostic_flags(dim_scores, weights)

        session["weights"] = weights
        session["dim_scores"] = dim_scores
        session["overall_score"] = overall
        session["tier"] = tier
        session["flags"] = flags

        try:
            explanation = generate_llm_explanation(dim_scores, weights, tier, overall, flags)
            session["explanation"] = explanation
            session["llm_error"] = None
            faithfulness = check_llm_faithfulness(explanation, flags)
            session["faithfulness"] = faithfulness
        except Exception as e:
            session["explanation"] = None
            session["llm_error"] = str(e)
            session["faithfulness"] = None

        # Persist the full session record to the database at this point
        record = {
            "source": "self_assessment",
            "identity": session.get("identity"),
            "consent": session.get("consent_answers"),
            "profile": session.get("profile_answers"),
            "sme_class": session.get("sme_class"),
            "stage1_answers": session.get("stage1_answers"),
            "stage1_result": session.get("stage1_result"),
            "stage2_answers": answers,
            "fuzzy_scores": {"dimension_scores": dim_scores, "overall_score": overall, "tier": tier},
            "diagnostic_flags": flags,
            "llm_explanation": session.get("explanation"),
        }
        session["record_id"] = save_session_record(record)

        return redirect(url_for("results"))

    return render_template("stage2.html", questions=STAGE2_QUESTIONS, valid_options=VALID_STAGE2_OPTIONS, expert_note=STAGE_EXPERT_NOTE_ORGANISATION)


# ============================================================
# RESULTS
# ============================================================
@app.route("/results")
def results():
    if "overall_score" not in session:
        return redirect(url_for("stage2"))
    return render_template(
        "results.html",
        overall_score=session["overall_score"],
        tier=session["tier"],
        dim_scores=session["dim_scores"],
        weights=session["weights"],
        flags=session["flags"],
        dim_labels=DIM_ORDER,
        dim_values=[session["dim_scores"][d] for d in DIM_ORDER],
        explanation=session.get("explanation"),
        llm_error=session.get("llm_error"),
        faithfulness=session.get("faithfulness"),
        results_to_validation_note=RESULTS_TO_VALIDATION_NOTE,
    )


# ============================================================
# VALIDATION
# ============================================================
@app.route("/validation")
def validation_select():
    return render_template("validation_select.html")


@app.route("/validation/expert", methods=["GET", "POST"])
def validation_expert():
    if request.method == "POST":
        closed = {key: request.form.get(key) for key in EXPERT_VALIDATION_CLOSED_QUESTIONS}
        reasons = {key: request.form.get(f"{key}_reason", "").strip() for key in EXPERT_VALIDATION_CLOSED_QUESTIONS}

        # Server-side enforcement (mirrors the client-side JS, but cannot be
        # bypassed by disabling JS): any negative Likert answer must be
        # accompanied by a non-empty reason.
        missing_reason_labels = [
            EXPERT_VALIDATION_CLOSED_QUESTIONS[key]
            for key in EXPERT_VALIDATION_CLOSED_QUESTIONS
            if closed[key] in NEGATIVE_LIKERT_RESPONSES and not reasons[key]
        ]
        if missing_reason_labels:
            for label in missing_reason_labels:
                flash(f"Please explain your answer for: \"{label}\"", "warning")
            return render_template(
                "validation_expert.html",
                likert_questions=EXPERT_VALIDATION_CLOSED_QUESTIONS,
                likert_scale=LIKERT_SCALE,
                negative_likert_responses=list(NEGATIVE_LIKERT_RESPONSES),
                saaty_explanation=SAATY_SCALE_EXPLANATION,
                ahp_questions=EXPERT_AHP_QUESTIONS,
                intensity_options=SAATY_INTENSITY_OPTIONS,
                dimension_structure_question=list(EXPERT_DIMENSION_STRUCTURE_QUESTION.values())[0],
                dimension_structure_options=EXPERT_DIMENSION_STRUCTURE_OPTIONS,
                open_questions=EXPERT_VALIDATION_OPEN_QUESTIONS,
            )

        ahp = {}
        for key in EXPERT_AHP_QUESTIONS:
            ahp[key] = {
                "direction": request.form.get(f"{key}_direction"),
                "intensity": request.form.get(f"{key}_intensity"),
            }
        dim_structure = request.form.get("dim_structure")
        open_answers = {key: request.form.get(key) for key in EXPERT_VALIDATION_OPEN_QUESTIONS}

        record = {
            "source": "expert_validation",
            "identity": session.get("identity"),
            "closed_answers": closed,
            "closed_answer_reasons": reasons,
            "ahp_pairwise": ahp,
            "dimension_structure_choice": dim_structure,
            "open_answers": open_answers,
            "linked_assessment_record_id": session.get("record_id"),
        }
        save_session_record(record)
        flash("Thank you for your expert feedback!", "success")
        return redirect(url_for("done"))

    return render_template(
        "validation_expert.html",
        likert_questions=EXPERT_VALIDATION_CLOSED_QUESTIONS,
        likert_scale=LIKERT_SCALE,
        negative_likert_responses=list(NEGATIVE_LIKERT_RESPONSES),
        saaty_explanation=SAATY_SCALE_EXPLANATION,
        ahp_questions=EXPERT_AHP_QUESTIONS,
        intensity_options=SAATY_INTENSITY_OPTIONS,
        dimension_structure_question=list(EXPERT_DIMENSION_STRUCTURE_QUESTION.values())[0],
        dimension_structure_options=EXPERT_DIMENSION_STRUCTURE_OPTIONS,
        open_questions=EXPERT_VALIDATION_OPEN_QUESTIONS,
    )


@app.route("/validation/sme", methods=["GET", "POST"])
def validation_sme():
    if request.method == "POST":
        closed = {key: request.form.get(key) for key in SME_VALIDATION_CLOSED_QUESTIONS}
        open_answers = {key: request.form.get(key) for key in SME_VALIDATION_OPEN_QUESTIONS}

        record = {
            "source": "sme_user_testing",
            "identity": session.get("identity"),
            "closed_answers": closed,
            "open_answers": open_answers,
            "linked_assessment_record_id": session.get("record_id"),
        }
        save_session_record(record)
        flash("Thank you for your feedback!", "success")
        return redirect(url_for("done"))

    return render_template(
        "validation_sme.html",
        likert_questions=SME_VALIDATION_CLOSED_QUESTIONS,
        likert_scale=LIKERT_SCALE,
        open_questions=SME_VALIDATION_OPEN_QUESTIONS,
    )


@app.route("/done")
def done():
    session.clear()
    return render_template("done.html")


# ============================================================
# ADMIN — password-protected viewer for all collected records
# ============================================================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    """
    Simple password-protected viewer for all collected records.

    Protected by a single shared password (ADMIN_PASSWORD env var) rather
    than individual user accounts, since only the researcher needs access.
    This is a minimal-effort protection appropriate for a research
    prototype — not a substitute for proper authentication in a
    production system handling sensitive data at scale.
    """
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        return "ADMIN_PASSWORD environment variable not set. Refusing to show this page.", 500

    if not session.get("admin_authed"):
        if request.method == "POST":
            if request.form.get("password") == admin_password:
                session["admin_authed"] = True
            else:
                flash("Incorrect password.", "error")
                return render_template("admin_login.html")
        else:
            return render_template("admin_login.html")

    keys = kv_list_keys("session:")
    records = []
    for k in keys:
        rec = kv_get(k)
        if rec:
            records.append(rec)
    records.sort(key=lambda r: r.get("saved_at", ""), reverse=True)

    return render_template("admin.html", records=records, records_json=json.dumps(records, indent=2, default=str))


@app.route("/admin/delete/<session_id>", methods=["POST"])
def admin_delete(session_id):
    """
    Deletes a single record from the database. Requires an authenticated
    admin session (same protection as the /admin viewer page) — this route
    cannot be reached without first logging in via /admin.
    """
    if not session.get("admin_authed"):
        return redirect(url_for("admin"))

    kv_delete(f"session:{session_id}")
    flash("Record deleted.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    if is_using_local_fallback():
        print("\u26A0\uFE0F  KV_REST_API_URL / KV_REST_API_TOKEN not set — using in-memory "
              "storage for local testing. Data will NOT persist after this process ends.\n")
    app.run(debug=True, port=5000)
