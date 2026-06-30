import os
import json
import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

AUDIT_LOG_PATH = "audit_log.jsonl"

_LLM_SYSTEM_PROMPT = """You are a writing analysis expert. Evaluate whether the text provided was likely written by an AI language model or a human.

Assess it for these AI-writing indicators:
- Structural Homogeneity: repetitive organizational patterns, generic transitions (e.g., "Furthermore,", "In conclusion,")
- Tone Mimicry: formulaic rhetorical templates (e.g., "But here's the thing...", "The result?")
- Punctuation Infatuation: overuse of em dashes (—) or other punctuation for artificial emphasis
- Buzzword Saturation: heavy use of AI-associated vocabulary (e.g., delve, pivotal, unlock, empower, seamlessly) without strong contextual necessity

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


def get_transparency_label(score: float) -> tuple[str, str]:
    """Map a confidence score to an attribution result and transparency label."""
    if score <= 0.35:
        return (
            "likely_human",
            "Our analysis found writing characteristics commonly associated with human authors, such as greater stylistic variation and vocabulary diversity. The system found little evidence suggesting AI-generated text, resulting in a high-confidence human classification.",
        )
    elif score <= 0.65:
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


@app.route("/submit", methods=["POST"])
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

    # TODO (Milestone 4): replace with calculate_confidence(llm_score, get_stylometric_signal(text))
    confidence_score = round(llm_score, 4)

    attribution_result, transparency_label = get_transparency_label(confidence_score)

    log_to_audit({
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": attribution_result,
        "confidence": confidence_score,
        "llm_score": llm_score,
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
