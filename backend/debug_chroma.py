import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

collection = client.get_or_create_collection("personaos_memories")

print("=== ALL STORED MEMORIES ===")
print("Total vectors:", collection.count())
print()

all_data = collection.get(include=["metadatas", "documents"])

for i, (meta, doc) in enumerate(
    zip(all_data["metadatas"], all_data["documents"]), 1
):
    print(f"--- Memory {i} ---")
    print("user_id      :", meta.get("user_id"))
    print("topic        :", meta.get("topic"))
    print("user_message :", meta.get("user_message"))
    print("ai_response  :", str(meta.get("ai_response", ""))[:100])
    print("embedded doc :", str(doc)[:120])
    print()