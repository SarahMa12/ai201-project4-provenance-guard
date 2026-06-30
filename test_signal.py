from app import get_llm_signal, get_stylometric_signal, calculate_confidence, get_transparency_label

# one sample per expected label range — tests all three variants are reachable
samples = [
    ("Clearly AI",      "likely_ai",    "Artificial intelligence represents a transformative paradigm shift in modern society.  It is important to note that while the benefits of AI are numerous, it is equally  essential to consider the ethical implications. Furthermore, stakeholders across  various sectors must collaborate to ensure responsible deployment."),
    ("Borderline",      "uncertain",    "I've been thinking a lot about remote work lately. There are genuine tradeoffs —  flexibility and no commute on one side, isolation and blurred work-life boundaries  on the other. Studies show productivity varies widely by individual and role type." ),
    ("Clearly Human",   "likely_human", "ok so i finally tried that new ramen place downtown and honestly?  underwhelming. the broth was fine but they put WAY too much sodium in it and  i was thirsty for like three hours after. my friend got the spicy version and  said it was better. probably won't go back unless someone drags me there"),
]

print("=" * 70)
print("SIGNAL COMPARISON")
print("=" * 70)
print(f"{'Sample':<16} {'LLM':>6} {'Style':>6} {'Combined':>9}  {'Got':<14} {'Expected':<14} Pass?")
print("-" * 70)

all_passed = True
seen_labels = set()

for sample_name, expected_attribution, text in samples:
    llm      = get_llm_signal(text)
    style    = get_stylometric_signal(text)
    combined = calculate_confidence(llm, style)
    attribution, label_text = get_transparency_label(combined)

    seen_labels.add(attribution)
    passed = attribution == expected_attribution
    all_passed = all_passed and passed

    print(f"{sample_name:<16} {llm:>6.2f} {style:>6.2f} {combined:>9.4f}  {attribution:<14} {expected_attribution:<14} {'PASS' if passed else 'FAIL'}")
    print(f"  label: \"{label_text[:80]}...\"")
    print()

print("=" * 70)
print(f"All three label variants reached: {sorted(seen_labels)}")
print(f"All expected attributions matched: {'YES' if all_passed else 'NO — check failing rows above'}")
