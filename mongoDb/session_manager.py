from datetime import datetime
import uuid
from mongoDb.mongodb import db

users_collection = db["chat_history"]

# ============================
# Create a new chat session (only with message)
# ============================
def create_new_session(email: str, content: str = None, role: str = "user", title: str = "New Chat"):
    if not content or not content.strip():
        return None

    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_session = {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "title": title,
        "messages": [
            {
                "role": role,
                "content": content.strip(),
                "timestamp": now
            }
        ]
    }

    user_doc = users_collection.find_one({"email": email})
    if not user_doc:
        users_collection.insert_one({
            "email": email,
            "sessions": [new_session]
        })
    else:
        users_collection.update_one(
            {"email": email},
            {"$push": {"sessions": new_session}}
        )

    # Auto-update title from first few words of message
    if role == "user" and content:
        new_title = " ".join(content.split()[:8])
        users_collection.update_one(
            {"email": email, "sessions.session_id": session_id},
            {"$set": {"sessions.$.title": new_title}}
        )

    return session_id


# ============================
# ✅ Create an empty session
# ============================
def create_empty_session(email: str, title: str = "New Chat"):
    """
    Creates an empty session but auto-removes it if it remains empty later.
    """
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_session = {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "title": title,
        "messages": []
    }

    user_doc = users_collection.find_one({"email": email})
    if not user_doc:
        users_collection.insert_one({
            "email": email,
            "sessions": [new_session]
        })
    else:
        users_collection.update_one(
            {"email": email},
            {"$push": {"sessions": new_session}}
        )

    return session_id


# ============================
# ✅ Delete empty sessions
# ============================
def delete_empty_sessions(email: str):
    """
    Removes all sessions for a user that have no messages.
    """
    users_collection.update_one(
        {"email": email},
        {"$pull": {"sessions": {"messages": {"$size": 0}}}}
    )


# ============================
# Store a message in an existing session
# ============================
def store_message(email: str, session_id: str, role: str, content: str):
    if not content or not content.strip():
        return
    if not session_id:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = {
        "role": role,
        "content": content.strip(),
        "timestamp": now
    }

    # Try to update existing session
    result = users_collection.update_one(
        {"email": email, "sessions.session_id": session_id},
        {
            "$push": {"sessions.$.messages": message},
            "$set": {"sessions.$.updated_at": now}
        }
    )

    # ✅ Auto-create session if it doesn't exist
    if result.modified_count == 0:
        print(f"⚠️ Session not found. Creating new session {session_id} for {email}")
        new_session = {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "title": " ".join(content.split()[:8]),
            "messages": [message]
        }

        user_doc = users_collection.find_one({"email": email})
        if not user_doc:
            users_collection.insert_one({
                "email": email,
                "sessions": [new_session]
            })
        else:
            users_collection.update_one(
                {"email": email},
                {"$push": {"sessions": new_session}}
            )


# ============================
# Get all sessions for a user
# ============================
def get_sessions(email: str):
    # 🧹 Clean empty sessions before returning
    delete_empty_sessions(email)

    user_doc = users_collection.find_one({"email": email})
    if not user_doc:
        return []
    
    sessions = user_doc.get("sessions", [])
    # Sort newest first
    sorted_sessions = sorted(sessions, key=lambda s: s.get("updated_at", ""), reverse=True)
    
    return [
        {
            "session_id": s["session_id"],
            "title": s.get("title", "Untitled"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
        }
        for s in sorted_sessions
        if len(s.get("messages", [])) > 0  # ✅ Ensure not empty
    ]


# ============================
# Get messages in a session
# ============================
def get_session_messages(email: str, session_id: str):
    user_doc = users_collection.find_one({"email": email})
    if not user_doc:
        return []
    
    for s in user_doc.get("sessions", []):
        if s["session_id"] == session_id:
            return s.get("messages", [])
    
    return []


# ============================
# Check if a session exists
# ============================
def session_exists(email: str, session_id: str) -> bool:
    result = users_collection.find_one(
        {"email": email, "sessions.session_id": session_id}
    )
    return result is not None
