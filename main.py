#!/usr/bin/env python3
"""
HealthGenA Semantic Medical Search API
"""
import sys
import os

# Force unbuffered output so logs appear immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("="*60, flush=True)
print("🚀 STARTING APPLICATION", flush=True)
print(f"Python: {sys.version}", flush=True)
print(f"PORT: {os.environ.get('PORT', 'NOT SET')}", flush=True)
print(f"Working Directory: {os.getcwd()}", flush=True)
print("="*60, flush=True)

# Import standard libraries first
print("📦 Importing standard libraries...", flush=True)
try:
    from typing import Optional
    from pydantic import BaseModel
    print("✅ Standard libraries imported", flush=True)
except Exception as e:
    print(f"❌ CRITICAL: Standard library import failed: {e}", flush=True)
    sys.exit(1)

# Import FastAPI
print("📦 Importing FastAPI...", flush=True)
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    print("✅ FastAPI imported", flush=True)
except Exception as e:
    print(f"❌ CRITICAL: FastAPI import failed: {e}", flush=True)
    print("Run: pip install 'fastapi[standard]'", flush=True)
    sys.exit(1)

# Initialize FastAPI app EARLY
print("🔧 Initializing FastAPI app...", flush=True)
app = FastAPI(title="HealthGenA Semantic Medical Search")

# Add CORS
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
print("✅ FastAPI app initialized", flush=True)

# Add immediate health check
@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "HealthGenA API",
        "port": os.environ.get("PORT", "not set")
    }

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Basic health check passed"}

print("✅ Health endpoints registered", flush=True)

# Now try to import custom modules
index = None
get_gemini_summary = None
MasterSearch = None
google_search_agent = None
store_message = None
create_empty_session = None
get_sessions = None
get_session_messages = None
session_exists = None
search_agent = None

print("\n📦 Importing custom modules...", flush=True)

# Pinecone
try:
    print("  → Importing knowledgebase.pinecone_client...", flush=True)
    from knowledgebase.pinecone_client import index
    print("  ✅ Pinecone client imported", flush=True)
except ImportError as e:
    print(f"  ⚠️ Pinecone import failed: {e}", flush=True)
except Exception as e:
    print(f"  ⚠️ Pinecone error: {e}", flush=True)

# Gemini
try:
    print("  → Importing agents.geminiSetup...", flush=True)
    from agents.geminiSetup import get_gemini_summary
    print("  ✅ Gemini imported", flush=True)
except ImportError as e:
    print(f"  ⚠️ Gemini import failed: {e}", flush=True)
except Exception as e:
    print(f"  ⚠️ Gemini error: {e}", flush=True)

# Search Agent
try:
    print("  → Importing agents.search_agent...", flush=True)
    from agents.search_agent import MasterSearch
    print("  ✅ Search agent imported", flush=True)
except ImportError as e:
    print(f"  ⚠️ Search agent import failed: {e}", flush=True)
except Exception as e:
    print(f"  ⚠️ Search agent error: {e}", flush=True)

# Google Agent
try:
    print("  → Importing agents.google_agent...", flush=True)
    from agents.google_agent import google_search_agent
    print("  ✅ Google agent imported", flush=True)
except ImportError as e:
    print(f"  ⚠️ Google agent import failed: {e}", flush=True)
except Exception as e:
    print(f"  ⚠️ Google agent error: {e}", flush=True)

# MongoDB
try:
    print("  → Importing mongoDb.session_manager...", flush=True)
    from mongoDb.session_manager import (
        store_message, create_empty_session,
        get_sessions, get_session_messages, session_exists
    )
    print("  ✅ MongoDB imported", flush=True)
except ImportError as e:
    print(f"  ⚠️ MongoDB import failed: {e}", flush=True)
except Exception as e:
    print(f"  ⚠️ MongoDB error: {e}", flush=True)

print("\n🔧 Initializing services...", flush=True)

# Initialize search agent
try:
    if MasterSearch and index:
        search_agent = MasterSearch(pinecone_index=index)
        print("✅ Search agent initialized", flush=True)
    else:
        print("⚠️ Search agent not initialized (missing dependencies)", flush=True)
except Exception as e:
    print(f"⚠️ Search agent init error: {e}", flush=True)

# Models
class QueryData(BaseModel):
    email: str
    session_id: str
    query: str

class SessionCreate(BaseModel):
    email: str
    title: Optional[str] = "New Chat"
    content: Optional[str] = None

# Helper Functions
def summarization_agent(kb_results, google_results, user_query):
    if not get_gemini_summary:
        raise HTTPException(status_code=503, detail="Gemini service unavailable")
    
    combined_results = []
    for r in kb_results:
        combined_results.append({
            "metadata": r.get("metadata", {}),
            "score": r.get("score", 0),
        })
    
    for g in google_results:
        combined_results.append({
            "metadata": {
                "source": g["title"],
                "text": g["snippet"],
                "url": g["link"]
            },
            "score": 0.8
        })
    
    return get_gemini_summary(combined_results, user_query)

def recommendation_agent(summary, google_results, kb_results):
    citations = []
    for g in google_results[:3]:
        citations.append({"source": g["title"], "link": g["link"]})
    
    for k in kb_results[:2]:
        source = k.get("metadata", {}).get("source")
        url = k.get("metadata", {}).get("url")
        if source:
            citations.append({"source": source, "link": url or "#"})
    
    return {"answer": summary, "citations": citations}

# Session Routes
@app.post("/new-session")
async def new_session(data: SessionCreate):
    if not create_empty_session:
        raise HTTPException(status_code=503, detail="Session service unavailable")
    try:
        session_id = create_empty_session(email=data.email, title=data.title or "New Chat")
        return {"session_id": session_id, "title": data.title or "New Chat"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{email}")
async def list_sessions(email: str):
    if not get_sessions:
        raise HTTPException(status_code=503, detail="Session service unavailable")
    try:
        sessions = get_sessions(email)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{email}/{session_id}/messages")
async def list_session_messages(email: str, session_id: str):
    if not get_session_messages:
        raise HTTPException(status_code=503, detail="Session service unavailable")
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
        raise HTTPException(status_code=500, detail=str(e))

# Main Query Route
@app.post("/query")
async def query_pipeline(data: QueryData):
    if not all([search_agent, google_search_agent, get_gemini_summary]):
        missing = []
        if not search_agent: missing.append("search_agent")
        if not google_search_agent: missing.append("google_search")
        if not get_gemini_summary: missing.append("gemini")
        raise HTTPException(status_code=503, detail=f"Services unavailable: {', '.join(missing)}")
    
    try:
        enriched_queries = search_agent.enrich_query(data.query)
        google_results = google_search_agent(data.query, num_results=5)
        
        semantic_results = []
        for eq in enriched_queries:
            semantic_results.extend(search_agent.semantic_search(eq, top_k=20))
        
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
        
        top_matches = sorted_results[:8]
        summary = summarization_agent(top_matches, google_results, data.query)
        final_response = recommendation_agent(summary, google_results, top_matches)
        
        if store_message:
            try:
                store_message(data.email, data.session_id, role="user", content=data.query)
                store_message(data.email, data.session_id, role="assistant", content=summary)
            except Exception as e:
                print(f"⚠️ Failed to store messages: {e}", flush=True)
        
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
        print(f"❌ Query error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

print("\n" + "="*60, flush=True)
print("✅ APPLICATION READY", flush=True)
print(f"🌐 Listening on port {os.environ.get('PORT', '8000')}", flush=True)
print("="*60 + "\n", flush=True)

# Start uvicorn server when run directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting uvicorn on port {port}...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
