# Provenance Guard

Provenance Guard is a Flask API that analyzes text submissions and assesses whether they are likely human-written or AI-generated. It combines two independent detection signals, an LLM-based semantic evaluator using Groq/Llama-3.3 and a stylometric analyzer, into a single weighted confidence score. Each submission receives a transparency label explaining the result, and creators who believe their work was misclassified can file an appeal. Every submission and appeal is recorded to an audit log.

## Architecture Overview

### Submission Flow
```
[User] --(text, creator_id)--> [POST /submit]
                                       |
                    +------------------+------------------+
                    |                                     |
          [Signal 1: LLM]                    [Signal 2: Stylometrics]
          get_llm_signal()                  get_stylometric_signal()
          (semantic score)                   (stylometric score)
                    |                                     |
                    +------------------+------------------+
                                       |
                              [Confidence Scoring]
                           calculate_confidence()
                          (0.7 × LLM + 0.3 × Style)
                                       |
                           [Transparency Label Gen]
                           get_transparency_label()
                                       |
                             [Audit Log Writer]
                              log_to_audit()
                                       |
                              (JSON Response)
                                       |
[User] <-------------------------------+
```

### Appeal Flow
```
[User] --(content_id, appeal_reason)--> [POST /appeal]
                                               |
                                   [Validate content_id exists]
                                         get_log()
                                               |
                                     [Audit Log Writer]
                                       log_to_audit()
                                  (status: 'under_review')
                                               |
                                    (Confirmation Response)
                                               |
[User] <---------------------------------------+
```

## Detection Signals

### Signal One: LLM-Based Semantic Evaluation (Groq/Llama-3.3)
* **What it measures:** This signal uses the `llama-3.3-70b-versatile` model to judge whether a piece of writing sounds like it was written by AI. Instead of making a simple yes/no decision, it assigns a confidence score based on two groups of writing patterns.
    * **Obvious indicators:**
        * **Structural Homogeneity:** Repetitive organization and common transition phrases like "Furthermore" or "In conclusion."
        * **Tone Mimicry:** Formulaic expressions often produced by AI, such as "But here's the thing..." or "The result?"
        * **Buzzword Saturation:** Overuse of words like delve, pivotal, unlock, and empower when they aren't necessary.
    * **Subtle indicators (added after testing):** During testing, borderline samples — such as structured formal writing and conversational-sounding AI text — were initially under-scored because the prompt only caught obvious AI tells. The prompt was expanded to also detect:
        * **Balanced Neutrality:** Carefully presenting both sides of an argument without expressing a clear opinion.
        * **Artificial Personal Voice:** Phrases like "I've been thinking about..." that imitate a personal voice without feeling genuine.
        * **Impersonal Precision:** Writing that is polished and factual but lacks personal experiences, uncertainty, or lived details.
        * **Even Paragraph Cadence:** Paragraphs that are all similarly structured, with each covering one clean idea and little natural variation.
* **Output Format:** A confidence score from 0.0 (likely human-written) to 1.0 (likely AI-written).
* **Blind Spots:** This signal is less accurate when a person heavily edits AI-generated text by adding their own experiences, personality, or writing style, making the text sound more naturally human.

### Signal Two: Stylometric Heuristics
* **What it measures:** This signal analyzes quantifiable characteristics of the writing style that often differ between human and AI-generated text, including:
    * **Sentence Length Variance:** Measures the variation in sentence lengths ("burstiness"), which tends to be higher in human writing.
    * **Type-Token Ratio (TTR):** Estimates vocabulary diversity by comparing unique words to total words.
    * **Punctuation Density:** Measures the frequency of expressive punctuation such as semicolons, parentheses, and exclamation marks.
* **Output Format:** A normalized score between 0.0 (Likely Human) and 1.0 (Likely AI).
* **Blind Spots:** Stylometric features become less informative for very short texts due to limited statistical evidence. Additionally, highly formal or academic writing often exhibits characteristics similar to AI-generated text, increasing the likelihood of false positives.

## Confidence Scoring

### Combination Formula
The two signals are combined using a weighted arithmetic mean:

