from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from typing import Optional

# =======================
# Startup Diagnostics
# =======================
print("="*50)
print("🚀 Starting HealthGenA API")
print(f"Python version: {sys.version}")
print(f"PORT environment variable: {os.environ.get('PORT', 'NOT SET')}")
print("="*50)

# =======================
# Import with Error Handling
# =======================
index = None
get_gemini_summary = None
MasterSearch = None
google_search_agent = None
store_message = None
create_empty_session = None
get_sessions = None
get_session_messages = None
session_exists = None

try:
    from knowledgebase.pinecone_client import index
    print("✅ Pinecone client imported successfully")
except Exception as e:
    print(f"❌ Failed to import Pinecone: {e}")
    import traceback
    traceback.print_exc()

try:
    from agents.geminiSetup import get_gemini_summary
    print("✅ Gemini setup imported successfully")
except Exception as e:
    print(f"❌ Failed to import Gemini: {e}")
    import traceback
    traceback.print_exc()

try:
    from agents.search_agent import MasterSearch
    print("✅ Search agent imported successfully")
except Exception as e:
    print(f"❌ Failed to import MasterSearch: {e}")
    import traceback
    traceback.print_exc()

try:
    from agents.google_agent import google_search_agent
    print("✅ Google agent imported successfully")
except Exception as e:
    print(f"❌ Failed to import Google agent: {e}")
    import traceback
    traceback.print_exc()

try:
    from mongoDb.session_manager import (
        store_message, create_empty_session, 
        get_sessions, get_session_messages, session_exists
    )
    print("✅ MongoDB session manager imported successfully")
except Exception as e:
    print(f"❌ Failed to import MongoDB: {e}")
    import traceback
    traceback.print_exc()

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# Health Check Endpoints
# =======================
@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {
        "status": "healthy",
        "service": "HealthGenA Semantic Medical Search",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    health_status = {
        "status": "ok",
        "services": {
            "pinecone": index is not None,
            "gemini": get_gemini_summary is not None,
            "search_agent": MasterSearch is not None,
            "google_agent": google_search_agent is not None,
            "mongodb": all([store_message, create_empty_session, get_sessions])
        }
    }
    return health_status

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
search_agent = None
try:
    if MasterSearch and index:
        search_agent = MasterSearch(pinecone_index=index)
        print("✅ Search agent initialized successfully")
    else:
        print("⚠️ Search agent not initialized (missing dependencies)")
except Exception as e:
    print(f"❌ Failed to initialize search agent: {e}")
    import traceback
    traceback.print_exc()

# =======================
# Helper Functions
# =======================
def summarization_agent(kb_results, google_results, user_query):
    """
    Merge Pinecone and Google results, format for Gemini summarization.
    """
    if not get_gemini_summary:
        raise HTTPException(status_code=503, detail="Gemini service not available")
    
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

# =======================
# Session Management Routes
# =======================
@app.post("/new-session")
async def new_session(data: SessionCreate):
    """Create a new chat session"""
    if not create_empty_session:
        raise HTTPException(status_code=503, detail="Session service not available")
    
    try:
        session_id = create_empty_session(email=data.email, title=data.title or "New Chat")
        return {"session_id": session_id, "title": data.title or "New Chat"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/sessions/{email}")
async def list_sessions(email: str):
    """List all sessions for a user"""
    if not get_sessions:
        raise HTTPException(status_code=503, detail="Session service not available")
    
    try:
        sessions = get_sessions(email)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@app.get("/sessions/{email}/{session_id}/messages")
async def list_session_messages(email: str, session_id: str):
    """Return messages array for the given session"""
    if not get_session_messages:
        raise HTTPException(status_code=503, detail="Session service not available")
    
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve messages: {str(e)}")

# =======================
# Main Query Route
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
    # Check if all required services are available
    if not all([search_agent, google_search_agent, get_gemini_summary, store_message]):
        missing_services = []
        if not search_agent: missing_services.append("search_agent")
        if not google_search_agent: missing_services.append("google_search")
        if not get_gemini_summary: missing_services.append("gemini")
        if not store_message: missing_services.append("session_storage")
        
        raise HTTPException(
            status_code=503, 
            detail=f"Required services not available: {', '.join(missing_services)}"
        )
    
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

        # Step 7: Store messages in session
        try:
            store_message(data.email, data.session_id, role="user", content=data.query)
            store_message(data.email, data.session_id, role="assistant", content=summary)
        except Exception as e:
            print(f"⚠️ Warning: Failed to store messages: {e}")

        # Step 8: Return structured output
        return {
            "query": data.query,
            "refined_queries": enriched_queries,
            "google_results": google_results,
            "semantic_results": sorted_results,
            "summary": summary,
            "final_response": final_response
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in query pipeline: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

print("="*50)
print("✅ FastAPI app initialized successfully")
print("🌐 Ready to accept connections")
print("="*50)