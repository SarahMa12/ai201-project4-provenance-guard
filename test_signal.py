from app import get_llm_signal, get_stylometric_signal, calculate_confidence

samples = [
    ("Clearly AI",      "Artificial intelligence represents a transformative paradigm shift in modern society.  It is important to note that while the benefits of AI are numerous, it is equally  essential to consider the ethical implications. Furthermore, stakeholders across  various sectors must collaborate to ensure responsible deployment."),
    ("Clearly Human",   "ok so i finally tried that new ramen place downtown and honestly?  underwhelming. the broth was fine but they put WAY too much sodium in it and  i was thirsty for like three hours after. my friend got the spicy version and  said it was better. probably won't go back unless someone drags me there"),
    ("Borderline",      "The relationship between monetary policy and asset price inflation has been  extensively studied in the literature. Central banks face a fundamental tension  between their mandate for price stability and the unintended consequences of  prolonged low interest rates on equity and real estate valuations."),
    ("Borderline",      "I've been thinking a lot about remote work lately. There are genuine tradeoffs —  flexibility and no commute on one side, isolation and blurred work-life boundaries  on the other. Studies show productivity varies widely by individual and role type."),
]

print(f"{'Sample':<20} {'LLM':>6} {'Style':>6} {'Combined':>10}  Agreement")
print("-" * 60)

for label, text in samples:
    llm   = get_llm_signal(text)
    style = get_stylometric_signal(text)
    combined = calculate_confidence(llm, style)

    # signals agree if both are on the same side of 0.5
    agree = "agree" if (llm > 0.5) == (style > 0.5) else "DISAGREE"

    print(f"{label:<20} {llm:>6.2f} {style:>6.2f} {combined:>10.4f}  {agree}")
    print(f"  text: {text[:75]}...")
    print()
