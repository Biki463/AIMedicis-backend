from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uvicorn
from typing import Optional
from knowledgebase.pinecone_client import index
from agents.geminiSetup import get_gemini_summary
from agents.search_agent import MasterSearch
from agents.google_agent import google_search_agent  # ✅ Google Search Agent



# Import session management utilities
from mongoDb.session_manager import store_message, create_empty_session, get_sessions, get_session_messages,session_exists


# =======================
# App Initialization
# =======================
app = FastAPI(title="HealthGenA Semantic Medical Search")

origins = [
    "https://ai-medicis-frontend.vercel.app",
    "http://localhost:3000"
]



app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# Models
# =======================
class QueryData(BaseModel):
    email: str
    session_id: str
    query: str

    
class SessionCreate(BaseModel):
    email: str
    title: Optional[str] = "New Chat"
    content: Optional[str] = None

# =======================
# Initialize Services
# =======================
search_agent = MasterSearch(pinecone_index=index)

# =======================
# Helper Functions
# =======================
def summarization_agent(kb_results, google_results, user_query):
    """
    Merge Pinecone and Google results, format for Gemini summarization.
    """
    combined_results = []

    # Add Pinecone results with metadata
    for r in kb_results:
        combined_results.append({
            "metadata": r.get("metadata", {}),
            "score": r.get("score", 0),
        })

    # Add Google results as pseudo-KB entries
    for g in google_results:
        combined_results.append({
            "metadata": {
                "source": g["title"],
                "text": g["snippet"],
                "url": g["link"]
            },
            "score": 0.8  # arbitrary mid-score for balance
        })

    summary = get_gemini_summary(combined_results, user_query)
    return summary


def recommendation_agent(summary, google_results, kb_results):
    """
    Attach relevant citation links to the final response.
    """
    citations = []

    # Prefer top Google results first
    for g in google_results[:3]:
        citations.append({
            "source": g["title"],
            "link": g["link"]
        })

    # Add KB document sources if available
    for k in kb_results[:2]:
        source = k.get("metadata", {}).get("source")
        url = k.get("metadata", {}).get("url")
        if source:
            citations.append({
                "source": source,
                "link": url or "#"
            })

    return {
        "answer": summary,
        "citations": citations
    }


@app.post("/new-session")
async def new_session(data: SessionCreate):
    session_id = create_empty_session(email=data.email, title=data.title or "New Chat")
    return {"session_id": session_id, "title": data.title or "New Chat"}


@app.get("/sessions/{email}")
async def list_sessions(email: str):
     sessions = get_sessions(email)
     return {"sessions": sessions}




@app.get("/sessions/{email}/{session_id}/messages")
async def list_session_messages(email: str, session_id: str):
    """
    Return messages array for the given session.
    """
    messages = get_session_messages(email, session_id)
    return [
        {
            "id": str(m.get("_id", "")),
            "sender": "ai" if m.get("role") == "assistant" else "user",
            "text": m.get("content", ""),
            "timestamp": m.get("timestamp"),
        }
        for m in messages
    ]



# =======================
# API Route
# =======================
@app.post("/query")
async def query_pipeline(data: QueryData):
    """
    Full AI pipeline:
    1️⃣ Enrich query (NER + Gemini)
    2️⃣ Fetch Google Search Results
    3️⃣ Semantic Search (Pinecone)
    4️⃣ Summarize using Gemini
    5️⃣ Return answer with citations
    """
    try:
        # Step 1: Enrich the query
        enriched_queries = search_agent.enrich_query(data.query)

        # Step 2: Google Search
        google_results = google_search_agent(data.query, num_results=5)

        # Step 3: Semantic Search in Pinecone
        semantic_results = []
        for eq in enriched_queries:
            semantic_results.extend(search_agent.semantic_search(eq, top_k=20))

        # Step 4: Clean and sort Pinecone results
        cleaned_results = []
        for r in semantic_results:
            cleaned_results.append({
                "id": getattr(r, "id", None) or r.get("id"),
                "score": getattr(r, "score", None) or r.get("score"),
                "metadata": getattr(r, "metadata", None) or r.get("metadata", {}),
                "source": r.get("query_variant", "pinecone")
            })

        unique_results = {r["id"]: r for r in cleaned_results}.values()
        sorted_results = sorted(unique_results, key=lambda x: x["score"], reverse=True)

        # Step 5: Summarization (Combine KB + Google)
        top_matches = sorted_results[:8]
        summary = summarization_agent(top_matches, google_results, data.query)

        # Step 6: Generate final recommendation + citations
        final_response = recommendation_agent(summary, google_results, top_matches)


        # User message
        store_message(data.email, data.session_id, role="user", content=data.query)
        # AI summary response
        store_message(data.email, data.session_id, role="assistant", content=summary)

        # Step 7: Return structured output
        return {
            "query": data.query,
            "refined_queries": enriched_queries,
            "google_results": google_results,
            "semantic_results": sorted_results,
            "summary": summary,
            "final_response": final_response
        }

    except Exception as e:
        return {"error": str(e)}
    

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # use Render’s PORT variable or default
    uvicorn.run("main:app", host="0.0.0.0", port=port)


