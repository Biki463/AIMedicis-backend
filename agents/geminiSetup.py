from dotenv import load_dotenv
import os
import google.generativeai as genai
from urllib.parse import urlparse

# ======================
# Load Environment & Configure Gemini
# ======================
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def get_gemini_summary(semantic_results=None, google_results=None, user_query: str = "") -> str:
    """
    Gemini summarizer with reliable reference extraction.
    - Smarter link extraction from semantic results.
    - Deduplicates and prioritizes valid URLs.
    - Filters only trivial queries (not valid ones).
    """

    try:
        # 1️⃣ Ignore only *trivial* inputs
        trivial_inputs = {"hi", "hii", "hello", "hey", "yo", "ok", "okay", "thanks", "thank you"}
        cleaned_query = user_query.strip().lower()
        if len(cleaned_query.split()) <= 2 and cleaned_query in trivial_inputs:
            return "Please provide a valid medical or health-related question."

        semantic_results = semantic_results or []
        google_results = google_results or []

        # 2️⃣ Flatten safely
        def flatten(data):
            flat = []
            if isinstance(data, (list, tuple)):
                for item in data:
                    flat.extend(flatten(item))
            elif data is not None:
                flat.append(data)
            return flat

        semantic_results = flatten(semantic_results)
        google_results = flatten(google_results)

        if not semantic_results and not google_results:
            return "No relevant results found."

        # 3️⃣ Extract safe score
        def get_score(item):
            try:
                if isinstance(item, dict):
                    return float(item.get("score", 0))
            except Exception:
                pass
            return 0.0

        # 4️⃣ Sort semantic results
        sorted_results = sorted(semantic_results, key=get_score, reverse=True)
        top_results = sorted_results[:15]

        # Helper: extract valid URL from multiple possible keys
        def extract_link(d):
            if not isinstance(d, (dict,)):
                return ""
            possible_keys = ["link", "url", "reference", "source_url", "href", "website"]
            for key in possible_keys:
                val = d.get(key)
                if val and isinstance(val, str) and val.startswith("http"):
                    return val
            # check inside metadata if exists
            meta = d.get("metadata") or {}
            for key in possible_keys:
                val = meta.get(key)
                if val and isinstance(val, str) and val.startswith("http"):
                    return val
            return ""

        # 5️⃣ Build semantic context with improved link extraction
        seen_links = set()
        combined_semantic_text = ""
        for i, result in enumerate(top_results, start=1):
            try:
                if isinstance(result, dict):
                    metadata = result.get("metadata", {}) or {}
                    source = metadata.get("source") or result.get("source") or "Unknown source"
                    text = (
                        metadata.get("text")
                        or metadata.get("content")
                        or result.get("text")
                        or result.get("content")
                        or str(result)
                    )
                    link = extract_link(result)
                    if link:
                        parsed = urlparse(link)
                        if not parsed.scheme.startswith("http"):
                            link = ""
                    if link in seen_links:
                        link = ""  # skip duplicates
                    else:
                        if link:
                            seen_links.add(link)
                else:
                    source, text, link = "Unknown source", str(result), ""
            except Exception:
                source, text, link = "Unknown source", str(result), ""

            combined_semantic_text += (
                f"[{i}] Source: {source}\n"
                f"Link: {link or 'Source unavailable'}\n"
                f"{text[:2000]}\n\n"
            )

        # 6️⃣ Build Google context (also dedup)
        google_context = ""
        for i, g in enumerate(google_results, start=1):
            try:
                if isinstance(g, dict):
                    title = g.get("title", "No Title")
                    snippet = g.get("snippet", "")
                    link = extract_link(g)
                    if link in seen_links:
                        link = ""
                    else:
                        if link:
                            seen_links.add(link)
                else:
                    title, snippet, link = str(g), "", ""
            except Exception:
                title, snippet, link = str(g), "", ""
            google_context += f"[G{i}] {title} — {snippet}\nLink: {link or 'Source unavailable'}\n\n"

        # 7️⃣ Structured prompt
        prompt = f"""
You are an expert **medical research summarizer**.
Generate an evidence-based, structured summary using the provided verified data.

---
🧠 **User Query:** "{user_query}"
---

Use **only** the provided "Semantic Context" and "Google Search Results".

## RULES:
1. Use existing links if valid URLs are available.
2. If no valid link, write "Source unavailable".
3. Never invent or hallucinate new sources.
4. Keep the output in Markdown format with clear sections.
5. Do not respond conversationally.

---
📚 **Semantic Context:**
{combined_semantic_text}

🔍 **Google Search Results:**
{google_context}
---

Now write the final formatted report as:

# Summary
2–3 short paragraphs overview.

# Detailed Explanation
- Causes / Mechanism
- Symptoms / Diagnosis
- Treatment Options
- Clinical / Research Findings
- Prevention (if relevant)

# Conclusion
Brief final insight.

# References
List all links found:
- **[Title](URL)** — short description
- If no URL: **[Title](Source unavailable)** — short description.
"""

        # 8️⃣ Generate
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        if not response or not hasattr(response, "text"):
            return "No summary generated."

        return response.text.strip()

    except Exception as e:
        return f"Error generating summary: {e}"
