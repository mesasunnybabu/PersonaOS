# backend/evaluation/build_testset.py
#
# PURPOSE: Builds an evaluation test set from your REAL conversation history
# in SQLite. We don't use synthetic data — we use what you actually asked
# PersonaOS, because that's what we actually need to measure.
#
# For each conversation, we need a "ground truth" — what the correct
# context/answer SHOULD have been. Since you don't have human-labeled
# ground truth, we use a practical approach:
#   - "question"           -> the real user_message
#   - "ground_truth"       -> the actual ai_response that was given (treated
#                              as the reference answer for faithfulness/relevancy)
#   - "contexts" (retrieved) -> we re-run retrieve_memories() live to get
#                              CURRENT retrieval behaviour (not what was
#                              retrieved historically, since that may have
#                              been buggy at the time)
#
# This lets us measure: given today's fixed retrieval code, how good is it
# at finding the right past memories and producing faithful answers?

import sys
import os
import json

# Add backend/ to path so we can import your actual modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal
import models
from memory_service import retrieve_memories


def build_testset(user_id: int, min_topic_count: int = 2, max_samples: int = 25):
    """
    Pulls conversations from SQLite for a given user and builds
    a RAGAS-compatible test set.

    Filters:
    - Skips topic == "general" (too vague to evaluate retrieval against)
    - Only includes topics the user asked about more than once
      (so there's actually something for retrieval to find)
    - Skips the FIRST occurrence of each topic (no prior memory could
      exist yet, so retrieval SHOULD return nothing — not a useful test row)
    """

    db = SessionLocal()

    conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user_id)
        .order_by(models.Conversation.created_at.asc())
        .all()
    )

    if not conversations:
        print(f"⚠️  No conversations found for user_id={user_id}")
        db.close()
        return []

    print(f"📚 Found {len(conversations)} total conversations for user_id={user_id}")

    # Count how many times each topic appears
    topic_counts = {}
    for c in conversations:
        topic_counts[c.topic] = topic_counts.get(c.topic, 0) + 1

    eligible_topics = {
        t for t, count in topic_counts.items()
        if t != "general" and count >= min_topic_count
    }

    print(f"📊 Topics with {min_topic_count}+ occurrences: {eligible_topics}")

    if not eligible_topics:
        print("⚠️  No topics have enough repeated occurrences for meaningful retrieval testing.")
        print("    Chat about the same topic at least 2-3 times, then re-run this script.")
        db.close()
        return []

    # Track how many times we've seen each topic so we can skip the first occurrence
    seen_topic_count = {}
    testset_rows = []

    for conv in conversations:
        if conv.topic not in eligible_topics:
            continue

        seen_topic_count[conv.topic] = seen_topic_count.get(conv.topic, 0) + 1

        # Skip the first occurrence — no memory could exist yet at that point
        if seen_topic_count[conv.topic] == 1:
            continue

        # Re-run retrieval LIVE using your current (fixed) retrieve_memories()
        retrieved = retrieve_memories(
            user_id=user_id,
            query=conv.user_message,
            n_results=3,
            topic=conv.topic
        )

        retrieved_texts = [
            f"Q: {m['user_message']} A: {m['ai_response']}"
            for m in retrieved
        ]

        testset_rows.append({
            "question":         conv.user_message,
            "ground_truth":     conv.ai_response,   # Treated as reference answer
            "contexts":         retrieved_texts if retrieved_texts else ["NO_CONTEXT_RETRIEVED"],
            "topic":            conv.topic,
            "conversation_id":  conv.id,
        })

        if len(testset_rows) >= max_samples:
            break

    db.close()

    print(f"✅ Built test set with {len(testset_rows)} rows")
    return testset_rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", type=int, default=1, help="User ID to build test set for")
    parser.add_argument("--max_samples", type=int, default=25)
    args = parser.parse_args()

    rows = build_testset(user_id=args.user_id, max_samples=args.max_samples)

    if not rows:
        print("\n❌ Could not build a test set. See warnings above.")
        exit(1)

    # Save to disk so run_evaluation.py can load it without re-querying
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "testset.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Saved test set to: {output_path}")
    print(f"\nSample row:")
    print(json.dumps(rows[0], indent=2)[:500] + "...")