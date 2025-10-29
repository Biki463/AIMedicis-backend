from embedding_agent import EmbeddingsClient
from .ner_extractor import extract_entities
from .gemini_keyword_support import gemini_summarize


class MasterSearch:
    def __init__(self, pinecone_index, namespaces=None):
        """
        Multi-namespace Pinecone semantic search.
        """
        self.index = pinecone_index
        self.embeddings = EmbeddingsClient()

        # Default to all known namespaces if not provided
        self.namespaces = namespaces or [
            "treatment",
            "diagnosis",
            "clinical_trial"
        ]

    def semantic_search(self, query: str, top_k: int = 20):
        """
        Search across all namespaces.
        """
        query_vector = self.embeddings.embed_query(query)
        all_results = []

        for namespace in self.namespaces:
            try:
                results = self.index.query(
                    vector=query_vector,
                    top_k=top_k,
                    include_metadata=True,
                    namespace=namespace
                ).get("matches", [])

                for r in results:
                    r["namespace"] = namespace
                    all_results.append(r)

            except Exception as e:
                print(f"⚠️ Error searching namespace '{namespace}': {e}")

        return all_results

    def enrich_query(self, query: str):
        """
        Gemini + NER enrichment.
        """
        enriched = gemini_summarize(query)

        if isinstance(enriched, str):
            enriched = [q.strip() for q in enriched.split(",") if q.strip()]

        entities = extract_entities(query)
        enriched += entities

        return list(set(filter(None, enriched)))

    def search_all(self, query: str, top_k: int = 20):
        """
        Enrich query → search all namespaces → deduplicate & sort results.
        """
        enriched_queries = self.enrich_query(query)
        all_results = []

        print(f"[DEBUG] Enriched Queries: {enriched_queries}")
        print(f"[DEBUG] Searching namespaces: {self.namespaces}")

        for eq in enriched_queries:
            try:
                eq_results = self.semantic_search(eq, top_k)
                for res in eq_results:
                    res["query_variant"] = eq
                    all_results.append(res)
            except Exception as e:
                print(f"⚠️ Search error for query '{eq}': {e}")

        # Deduplicate and sort by score
        unique_results = {r["id"]: r for r in all_results}.values()
        sorted_results = sorted(unique_results, key=lambda x: x.get("score", 0), reverse=True)

        print(f"[DEBUG] Total results found: {len(sorted_results)}")
        return {
            "query": query,
            "refined_queries": enriched_queries,
            "semantic_results": sorted_results
        }
