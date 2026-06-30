# Provenance Guard — planning.md

## Detection Signals

My system combines two independent detection signals to provide a more robust assessment of whether a piece of text is human- or AI-generated. By evaluating both semantic writing patterns and measurable stylometric features, the system is less susceptible to adversarial techniques that can bypass any single detection method.

### 1. Signal One: LLM-Based Semantic Evaluation (Groq/Llama-3.3)
* **What it measures:** This signal uses the `llama-3.3-70b-versatile` model as an evaluator that assesses writing for stylistic characteristics commonly associated with AI-generated text. Rather than making a simple binary decision, it estimates how strongly the writing exhibits AI-like patterns, including:
    * **Structural Homogeneity:** Repetitive organizational patterns and generic transition phrases (e.g., "Furthermore," "In conclusion").
    * **Tone Mimicry:** Formulaic rhetorical templates often produced by language models, such as "But here's the thing..." or "The result?".
    * **Punctuation Infatuation:** Overuse of em dashes (—) and other punctuation used to create artificial emphasis.
    * **Buzzword Saturation:** Frequent use of generic AI-associated vocabulary (e.g., delve, pivotal, unlock, and empower) without strong contextual necessity.
* **Output Format:** A continuous confidence score (`float`) between 0.0 (Likely Human) and 1.0 (Likely AI).
* **Blind Spots:** This signal is less reliable for hybrid writing, where humans substantially edit AI-generated text by adding personal experiences, informal tangents, or unique stylistic elements that disrupt typical AI writing patterns.

### 2. Signal Two: Stylometric Heuristics (Pure Python)
* **What it measures:** This signal analyzes quantifiable characteristics of the writing style that often differ between human and AI-generated text, including:
    * **Sentence Length Variance:** Measures the variation in sentence lengths ("burstiness"), which tends to be higher in human writing.
    * **Type-Token Ratio (TTR):** Estimates vocabulary diversity by comparing unique words to total words.
    * **Punctuation Density:** Measures the frequency of expressive punctuation such as semicolons, parentheses, and exclamation marks.
* **Output Format:** A normalized score between 0.0 (Likely Human) and 1.0 (Likely AI).
* **Blind Spots:** Stylometric features become less informative for very short texts due to limited statistical evidence. Additionally, highly formal or academic writing often exhibits characteristics similar to AI-generated text, increasing the likelihood of false positive

---

### Confidence Scoring Logic

The final confidence score is computed using a weighted arithmetic mean:

**The Combination Formula:**
Final Score = (0.7 × Semantic Score) + (0.3 × Stylometric Score)

The semantic evaluation receives a higher weight because it captures higher-level characteristics such as tone, structure, and rhetorical style that are generally more informative than purely statistical writing features.

## Uncertainty Representation

**What a confidence score of 0.6 means:**
A confidence score of 0.60 indicates that the system detected noticeable characteristics associated with AI-generated writing, but not enough evidence to confidently classify the text as machine-generated. Rather than making a definitive judgment, the system labels this range as *Uncertain*, acknowledging that these patterns can also appear in legitimate human writing, particularly in formal or academic contexts. This conservative approach reduces the likelihood of falsely attributing human-written work to AI.

**Mapping raw signals to a calibrated score:**
The final confidence score is computed using a weighted arithmetic mean of the two detection signals:

Final Score = (0.7 × Semantic Score) + (0.3 × Stylometric Score)

Both signals produce normalized values between 0.0 and 1.0, ensuring the combined score remains on the same scale.

* **70% Semantic Evaluation (LLM)**: Receives the larger weight because it captures higher-level characteristics such as tone, organization, and rhetorical style that are difficult to measure with simple statistics.
* **30% Stylometric Heuristics**: Acts as an independent structural signal by measuring sentence-length variation, vocabulary diversity, and punctuation usage. This complementary signal helps moderate the final score when the semantic evaluator is uncertain or overly confident.
Combining these independent signals produces a more balanced assessment than relying on either method alone.

**Thresholds and Mapping:**
The continuous confidence score is mapped to three user-facing categories:
* **0.00 – 0.35:** Likely Human-written.
The writing exhibits characteristics commonly associated with human authors, such as greater stylistic variation and vocabulary diversity.

