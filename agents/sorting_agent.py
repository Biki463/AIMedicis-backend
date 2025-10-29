from .geminiSetup import get_gemini_summary

def classify_query(query: str) -> str:
    """
    Classifies a medical query into Treatment, Diagnosis, or Clinical_rial
    using Gemini model.
    """
    prompt = (
        f"Classify the following medical query into one of these categories: "
        f"Treatment, Diagnosis, Clinical_Trial.\n"
        f"Query: {query}\n"
        f"Answer with only the category name."
    )
    category = get_gemini_summary(prompt).strip()
    # Optional: basic cleanup
    category = category.split("\n")[0].strip().lower()
    if category not in ["treatment", "diagnosis", "clinical_trial"]:
        category = "treatment"  # default fallback
        print(category)
    return category
