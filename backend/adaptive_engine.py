# backend/adaptive_engine.py
#
# PURPOSE: The brain of Phase 5. All adaptive tutoring logic lives here.
# Four responsibilities:
#   1. calibrate_difficulty()   → compute how deep to go on a topic
#   2. should_generate_quiz()   → decide if this response warrants a quiz
#   3. get_due_reviews()        → find topics due for spaced repetition
#   4. update_spaced_rep()      → update review schedule after interaction

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import models

# ── Difficulty Calibration ────────────────────────────────────────────────────

# Maps confidence score ranges to teaching instructions
DIFFICULTY_LEVELS = {
    "novice": {
        "range":       (0.0, 0.2),
        "instruction": (
            "This is a NEW topic for the student. "
            "Start from absolute basics. Use simple real-world analogies. "
            "Avoid jargon. Give one short code example with every line commented. "
            "Check understanding at the end with one simple question."
        )
    },
    "learning": {
        "range":       (0.2, 0.5),
        "instruction": (
            "The student has seen this topic a few times. "
            "Skip the very basics. Focus on the 'why' behind concepts. "
            "Introduce patterns and common use cases. "
            "Give practical examples, not just toy code."
        )
    },
    "familiar": {
        "range":       (0.5, 0.8),
        "instruction": (
            "The student is comfortable with this topic. "
            "Go deeper — discuss edge cases, gotchas, and best practices. "
            "Compare with alternative approaches. "
            "Assume they know the syntax; explain the reasoning."
        )
    },
    "confident": {
        "range":       (0.8, 1.01),
        "instruction": (
            "The student knows this topic well. "
            "Be concise. Discuss advanced nuances, performance trade-offs, "
            "and real-world production considerations. "
            "Treat them as a peer — no hand-holding needed."
        )
    }
}

# Spaced repetition intervals in days: 1 → 3 → 7 → 14 → 30
REVIEW_INTERVALS = [1, 3, 7, 14, 30]


def calibrate_difficulty(user_id: int, topic: str, db: Session) -> dict:
    """
    Looks up the user's knowledge of a topic and returns
    a difficulty level with teaching instructions.

    If the topic is new (no record), returns "novice".
    """
    knowledge = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id,
        models.TopicKnowledge.topic   == topic
    ).first()

    score = knowledge.confidence_score if knowledge else 0.0

    for level_name, level_data in DIFFICULTY_LEVELS.items():
        low, high = level_data["range"]
        if low <= score < high:
            return {
                "topic":       topic,
                "level":       level_name,
                "score":       score,
                "instruction": level_data["instruction"]
            }

    # Fallback
    return {
        "topic":       topic,
        "level":       "novice",
        "score":       0.0,
        "instruction": DIFFICULTY_LEVELS["novice"]["instruction"]
    }


def should_generate_quiz(user_id: int, topic: str, db: Session) -> bool:
    """
    Decides whether to generate a quiz after this response.

    Rules:
    - Only quiz on non-general topics
    - Quiz every 3rd encounter with a topic (not every single message)
    - Don't quiz if the user just answered a quiz (quiz_records check)
    - Never quiz on meta-questions ("what did we discuss", "summarize")
    """
    if topic == "general":
        return False

    knowledge = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id,
        models.TopicKnowledge.topic   == topic
    ).first()

    if not knowledge:
        return False

    # Quiz on 3rd, 6th, 9th... encounter
    return knowledge.encounter_count % 3 == 0


def get_due_reviews(user_id: int, db: Session) -> list:
    """
    Returns topics that are due (or overdue) for spaced repetition review.
    A topic is "due" if next_review_at <= now.
    """
    now = datetime.now(timezone.utc)

    due_topics = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id      == user_id,
        models.TopicKnowledge.next_review_at != None,
        models.TopicKnowledge.next_review_at <= now
    ).order_by(
        models.TopicKnowledge.next_review_at.asc()
    ).all()

    result = []
    for t in due_topics:
        # Calculate how many days overdue
        overdue_delta = now - t.next_review_at.replace(tzinfo=timezone.utc)
        days_overdue  = max(0, overdue_delta.days)

        result.append({
            "topic":           t.topic,
            "last_seen":       t.last_seen,
            "encounter_count": t.encounter_count,
            "days_overdue":    days_overdue
        })

    return result


def update_spaced_repetition(user_id: int, topic: str, db: Session) -> None:
    """
    Updates the spaced repetition schedule for a topic after an encounter.

    First encounter → next review in 1 day
    Subsequent encounters → move to next interval in sequence
    """
    if topic == "general":
        return

    knowledge = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id,
        models.TopicKnowledge.topic   == topic
    ).first()

    if not knowledge:
        return

    now = datetime.now(timezone.utc)

    # Find current interval index
    current_interval = knowledge.review_interval or 1
    try:
        idx = REVIEW_INTERVALS.index(current_interval)
        # Move to next interval, cap at last one
        next_idx     = min(idx + 1, len(REVIEW_INTERVALS) - 1)
        next_interval = REVIEW_INTERVALS[next_idx]
    except ValueError:
        next_interval = 1

    knowledge.review_interval  = next_interval
    knowledge.next_review_at   = now + timedelta(days=next_interval)
    knowledge.last_reviewed_at = now

    db.commit()
    print(f"📅 Spaced rep updated: topic='{topic}' next review in {next_interval} days")