* **0.36 – 0.65:** Uncertain.
The available evidence is mixed or inconclusive. This range acknowledges that both human and AI-generated writing can share similar stylistic features and avoids making overly confident classifications.

* **0.66 – 1.00:** Likely AI-generated.
Multiple indicators consistently suggest AI-generated writing, resulting in a higher-confidence classification.

The intentionally broad Uncertain range (0.36–0.65) reflects a conservative detection strategy. Rather than maximizing the number of AI detections, the system prioritizes minimizing false positives, since incorrectly labeling human-written work as AI-generated can undermine user trust more than failing to identify some AI-generated text. This trade-off favors precision over recall for the Likely AI-generated classification while providing users with transparent, confidence-based feedback instead of definitive claims.

## Transparency Label Design

The transparency label is designed to communicate the system's confidence rather than provide a definitive judgment. Each message is mapped to a confidence range so that the explanation reflects the level of certainty behind the classification.

### 1. Likely AI-generated (Score: 0.66–1.00)
Label: **Likely AI-generated**
> Our analysis detected multiple writing patterns commonly associated with AI-generated text, including consistent structural organization and AI-typical language. Based on these signals, the system has a high level of confidence in this assessment. This result represents a probability, not definitive proof.

### 2. Likely Human-written (Score: 0.00–0.35)
Label: **Likely Human-written**
> Our analysis found writing characteristics commonly associated with human authors, such as greater stylistic variation and vocabulary diversity. The system found little evidence suggesting AI-generated text, resulting in a high-confidence human classification.

### 3. Uncertain (Score: 0.36–0.65)
Label: **Uncertain**
> The available evidence is mixed, and the system cannot confidently determine whether the content is human- or AI-generated. Some detected patterns are associated with AI-generated writing, while others are consistent with human writing. If you believe this classification is incorrect, you may submit an appeal for manual review.

## Appeals Workflow

### Eligibility
Any creator whose content has been processed and assigned a classified status may submit an appeal. The appeals process is intended primarily for users who believe their work has been incorrectly classified, particularly in cases where human-written content has been flagged as AI-generated.

### Appeal Submission
To submit an appeal, the creator must provide:
* Content ID: The unique identifier assigned to the original submission.
* Appeal Reason: A required text field explaining why the creator believes the classification is inaccurate.

### System Workflow
When an appeal is submitted, the system performs the following actions:

1. **Update Status**: The submission status is changed from `classified` to `under_review`, indicating that it is awaiting human evaluation.
2. **Create an Audit Log Entry**: A new record is appended to `audit_log.jsonl` containing the content ID, the creator's appeal reason, a timestamp, and the updated status. This preserves a complete audit trail linking the appeal to the original classification.
3. **Confirmation**: The system confirms that the appeal has been successfully received and informs the creator that the submission has been placed in the manual review queue.

### Human Review Interface
A human reviewer evaluating an appeal is presented with all relevant information needed to make an informed decision, including:
* **Original Submission**: The complete text submitted by the creator.
* **Original Classification**: The predicted label and overall confidence score.
* **Signals Breakdown**: Detection Signal Breakdown: The individual semantic (LLM) and stylometric scores that contributed to the final confidence score.
* **Appeal Details**: The creator's explanation for why they believe the classification is incorrect.
* **Status Flag**: An `under_review` status indicator to distinguish pending appeals from finalized decisions.

Providing reviewers with both the system's reasoning and the creator's explanation promotes transparency, accountability, and more informed human oversight.

## Anticipated Edge Cases
Although combining semantic and stylometric signals improves robustness, the system still has several known limitations where misclassification is more likely.

**1. AI Writing That Intentionally Mimics Human Style**
The system may incorrectly classify AI-generated text as human-written when the model is explicitly prompted to imitate natural human imperfections. For example, prompting an LLM to write like "a distracted teenager with run-on sentences, slang, and inconsistent grammar" can produce writing with the stylistic variation and irregular sentence patterns that the stylometric heuristics associate with human authors. In these cases, the structural evidence may outweigh the semantic signal, increasing the likelihood of a false negative (AI content classified as human).

