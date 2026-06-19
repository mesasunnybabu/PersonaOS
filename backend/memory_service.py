import os
import requests
import chromadb
from chromadb.config import Settings
from datetime import datetime
import uuid

# Fetch the Hugging Face Token from your Render Environment Variables
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

# 🧠 FIX: Dummy class to prevent ChromaDB from loading heavy default ONNX/onnxruntime utilities
class DisableClientEmbedding:
    def __call__(self, input: list) -> list:
        return []

chroma_client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

# Pass the dummy class here to override default model instantiation
collection = chroma_client.get_or_create_collection(
    name="personaos_memories",
    metadata={"hnsw:space": "cosine"},
    embedding_function=DisableClientEmbedding() # ✅ ONNX runtime disabled
)


def embed_text(text: str) -> list:
    """Calls Hugging Face API instead of loading the model locally to save RAM"""
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN environment variable is missing in Render settings!")
        
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Hugging Face API returned error status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        raise e


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
            "user_id":      str(user_id),
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
    total_in_collection = collection.count()
    print(f"🔍 Retrieving memories: user_id={user_id}, query='{query[:50]}...', total_in_db={total_in_collection}")

    if total_in_collection == 0:
        return []

    query_embedding = embed_text(query)
    fetch_count = min(n_results * 5, total_in_collection)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_count,
            where={"user_id": str(user_id)},
            include=["metadatas", "distances"]
        )
    except Exception as e:
        print(f"❌ ChromaDB query failed: {e}")
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=fetch_count,
                include=["metadatas", "distances"]
            )
        except Exception as e2:
            return []

    if not results["metadatas"] or not results["metadatas"][0]:
        return []

    memories      = []
    seen_snippets = []

    for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
        if str(metadata.get("user_id")) != str(user_id):
            continue

        similarity = round(1 - distance, 3)
        if similarity < 0.25:
            continue

        if topic and topic != "general" and metadata.get("topic") != topic:
            continue

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

    return memories


def _text_overlap(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a), len(words_b))


def get_memory_count(user_id: int) -> int:
    try:
        # Optimized to only pull IDs and not heavy text data
        results = collection.get(where={"user_id": str(user_id)}, include=[])
        return len(results["ids"])
    except Exception:
        return 0