from app import get_llm_signal

samples = [
    ("Clearly AI", "Furthermore, it is pivotal to delve into the multifaceted implications of this transformative and game-changing paradigm. In conclusion, we must unlock new synergies to empower stakeholders."),
    ("Clearly Human", "i dunno man, i just felt really off that whole week. like nothing was wrong exactly but everything felt kinda heavy? hard to explain."),
    ("Formal/Academic", "The results of the study indicate a statistically significant correlation between sleep deprivation and reduced cognitive performance across all age groups tested."),
    ("Hybrid", "AI tools are genuinely useful — I use them all the time — but I've started noticing how they make everything sound weirdly tidy, you know? Like, real thoughts are messier than that."),
]

for label, text in samples:
    score = get_llm_signal(text)
    print(f"[{label}]")
    print(f"  Score: {score}")
    print(f"  Text:  {text[:80]}...")
    print()
