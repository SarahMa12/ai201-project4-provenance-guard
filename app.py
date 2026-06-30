import os
import re
import math
import json
import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

AUDIT_LOG_PATH = "audit_log.jsonl"

_LLM_SYSTEM_PROMPT = """You are a writing analysis expert. Evaluate whether the text provided was likely written by an AI language model or a human.

Assess it for these AI-writing indicators:

Obvious indicators:
- Structural Homogeneity: repetitive organizational patterns, generic transitions (e.g., "Furthermore,", "In conclusion,")
- Tone Mimicry: formulaic rhetorical templates (e.g., "But here's the thing...", "The result?")
- Buzzword Saturation: heavy use of AI-associated vocabulary (e.g., delve, pivotal, unlock, empower, seamlessly) without contextual necessity

Subtle indicators:
- Balanced neutrality: methodically presenting "on one hand / on the other hand" without a clear personal stance or conviction
- Artificial personal voice: conversational openers ("I've been thinking about...", "Let's explore...") that feel like a performance of human writing rather than genuine expression
- Impersonal precision: formal or academic writing with no personal hedging, anecdotes, or specific lived details — reads like a summary rather than experience
- Even paragraph cadence: each paragraph cleanly covers exactly one point with no tangents, interruptions, or unresolved thoughts

Respond with a single JSON object and nothing else:
{"score": <float between 0.0 and 1.0>}

0.0 = very likely human-written, 1.0 = very likely AI-generated."""


def get_llm_signal(text: str) -> float:
    """Query Groq/Llama-3.3 to score AI writing patterns. Returns a float in [0.0, 1.0]."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    score = float(result["score"])
    return max(0.0, min(1.0, score))


def get_stylometric_signal(text: str) -> float:
    """Compute stylometric AI-likelihood from sentence variance, TTR, and punctuation density."""

    # Sentence Length Variance — higher burstiness = more human = lower AI score
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if len(sentences) >= 2:
        lengths = [len(s.split()) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        std_len = math.sqrt(sum((l - mean_len) ** 2 for l in lengths) / len(lengths))
        cv = std_len / mean_len if mean_len > 0 else 0.0
        variance_score = 1.0 / (1.0 + cv)
    else:
        variance_score = 0.5

    # Type-Token Ratio — higher vocabulary diversity = more human = lower AI score
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) >= 5:
        ttr = len(set(words)) / len(words)
        ttr_score = 1.0 - ttr
    else:
        ttr_score = 0.5

    # Punctuation Density — more expressive punctuation = more human = lower AI score
    expressive_count = sum(text.count(c) for c in ';()!')
    density = expressive_count / max(1, len(text))
    punct_score = max(0.0, 1.0 - min(density * 30, 1.0))

    stylometric_score = (variance_score + ttr_score + punct_score) / 3.0
    return round(max(0.0, min(1.0, stylometric_score)), 4)


def calculate_confidence(llm_score: float, stylometric_score: float) -> float:
    """Combine signals: 70% semantic (LLM) + 30% stylometric."""
    return round((0.7 * llm_score) + (0.3 * stylometric_score), 4)


def get_transparency_label(score: float) -> tuple[str, str]:
    """Map a confidence score to an attribution result and transparency label."""
    if score <= 0.35:
        return (
            "likely_human",
            "Our analysis found writing characteristics commonly associated with human authors, such as greater stylistic variation and vocabulary diversity. The system found little evidence suggesting AI-generated text, resulting in a high-confidence human classification.",
        )
    elif score <= 0.72:
        return (
            "uncertain",
            "The available evidence is mixed, and the system cannot confidently determine whether the content is human- or AI-generated. Some detected patterns are associated with AI-generated writing, while others are consistent with human writing. If you believe this classification is incorrect, you may submit an appeal for manual review.",
        )
    else:
        return (
            "likely_ai",
            "Our analysis detected multiple writing patterns commonly associated with AI-generated text, including consistent structural organization and AI-typical language. Based on these signals, the system has a high level of confidence in this assessment. This result represents a probability, not definitive proof.",
        )


def log_to_audit(entry: dict) -> None:
    """Append a single JSON record to audit_log.jsonl."""
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_log() -> list[dict]:
    """Read all entries from audit_log.jsonl and return as a list."""
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()}), 200


@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json(silent=True)
    if not data or "content_id" not in data or "appeal_reason" not in data:
        return jsonify({"error": "Request body must include 'content_id' and 'appeal_reason'."}), 400

    content_id = data["content_id"]
    appeal_reason = data["appeal_reason"].strip()

    if not appeal_reason:
        return jsonify({"error": "'appeal_reason' must not be empty."}), 400

    # verify the content_id exists in the audit log
    entries = get_log()
    known_ids = {e["content_id"] for e in entries}
    if content_id not in known_ids:
        return jsonify({"error": f"content_id '{content_id}' not found."}), 404

    log_to_audit({
        "content_id": content_id,
        "appeal_reason": appeal_reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "under_review",
    })

    return jsonify({
        "message": "Your appeal has been received. This submission has been placed in the manual review queue.",
        "content_id": content_id,
        "status": "under_review",
    }), 200


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute; 100 per day")
def submit():
    data = request.get_json(silent=True)
    if not data or "text" not in data or "creator_id" not in data:
        return jsonify({"error": "Request body must include 'text' and 'creator_id'."}), 400

    text = data["text"].strip()
    creator_id = data["creator_id"]

    if not text:
        return jsonify({"error": "'text' must not be empty."}), 400

    content_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    llm_score = get_llm_signal(text)
    stylometric_score = get_stylometric_signal(text)
    confidence_score = calculate_confidence(llm_score, stylometric_score)

    attribution_result, transparency_label = get_transparency_label(confidence_score)

    log_to_audit({
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "llm_score": llm_score,
        "stylometric_score": stylometric_score,
        "confidence_score": confidence_score,
        "attribution": attribution_result,
        "status": "classified",
    })

    return jsonify({
        "content_id": content_id,
        "attribution": attribution_result,
        "confidence": confidence_score,
        "label": transparency_label,
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
