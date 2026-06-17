# backend/reclassify.py
# Run ONCE to fix existing "general" conversations
# Usage: .\venv\Scripts\python.exe reclassify.py

from database import SessionLocal
from groq_service import get_groq_client
from topic_service import classify_topic, update_knowledge_graph
import models

db = SessionLocal()
client = get_groq_client()

conversations = db.query(models.Conversation).filter(
    models.Conversation.topic == "general"
).all()

print(f"Found {len(conversations)} conversations to reclassify...")

for conv in conversations:
    new_topic = classify_topic(conv.user_message, conv.ai_response, client)
    old_topic = conv.topic
    conv.topic = new_topic
    print(f"  [{conv.id}] '{old_topic}' → '{new_topic}': {conv.user_message[:60]}")

db.commit()
print("✅ Reclassification complete.")

# Rebuild knowledge graph from scratch
users = db.query(models.UserProfile).all()
for user in users:
    # Clear existing knowledge
    db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user.id
    ).delete()
    db.commit()

    # Recount from corrected conversations
    convs = db.query(models.Conversation).filter(
        models.Conversation.user_id == user.id
    ).all()
    for conv in convs:
        update_knowledge_graph(user.id, conv.topic, db)

    print(f"✅ Rebuilt knowledge graph for user {user.name}")

db.close()