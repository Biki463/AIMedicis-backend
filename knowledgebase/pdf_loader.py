import os
import json
from pathlib import Path
from embedding import EmbeddingsClient, index
from vector_store import VectorStore
from load_and_chunk_pdf import load_and_chunk_json

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "downloads"
PROCESSED_FILES_LOG = BASE_DIR / "processed_json.json"


def load_processed_files():
    if PROCESSED_FILES_LOG.exists():
        with open(PROCESSED_FILES_LOG, 'r') as f:
            return json.load(f)
    return {}


def save_processed_file(json_path, namespace, chunk_count):
    processed = load_processed_files()
    if namespace not in processed:
        processed[namespace] = {}

    processed[namespace][str(json_path)] = {
        "chunk_count": chunk_count,
        "processed_at": str(os.path.getmtime(json_path))
    }

    with open(PROCESSED_FILES_LOG, 'w') as f:
        json.dump(processed, f, indent=2)

    print(f"[INFO] Logged: {json_path} ({chunk_count} chunks)")


def is_already_processed(json_path, namespace):
    processed = load_processed_files()
    if namespace in processed and str(json_path) in processed[namespace]:
        stored_mtime = processed[namespace][str(json_path)]["processed_at"]
        current_mtime = str(os.path.getmtime(json_path))
        return stored_mtime == current_mtime
    return False


def process_category_json(category_folder: Path, namespace: str, batch_size: int = 50):
    json_files = [f for f in category_folder.glob("*.json")]
    print(f"[INFO] Found {len(json_files)} JSON files in {category_folder}.")

    embeddings_client = EmbeddingsClient()
    vector_store = VectorStore(namespace)

    processed_count = 0
    skipped_count = 0

    for json_path in json_files:
        if is_already_processed(json_path, namespace):
            skipped_count += 1
            print(f"[SKIP] Already processed: {json_path.name}")
            continue

        print(f"[INFO] Processing: {json_path.name}")
        try:
            chunks = load_and_chunk_json(str(json_path))
            if not chunks:
                print(f"[WARNING] No chunks extracted from {json_path}")
                continue

            total_chunks = len(chunks)
            for batch_start in range(0, total_chunks, batch_size):
                batch_chunks = chunks[batch_start : batch_start + batch_size]

                texts = [chunk.page_content for chunk in batch_chunks]
                embeddings = embeddings_client.embed_documents(texts)

                if not embeddings:
                    print(f"[ERROR] Failed to embed batch starting at chunk {batch_start}")
                    continue

                metadatas = [
                    {
                        "source": chunk.metadata.get("source", ""),
                        "classification": chunk.metadata.get("classification", ""),
                        "section_id": chunk.metadata.get("section_id", ""),
                        "title": chunk.metadata.get("title", ""),
                        "page": int(chunk.metadata.get("page", 0)),
                        "page_range": str(chunk.metadata.get("page_range", [])),
                        "content_type": chunk.metadata.get("content_type", "text"),
                        "text": chunk.page_content[:500]
                    }
                    for chunk in batch_chunks
                ]
                ids = [f"{json_path.stem}_chunk_{batch_start + i}" for i in range(len(batch_chunks))]

                vector_store.store_embeddings(embeddings, metadatas, ids)
                print(f"[INFO] Stored batch {batch_start // batch_size + 1} ({len(batch_chunks)} chunks) for {json_path.name}")

            save_processed_file(json_path, namespace, len(chunks))
            processed_count += 1

        except Exception as e:
            print(f"[ERROR] Failed to process {json_path}: {e}")
            continue

    print(f"\n[SUMMARY] Processed: {processed_count}, Skipped: {skipped_count}, Total: {len(json_files)}")


def process_all_categories():
    categories = {
        "treatment": DATA_DIR / "treatment",
        "diagnosis": DATA_DIR / "diagnosis",
        "clinical_trial": DATA_DIR / "clinical_trial"
    }

    for namespace, folder_path in categories.items():
        if folder_path.exists():
            print(f"\n{'='*60}")
            print(f"Processing folder: {folder_path}")
            print(f"Namespace: {namespace}")
            print(f"{'='*60}")
            process_category_json(folder_path, namespace)
        else:
            print(f"[WARNING] Folder not found: {folder_path}")


def reset_progress(namespace=None, json_file=None):
    processed = load_processed_files()
    if namespace and json_file:
        if namespace in processed and json_file in processed[namespace]:
            del processed[namespace][json_file]
            print(f"[INFO] Reset: {json_file} in {namespace}")
    elif namespace:
        if namespace in processed:
            del processed[namespace]
            print(f"[INFO] Reset namespace: {namespace}")
    else:
        processed = {}
        print("[INFO] Reset all progress")

    with open(PROCESSED_FILES_LOG, 'w') as f:
        json.dump(processed, f, indent=2)


if __name__ == "__main__":
    process_all_categories()
