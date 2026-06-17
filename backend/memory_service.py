# backend/memory_service.py

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from datetime import datetime
import uuid

embedding_model = None

def get_embedding_model():
    global embedding_model

    if embedding_model is None:
        print("Loading embedding model...", flush=True)
        embedding_model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

    return embedding_model

chroma_client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

collection = chroma_client.get_or_create_collection(
    name="personaos_memories",
    metadata={"hnsw:space": "cosine"}
)


def embed_text(text: str) -> list:
    return get_embedding_model().encode(text).tolist()


def store_memory(
    user_id:      int,
    user_message: str,
    ai_response:  str,
    topic:        str = "general"
) -> str:
    combined_text = f"Question: {user_message}\nAnswer: {ai_response}"
    embedding     = embed_text(combined_text)
    memory_id     = str(uuid.uuid4())

    collection.add(
        ids=[memory_id],
        embeddings=[embedding],
        documents=[combined_text],
        metadatas=[{
            "user_id":      str(user_id),       # Always store as string
            "user_message": user_message,
            "ai_response":  ai_response[:1000],
            "topic":        topic,
            "created_at":   datetime.now().isoformat()
        }]
    )
    print(f"💾 Memory stored: topic='{topic}', id={memory_id[:8]}...")
    return memory_id


def retrieve_memories(
    user_id:   int,
    query:     str,
    n_results: int = 3,
    topic:     str = None
) -> list:
    """
    Fixed retrieval:
    - Uses ONLY single-field where clause (no $and — avoids ChromaDB version issues)
    - Filters by user_id in the where clause
    - Post-filters by topic in Python if needed
    - Logs what's happening so bugs are visible
    """

    total_in_collection = collection.count()
    print(f"🔍 Retrieving memories: user_id={user_id}, query='{query[:50]}...', total_in_db={total_in_collection}")

    if total_in_collection == 0:
        print("⚠️  ChromaDB collection is empty.")
        return []

    query_embedding = embed_text(query)

    # Fetch more than needed so we can post-filter by user and deduplicate
    # Cap at total collection size to avoid ChromaDB errors
    fetch_count = min(n_results * 5, total_in_collection)

    try:
        # Single-condition where clause — much more compatible across ChromaDB versions
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_count,
            where={"user_id": str(user_id)},    # ✅ Simple single filter only
            include=["metadatas", "distances"]
        )
    except Exception as e:
        print(f"❌ ChromaDB query failed: {e}")
        # Last resort: fetch everything and filter manually
        try:
            print("🔄 Falling back to unfiltered query...")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=fetch_count,
                include=["metadatas", "distances"]
            )
        except Exception as e2:
            print(f"❌ Fallback query also failed: {e2}")
            return []

    if not results["metadatas"] or not results["metadatas"][0]:
        print("⚠️  ChromaDB returned no results.")
        return []

    memories      = []
    seen_snippets = []

    for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
        # Manual user filter (handles fallback case where where= wasn't applied)
        if str(metadata.get("user_id")) != str(user_id):
            continue

        similarity = round(1 - distance, 3)
        print(f"   Found memory: similarity={similarity}, topic={metadata.get('topic')}")

        if similarity < 0.25:
            continue

        # Optional Python-side topic filter
        if topic and topic != "general":
            if metadata.get("topic") != topic:
                continue

        # Deduplicate
        snippet = metadata.get("ai_response", "")[:100]
        if any(_text_overlap(snippet, seen) > 0.7 for seen in seen_snippets):
            continue

        seen_snippets.append(snippet)
        memories.append({
            "user_message": metadata.get("user_message", ""),
            "ai_response":  metadata.get("ai_response", ""),
            "similarity":   similarity,
            "topic":        metadata.get("topic", "general"),
            "created_at":   metadata.get("created_at", "")
        })

        if len(memories) >= n_results:
            break

    print(f"✅ Retrieved {len(memories)} memories for injection.")
    return memories


def _text_overlap(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a), len(words_b))


def get_memory_count(user_id: int) -> int:
    try:
        results = collection.get(where={"user_id": str(user_id)})
        return len(results["ids"])
    except Exception:
        return 0