```
Final Score = (0.7 × LLM Semantic Score) + (0.3 × Stylometric Score)
```

The LLM signal receives 70% of the weight because it captures higher-level characteristics — tone, rhetorical structure, and vocabulary patterns — that are more directly informative than statistical writing features alone. The stylometric signal acts as an independent structural check: it cannot be fooled by prompt engineering and helps moderate the final score when the LLM is uncertain or overconfident.

### Threshold Mapping
| Score Range | Label |
|---|---|
| 0.00 – 0.35 | Likely Human-written |
| 0.36 – 0.72 | Uncertain |
| 0.73 – 1.00 | Likely AI-generated |

> **Note:** The `likely_ai` threshold was raised from 0.66 (original spec) to 0.72 during testing. Borderline samples — structured, formal writing that lacks obvious AI buzzwords — were landing in `likely_ai` when the LLM scored them near 0.70. Because the LLM has natural run-to-run variance of ±0.10–0.15 on ambiguous inputs, a threshold of 0.66 was too close to the edge. Raising it to 0.72 ensures that only texts where both signals consistently agree reach the `likely_ai` classification, which aligns with the system's conservative design goal of minimizing false positives.

### Validation
Confidence scores were validated by running `test_signal.py` across four representative samples — clearly AI-generated, clearly human, formal/academic, and hybrid — and checking that:
- Scores spread meaningfully across the 0–1 range rather than clustering
- The two signals agreed on clear-cut cases and disagreed on genuinely ambiguous ones
- All three label variants (`likely_ai`, `uncertain`, `likely_human`) were reachable

### Example Submissions

**High-confidence AI detection (combined: 0.7441 → `likely_ai`)**
> "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment."

| Signal | Score |
|---|---|
| LLM Semantic | 0.80 |
| Stylometric | 0.61 |
| **Combined** | **0.7441** |

Both signals lean AI. The LLM catches "Furthermore," "paradigm shift," and "stakeholders" as buzzword-heavy AI phrasing. Stylometrics confirms low sentence variance and limited expressive punctuation.

---

**Lower-confidence, uncertain result (combined: 0.4624 → `uncertain`)**
> "I've been thinking a lot about remote work lately. There are genuine tradeoffs — flexibility and no commute on one side, isolation and blurred work-life boundaries on the other. Studies show productivity varies widely by individual and role type."

| Signal | Score |
|---|---|
| LLM Semantic | 0.40 |
| Stylometric | 0.61 |
| **Combined** | **0.4624** |

The signals diverge here. The LLM reads the conversational opener as human-leaning, while stylometrics flags the balanced, even structure as mildly AI-like. The combined score correctly lands in `uncertain` — neither signal is confident enough to make a definitive call.

## Transparency Label
The transparency label is designed to communicate the system's confidence rather than provide a definitive judgment. Each message is mapped to a confidence range so that the explanation reflects the level of certainty behind the classification.

### 1. Likely AI-generated (Score: 0.73–1.00)
Label: **Likely AI-generated**
> Our analysis detected multiple writing patterns commonly associated with AI-generated text, including consistent structural organization and AI-typical language. Based on these signals, the system has a high level of confidence in this assessment. This result represents a probability, not definitive proof.

### 2. Likely Human-written (Score: 0.00–0.35)
Label: **Likely Human-written**
> Our analysis found writing characteristics commonly associated with human authors, such as greater stylistic variation and vocabulary diversity. The system found little evidence suggesting AI-generated text, resulting in a high-confidence human classification.

### 3. Uncertain (Score: 0.36–0.72)
Label: **Uncertain**
> The available evidence is mixed, and the system cannot confidently determine whether the content is human- or AI-generated. Some detected patterns are associated with AI-generated writing, while others are consistent with human writing. If you believe this classification is incorrect, you may submit an appeal for manual review.

## Rate Limiting

Rate limiting is applied to `POST /submit` using Flask-Limiter with in-memory storage:

```
10 per minute — 100 per day
```

