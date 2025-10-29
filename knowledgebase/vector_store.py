# knowledge_base/vector_store.py

from pinecone_client import index

class VectorStore:
    def __init__(self, namespace: str):
        self.index = index
        self.namespace = namespace

    def store_embeddings(self, embeddings, metadatas, ids):
        self.index.upsert(
            vectors=[(id_, emb, meta) for id_, emb, meta in zip(ids, embeddings, metadatas)],
            namespace=self.namespace
        )

    def query(self, query_vector, top_k=5):
        return self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace
        )
