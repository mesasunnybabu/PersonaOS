# backend/topic_service.py

from sqlalchemy.orm import Session
import models

# ── Topic Taxonomy ────────────────────────────────────────────────────────────
# All lowercase internally — we normalise everything before comparing

VALID_TOPICS = [
    "variables",
    "loops",
    "functions",
    "recursion",
    "oop",
    "data-structures",
    "algorithms",
    "debugging",
    "modules",
    "file-handling",
    "apis",
    "databases",
    "error-handling",
    "decorators",
    "async",
    "testing",
    "general",
]

# Aliases — maps what Groq might return → our canonical topic name
# This is the key fix: handles "oops", "object oriented", "classes" etc.
TOPIC_ALIASES = {
    "oops":                  "oop",
    "oop":                   "oop",
    "object oriented":       "oop",
    "object-oriented":       "oop",
    "classes":               "oop",
    "class":                 "oop",
    "inheritance":           "oop",
    "polymorphism":          "oop",
    "encapsulation":         "oop",
    "abstraction":           "oop",
    "loop":                  "loops",
    "iteration":             "loops",
    "for loop":              "loops",
    "while loop":            "loops",
    "function":              "functions",
    "method":                "functions",
    "methods":               "functions",
    "def":                   "functions",
    "lambda":                "functions",
    "recursive":             "recursion",
    "data structure":        "data-structures",
    "data structures":       "data-structures",
    "list":                  "data-structures",
    "dictionary":            "data-structures",
    "dict":                  "data-structures",
    "stack":                 "data-structures",
    "queue":                 "data-structures",
    "tree":                  "data-structures",
    "algorithm":             "algorithms",
    "sorting":               "algorithms",
    "searching":             "algorithms",
    "error":                 "error-handling",
    "exception":             "error-handling",
    "exceptions":            "error-handling",
    "try except":            "error-handling",
    "try/except":            "error-handling",
    "decorator":             "decorators",
    "async await":           "async",
    "asynchronous":          "async",
    "coroutine":             "async",
    "api":                   "apis",
    "rest api":              "apis",
    "requests":              "apis",
    "database":              "databases",
    "sql":                   "databases",
    "sqlite":                "databases",
    "test":                  "testing",
    "unit test":             "testing",
    "pytest":                "testing",
    "import":                "modules",
    "module":                "modules",
    "package":               "modules",
    "file":                  "file-handling",
    "files":                 "file-handling",
    "read file":             "file-handling",
    "write file":            "file-handling",
    "variable":              "variables",
    "debug":                 "debugging",
    "breakpoint":            "debugging",
}

LEARNING_PATH = {
    "variables":       "loops",
    "loops":           "functions",
    "functions":       "recursion",
    "recursion":       "data-structures",
    "data-structures": "algorithms",
    "algorithms":      "oop",
    "oop":             "modules",
    "modules":         "error-handling",
    "error-handling":  "apis",
    "apis":            "databases",
    "databases":       "testing",
    "testing":         "async",
    "debugging":       "error-handling",
    "decorators":      "async",
    "file-handling":   "databases",
    "async":           "testing",
    "general":         "variables",
}


def _normalise_topic(raw: str) -> str:
    """
    Converts any raw string from Groq into a canonical topic name.
    Steps:
      1. Lowercase and strip whitespace
      2. Check alias map (handles oops, inheritance, classes, etc.)
      3. Check if it's already a valid topic
      4. Try partial match against valid topics
      5. Fall back to "general"
    """
    cleaned = raw.strip().lower()

    # Step 1: Direct alias match (most common case)
    if cleaned in TOPIC_ALIASES:
        return TOPIC_ALIASES[cleaned]

    # Step 2: Already a valid topic (e.g. "loops", "functions")
    if cleaned in VALID_TOPICS:
        return cleaned

    # Step 3: Check if any alias key is contained in the raw response
    for alias, canonical in TOPIC_ALIASES.items():
        if alias in cleaned:
            return canonical

    # Step 4: Partial match against valid topic names
    for topic in VALID_TOPICS:
        if topic in cleaned or cleaned in topic:
            return topic

    # Step 5: Give up
    return "general"


def classify_topic(user_message: str, ai_response: str, groq_client) -> str:
    """
    Uses Groq to classify a conversation into one topic.
    Fixed: all-lowercase topic list in prompt, robust normalisation.
    """

    # Prompt uses lowercase topics to match what Groq naturally returns
    topics_str = ", ".join(VALID_TOPICS)

    classification_prompt = f"""You are a topic classifier for a Python coding tutor.

Classify the conversation below into exactly ONE topic from this list:
{topics_str}

Important rules:
- If the conversation is about classes, inheritance, polymorphism, or object-oriented programming, return: oop
- If about for/while loops or iteration, return: loops
- If about def/functions/methods/lambda, return: functions
- If about exceptions/try/except, return: error-handling
- Return ONLY the topic word or hyphenated-phrase, nothing else
- No punctuation, no capitals, no explanation

Conversation:
Student: {user_message[:400]}
Tutor: {ai_response[:400]}

Topic:"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": classification_prompt}],
            temperature=0.0,
            max_tokens=15,
        )
        raw = response.choices[0].message.content.strip()
        result = _normalise_topic(raw)
        print(f"🏷️  Topic classified: '{raw}' → '{result}'")   # Debug log
        return result

    except Exception as e:
        print(f"⚠️  Topic classification failed: {e}")
        return "general"


def update_knowledge_graph(user_id: int, topic: str, db: Session) -> None:
    """Updated to trigger spaced repetition scheduling."""
    from adaptive_engine import update_spaced_repetition

    existing = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id,
        models.TopicKnowledge.topic   == topic
    ).first()

    if existing:
        existing.encounter_count  += 1
        existing.confidence_score  = min(existing.encounter_count / 10.0, 1.0)
    else:
        db.add(models.TopicKnowledge(
            user_id          = user_id,
            topic            = topic,
            encounter_count  = 1,
            confidence_score = 0.1
        ))
    db.commit()

    # Schedule spaced repetition review
    update_spaced_repetition(user_id, topic, db)


def get_knowledge_graph(user_id: int, db: Session) -> dict:
    topics = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id
    ).order_by(models.TopicKnowledge.encounter_count.desc()).all()

    total_conversations = db.query(models.Conversation).filter(
        models.Conversation.user_id == user_id
    ).count()

    profile  = db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    strongest = topics[0].topic if topics else None
    suggested = LEARNING_PATH.get(strongest, "variables") if strongest else "variables"

    return {
        "user_id":         user_id,
        "user_name":       profile.name if profile else "Unknown",
        "total_topics":    len(topics),
        "total_sessions":  total_conversations,
        "topics":          topics,
        "strongest_topic": strongest,
        "suggested_next":  suggested,
    }


def get_topic_context(user_id: int, db: Session) -> str:
    topics = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id
    ).order_by(models.TopicKnowledge.encounter_count.desc()).all()

    if not topics:
        return "No learning history yet."

    strong = [t for t in topics if t.confidence_score >= 0.5]
    weak   = [t for t in topics if t.confidence_score <  0.5]
    lines  = []

    if strong:
        lines.append("Strong topics: " + ", ".join(
            f"{t.topic} ({t.encounter_count}x)" for t in strong[:3]
        ))
    if weak:
        lines.append("Still exploring: " + ", ".join(t.topic for t in weak[:3]))

    return " | ".join(lines)