**2. Highly Technical or Formulaic Human Writing**
The system may incorrectly classify human-written technical, legal, or scientific documents as AI-generated. Writers in these domains intentionally use standardized sentence structures, precise terminology, and objective language to maximize clarity and consistency. These characteristics resemble the structural regularity often found in AI-generated text, which can increase the likelihood of a false positive (human content classified as AI).

**3. Very Short or Minimalist Writing:**
Short-form content, such as haikus, aphorisms, or brief social media posts, may receive an Uncertain classification. Stylometric features such as sentence-length variance and vocabulary diversity require a sufficient amount of text to produce meaningful measurements. When limited evidence is available, the system intentionally favors an Uncertain result rather than making an overconfident classification.

---
### Design Trade-off
These edge cases illustrate an inherent limitation of AI authorship detection: no single set of linguistic features can reliably distinguish human and AI writing in every situation. To reduce the impact of these limitations, the system adopts a conservative decision strategy, reserving high-confidence classifications for cases where both semantic and stylometric signals consistently support the same conclusion.

## Architecture

```
========================================================================
1. SUBMISSION FLOW
========================================================================
[User] --(text, creator_id)--> [POST /submit]
                                    |
            +-----------------------+-----------------------+
            |                                               |
      [Signal 1: LLM] --(LLM score)--> [Confidence Scoring] |
                                               |            |
      [Signal 2: Stylometrics] --(Style score)-+            |
                                               |            |
                                    [Transparency Label Gen]
                                               |            |
                                       [Audit Log Writer]   |
                                               |            |
                                     (label, score, status) |
                                               |            |
[User] <-----------(JSON Response)-------------+------------+


========================================================================
2. APPEAL FLOW
========================================================================
[User] --(content_id, reasoning)--> [POST /appeal]
                                           |
                                 [Status Update Logic]
                                           |
                                   [Audit Log Writer]
                                           |
                                (log appeal, set 'under_review')
                                           |
[User] <----------(Confirmation Msg)-------+
```

## AI Tool Plan
**Milestone 3 — Submission Endpoint + First Signal**
* **AI Tool:** Claude Code
* **Input Provided:** I will provide the Architecture diagram, the API contract, and the Detection Signals section describing the LLM-based semantic evaluation.
* **Expected Output:** Claude Code should generate a Flask application skeleton containing the `POST /submit` endpoint, a `log_to_audit()` helper function, and a `get_llm_signal()` function that queries the Groq API and returns a normalized confidence score.
* **Verification Method:** I will run the Flask application locally and submit sample text using a curl request. I will verify that a unique content_id is generated, the response matches the API contract, and a corresponding entry is successfully written to audit_log.jsonl.

**Milestone 4: Second Signal + Confidence Scoring**
* **AI Tool:** Claude Code
* **Input Provided:** I will provide the Detection Signals section describing the Stylometric Heuristics along with the Confidence Scoring Logic section containing the weighted arithmetic mean formula.
* **Expected Output:** Claude Code should implement a `get_stylometric_signal()` function that computes sentence length variance, type-token ratio (TTR), and punctuation density, followed by a `calculate_confidence()` function that combines the semantic and stylometric signals into a single confidence score.
* **Verification Method:** I will evaluate the system using four representative writing samples: clearly AI-generated text, clearly human-written text, a human-edited AI sample, and a formal academic passage. I will verify that the confidence scores vary meaningfully across the 0–1 range and map to my defined attribution thresholds.

**Milestone 5 — Production Layer**
* **AI Tool:** Claude Code
* **Input Provided:** I will provide the Transparency Label Design, the Appeals Workflow, and the Flask-Limiter configuration requirements.
* **Expected Output:** Claude Code should implement a `get_transparency_label()` function that maps confidence scores to the three transparency label variants, a `POST /appeal` endpoint that updates a submission's status to `under_review`, and Flask-Limiter protection for the `POST /submit` endpoint.
* **Verification Method:** I will manually submit content that triggers each transparency label category and verify that the returned messages match my specification. I will then execute a shell loop (`seq 1 12`) to exceed the configured rate limit and confirm that the API returns HTTP 429 status codes. Finally, I will submit an appeal for an existing `content_id` and verify that its status is updated to `under_review` and that the change is recorded in the audit log.
