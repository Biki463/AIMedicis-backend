import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load .env variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")  # e.g., "us-east-1"
INDEX_NAME = "medical-search-local"

# Create Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Create index if it does not exist
if INDEX_NAME not in pc.list_indexes().names():
    print(f"[INFO] Index '{INDEX_NAME}' not found. Creating...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,  # Match your embedding dimension
        metric="cosine",  # Or "euclidean"
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

# Connect to index
index = pc.Index(INDEX_NAME)
print(f"[INFO] Connected to Pinecone index: {INDEX_NAME}")
