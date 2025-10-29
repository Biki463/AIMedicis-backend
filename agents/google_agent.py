import os
from serpapi import GoogleSearch

def google_search_agent(query, num_results=5):
    """
    Fetches live Google results using SerpAPI.
    Returns list of {title, link, snippet}.
    """
    params = {
        "engine": "google",
        "q": query,
        "api_key": os.getenv("SERPAPI_KEY"),
        "num": num_results
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    output = []

    if "organic_results" in results:
        for r in results["organic_results"][:num_results]:
            output.append({
                "title": r.get("title"),
                "link": r.get("link"),
                "snippet": r.get("snippet", "")
            })

    return output
