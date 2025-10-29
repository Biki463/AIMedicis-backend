import os
import time
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import traceback
import numpy as np

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()

# -------------------------
# Local Embedding Model Setup
# -------------------------
class EmbeddingsClient:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 50):
        """
        Local EmbeddingsClient using SentenceTransformer instead of Cohere.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        print(f"[DEBUG] Loading local embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"[DEBUG] Model loaded with embedding dimension: {self.embedding_dim}")

    def embed_query(self, text: str):
        """Generate embedding for a single query."""
        try:
            print(f"[DEBUG] Embedding query text: {text[:50]}...")
            embedding = self.model.encode(
                [text],
                convert_to_numpy=True,
                show_progress_bar=False
            )[0]
            return embedding.tolist()
        except Exception as e:
            print("[ERROR] embed_query failed:", e)
            traceback.print_exc()
            return None

    def embed_documents(self, texts: list):
        """Generate embeddings for a list of documents."""
        embeddings = []
        print(f"[DEBUG] Embedding {len(texts)} documents locally.")
        try:
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                print(f"[DEBUG] Processing batch {i} to {i + len(batch)}...")
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                embeddings.extend(batch_embeddings.tolist())
                time.sleep(0.2)  # small delay for safety
        except Exception as e:
            print("[ERROR] embed_documents failed:", e)
            traceback.print_exc()
        return embeddings


# -------------------------
# Pinecone Setup
# -------------------------
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT")  # e.g., "us-east-1"
print("[DEBUG] Pinecone API Key Loaded:", bool(pinecone_api_key))

if not pinecone_api_key or not pinecone_env:
    raise ValueError("PINECONE_API_KEY or PINECONE_ENVIRONMENT not found")

# ⚠️ Important: Use a NEW index for local embeddings
INDEX_NAME = "medical-search-local"   # <--- changed to avoid dimension conflict

pc = Pinecone(api_key=pinecone_api_key)

# List indexes
indexes = pc.list_indexes().names()
print("[DEBUG] Pinecone indexes:", indexes)

# Create new index if it doesn’t exist
if INDEX_NAME not in indexes:
    dummy_model = SentenceTransformer("all-MiniLM-L6-v2")
    dimension = dummy_model.get_sentence_embedding_dimension()
    print(f"[DEBUG] Creating Pinecone index '{INDEX_NAME}' with dimension: {dimension}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=dimension,  # 384 for all-MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
else:
    print(f"[DEBUG] Pinecone index '{INDEX_NAME}' already exists.")

# Connect to index
index = pc.Index(INDEX_NAME)
print(f"[DEBUG] Connected to Pinecone index: {INDEX_NAME}")
