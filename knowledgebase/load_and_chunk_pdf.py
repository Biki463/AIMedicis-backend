import json
from typing import List
from langchain.schema import Document


def load_and_chunk_json(
    json_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Document]:
    """
    Load a JSON file and split it into chunks.
    
    Args:
        json_path: Path to the JSON file
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of Document objects containing the chunked text
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] JSON file not found: {json_path}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load JSON: {json_path}, error: {e}")
        return []
    
    documents = []
    file_name = json_data.get("file_name", "unknown")
    classification = json_data.get("classification", "unknown")
    
    for section in json_data.get("sections", []):
        section_id = section.get("id", "")
        title = section.get("title", "")
        summary = section.get("summary", "")
        content = section.get("content", "")
        page_range = section.get("page_range", [0, 0])
        tables = section.get("tables", [])
        key_terms = section.get("key_terms", [])
        
        # Combine title, summary, and content for context
        full_text = f"Title: {title}\n\nSummary: {summary}\n\nContent: {content}"
        
        # Split into chunks based on chunk_size
        if len(full_text) > chunk_size:
            start = 0
            chunk_index = 0
            while start < len(full_text):
                end = start + chunk_size
                chunk_text = full_text[start:end]
                
                doc = Document(
                    page_content=chunk_text,
                    metadata={
                        "source": file_name,
                        "classification": classification,
                        "section_id": section_id,
                        "title": title,
                        "page": page_range[0] if page_range else 0,
                        "page_range": page_range,
                        "chunk_index": chunk_index,
                        "has_tables": len(tables) > 0,
                        "key_terms": key_terms,
                        "content_type": "text"
                    }
                )
                documents.append(doc)
                
                start = end - chunk_overlap
                chunk_index += 1
        else:
            doc = Document(
                page_content=full_text,
                metadata={
                    "source": file_name,
                    "classification": classification,
                    "section_id": section_id,
                    "title": title,
                    "page": page_range[0] if page_range else 0,
                    "page_range": page_range,
                    "chunk_index": 0,
                    "has_tables": len(tables) > 0,
                    "key_terms": key_terms,
                    "content_type": "text"
                }
            )
            documents.append(doc)
        
        # Add tables as separate documents
        for table_idx, table in enumerate(tables):
            table_text = f"Table from {title}:\n{json.dumps(table, indent=2)}"
            doc = Document(
                page_content=table_text,
                metadata={
                    "source": file_name,
                    "classification": classification,
                    "section_id": section_id,
                    "title": title,
                    "page": page_range[0] if page_range else 0,
                    "page_range": page_range,
                    "table_index": table_idx,
                    "content_type": "table"
                }
            )
            documents.append(doc)
    
    if not documents:
        print(f"[WARNING] No content extracted from JSON: {json_path}")
        return []
    
    print(f"[INFO] JSON '{json_path}' loaded and split into {len(documents)} chunks.")
    return documents