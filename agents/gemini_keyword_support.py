import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def gemini_summarize(text: str) -> list:
    """
    Use Gemini to produce enriched biomedical keywords for better semantic search.
    Returns a list of refined query terms, without bias towards clinical trials.
    """
    prompt = f"""
    You are a medical search assistant.  
    Given a user's query, rewrite it into a concise biomedical research phrase and generate
    3–5 related keywords covering diagnosis, treatment, and clinical trials.  
    Avoid bias towards any single category.

    Input: "{text}"

    Output format:
    - Short refined query phrase
    - List of related keywords
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    enriched_queries = [line.strip("- ").strip() for line in response.text.split("\n") if line.strip()]
    return enriched_queries