**10 per minute:** A writer actively checking multiple drafts in a session can comfortably stay under this — it allows one submission every 6 seconds, which is faster than most people can meaningfully revise and re-submit. Any automated script flooding the endpoint would hit this ceiling almost immediately.

**100 per day:** Generous enough for an individual user (more than 3 submissions per hour across an 8-hour day), but low enough that a single IP sustaining abuse at scale is effectively throttled. The per-minute limit is the primary abuse guard; the daily limit exists as a backstop for persistent low-and-slow requests that stay under the per-minute cap.

The endpoint returns HTTP `429 Too Many Requests` when either limit is exceeded. Verified by running a 12-request loop — the first 10 returned `200`, requests 11 and 12 returned `429`:

```
200
200
200
200
200
200
200
200
200
200
429
429
```

## Known Limitations

**1. Legal, scientific, and technical writing will score as AI-generated even when human-written.**
This is the system's most predictable weakness because of how both signals work. The LLM signal looks for features like precise wording, consistent sentence structure, and an objective tone, but those are also the normal style of scientific and technical writing. The stylometric signal has the same problem. Academic writing usually has similar sentence lengths and very little expressive punctuation, which also pushes the score toward AI. As a result, a paper written entirely by a human could still be labeled `likely_ai`. The system cannot tell the difference between writing that sounds like AI and writing from a genre that naturally uses the same style.

**2. AI text that mimics casual human writing will score as human-written.**
If an AI is asked to write like a casual person with slang, lowercase text, run-on sentences, or fewer transitions, both signals become much less reliable. The LLM signal is looking for the structured patterns that AI writing usually has, so it may not recognize this style. The stylometric signal also sees the uneven sentence lengths and informal writing as more human. This is a basic limitation of the system: it detects the writing style AI usually produces, not every style AI is capable of producing.

**3. The stylometric signal is unreliable on short texts.**
The stylometric score is based on sentence length, vocabulary variety, and punctuation, but those measurements only become reliable with enough text. In a very short passage, one unusual sentence can have a large effect, and vocabulary variety is naturally higher because there are fewer words overall. To avoid making unreliable judgments, the system gives each stylometric feature a neutral score of 0.5 when there is not enough text to measure it properly. This means short submissions depend mostly on the LLM signal instead of the stylometric signal.

## Spec Reflection

**One way the spec helped you during implementation:** Defining the transparency labels and score thresholds before writing any code made the label generation function much easier to implement. The label names, score ranges, and weighted formula `(0.7 × LLM + 0.3 × Stylometric)` were already decided, so implementation could simply follow the plan instead of having to decide while implementing.

**One way your implementation diverged from the spec, and why:**
The `likely_ai` threshold was raised from 0.66 (spec) to 0.72 (implementation) after testing revealed that borderline formal writing was landing in `likely_ai` on some runs but `uncertain` on others, due to natural LLM score variance of ±0.10–0.15 on ambiguous inputs. A threshold of 0.66 was too close to where the LLM scores for borderline texts cluster, meaning classification depended partly on which run you happened to get. Raising it to 0.72 made the `likely_ai` label more consistent and harder to reach by accident — which better reflects the spec's stated design goal of minimizing false positives, even if the specific number changed.

## AI Usage

**Instance 1**
- *What I gave the AI:* The architecture diagram and the Detection Signals section from planning.md describing the `POST /submit` endpoint for Milestone 3.
- *What it produced:* A Flask app skeleton with the `POST /submit` route, `get_llm_signal()`, and `log_to_audit()` implemented and wired together.
- *What I changed or overrode:* The initial JSON response used the wrong key names — the formatted output didn't match my API contract. For example, the attribution field came back as `label` and the confidence field used inconsistent naming. I corrected the response keys to match the spec (`attribution`, `confidence`, `label`).

**Instance 2**
- *What I gave the AI:* The Transparency Label Design section from planning.md, which included the three label variants and their exact message text.
- *What it produced:* A `get_transparency_label()` function with the correct score ranges and three return branches, but it wrote its own label text rather than using the exact wording I had written in the spec.
- *What I changed or overrode:* I replaced the generated label text with the exact messages from my planning.md, word for word. The logic and structure were correct.