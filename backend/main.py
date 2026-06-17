# backend/main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone, date, timedelta

import models
import schemas
from database import engine, get_db
from memory_service import store_memory, retrieve_memories, get_memory_count
from groq_service import ask_groq, classify_topic_groq, generate_follow_ups, generate_quiz
from topic_service import update_knowledge_graph, get_knowledge_graph, get_topic_context
from adaptive_engine import calibrate_difficulty, should_generate_quiz, get_due_reviews

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="PersonaOS API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Phase 1-4 Routes (unchanged) ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "PersonaOS API v0.5.0", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {
        "status":    "healthy",
        "timestamp": datetime.now().isoformat(),
        "phase":     "Phase 5 — Adaptive Tutoring"
    }

@app.get("/api/status")
def api_status():
    return {
        "backend":          "online",
        "database":         "SQLite connected",
        "vector_store":     "ChromaDB connected",
        "llm":              "Groq ready",
        "memory_system":    "active",
        "topic_system":     "active",
        "knowledge_graph":  "active",
        "adaptive_engine":  "active",      # ✅ New
        "spaced_repetition":"active",      # ✅ New
        "current_phase":    5,
    }

@app.post("/api/profile", response_model=schemas.UserProfileResponse, status_code=201)
def create_profile(profile_data: schemas.UserProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(models.UserProfile).filter(
        models.UserProfile.name == profile_data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Profile '{profile_data.name}' already exists.")
    new_profile = models.UserProfile(**profile_data.model_dump())
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile

@app.get("/api/profile/{profile_id}", response_model=schemas.UserProfileResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == profile_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.put("/api/profile/{profile_id}", response_model=schemas.UserProfileResponse)
def update_profile(
    profile_id:  int,
    update_data: schemas.UserProfileUpdate,
    db:          Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == profile_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile

@app.get("/api/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(models.UserProfile).all()
    return {"count": len(profiles), "profiles": [
        {"id": p.id, "name": p.name, "level": p.experience_level}
        for p in profiles
    ]}

@app.get("/api/knowledge/{user_id}", response_model=schemas.KnowledgeGraphResponse)
def knowledge_graph(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    graph = get_knowledge_graph(user_id, db)
    return schemas.KnowledgeGraphResponse(**graph)

@app.get("/api/knowledge/{user_id}/topic/{topic}")
def topic_detail(user_id: int, topic: str, db: Session = Depends(get_db)):
    knowledge = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id,
        models.TopicKnowledge.topic   == topic
    ).first()
    if not knowledge:
        raise HTTPException(status_code=404, detail=f"No knowledge found for '{topic}'")
    recent = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.user_id == user_id,
            models.Conversation.topic   == topic
        )
        .order_by(models.Conversation.created_at.desc())
        .limit(3).all()
    )
    return schemas.TopicStatsResponse(
        topic=topic,
        encounter_count=knowledge.encounter_count,
        confidence_score=knowledge.confidence_score,
        recent_questions=[c.user_message for c in recent]
    )

@app.get("/api/memory/stats/{user_id}")
def memory_stats(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    total = db.query(models.Conversation).filter(
        models.Conversation.user_id == user_id
    ).count()
    return {
        "user_id":             user_id,
        "total_conversations": total,
        "vectors_stored":      get_memory_count(user_id),
        "memory_active":       True
    }

@app.get("/api/chat/history/{user_id}")
def get_chat_history(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user_id)
        .order_by(models.Conversation.created_at.desc())
        .limit(limit).all()
    )
    conversations = list(reversed(conversations))
    return {
        "user_id":       user_id,
        "count":         len(conversations),
        "conversations": [
            {
                "id":           c.id,
                "user_message": c.user_message,
                "ai_response":  c.ai_response,
                "topic":        c.topic,
                "created_at":   c.created_at.isoformat()
            }
            for c in conversations
        ]
    }


# ── Phase 5 Routes ────────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """
    Phase 5 chat flow:
    1.  Validate user
    2.  Get knowledge context
    3.  Retrieve memories
    4.  Calibrate difficulty for detected topic
    5.  Call Groq with difficulty injected
    6.  Classify topic
    7.  Save to SQLite
    8.  Update knowledge graph + spaced repetition
    9.  Save to ChromaDB
    10. Generate follow-up suggestions
    11. Maybe generate a quiz
    12. Return everything
    """

    # Step 1 — Validate user
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == request.user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Step 2 — Knowledge context
    knowledge_context = get_topic_context(request.user_id, db)

    # Step 3 — Retrieve memories
    memories = retrieve_memories(
        user_id=request.user_id,
        query=request.message,
        n_results=3
    )

    # Step 4 — Pre-classify topic for difficulty calibration
    # We do a quick keyword-based pre-classification before the full response
    # Full classification happens after (with the AI response for better accuracy)
    from topic_service import _normalise_topic
    pre_topic   = _normalise_topic(request.message)
    difficulty  = calibrate_difficulty(request.user_id, pre_topic, db)
    print(f"🎯 Difficulty: topic='{pre_topic}' level='{difficulty['level']}'")

    # Step 5 — Call Groq
    profile_dict = {
        "name":               profile.name,
        "background":         profile.background,
        "experience_level":   profile.experience_level,
        "preferred_language": profile.preferred_language,
        "learning_goals":     profile.learning_goals,
    }

    try:
        ai_response = ask_groq(
            user_message=request.message,
            profile=profile_dict,
            memories=memories,
            knowledge_context=knowledge_context,
            difficulty=difficulty
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI error: {str(e)}")

    # Step 6 — Classify topic (accurate, uses full AI response)
    topic = classify_topic_groq(request.message, ai_response)

    # Step 7 — Save conversation
    conversation = models.Conversation(
        user_id=request.user_id,
        user_message=request.message,
        ai_response=ai_response,
        topic=topic
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Step 8 — Update knowledge graph + spaced repetition
    update_knowledge_graph(request.user_id, topic, db)

    # Step 9 — Save to ChromaDB
    memory_id = store_memory(
        user_id=request.user_id,
        user_message=request.message,
        ai_response=ai_response,
        topic=topic
    )
    conversation.memory_id = memory_id
    db.commit()

    # Update learning streak
    try:
        today       = date.today()
        last_active = profile.last_active_date
        if last_active != today:
            if last_active == today - timedelta(days=1):
                profile.current_streak = (profile.current_streak or 0) + 1
            elif last_active is None or last_active < today - timedelta(days=1):
                profile.current_streak = 1
            if (profile.current_streak or 0) > (profile.longest_streak or 0):
                profile.longest_streak = profile.current_streak
            profile.last_active_date = today
            db.commit()
    except Exception as e:
        print(f"⚠️ Streak update failed: {e}")


    # Step 10 — Generate follow-up suggestions
    follow_ups = generate_follow_ups(
        topic=topic,
        user_message=request.message,
        ai_response=ai_response,
        level=difficulty["level"]
    )

    # Step 11 — Maybe generate quiz
    quiz_data = None
    if should_generate_quiz(request.user_id, topic, db):
        print(f"📝 Generating quiz for topic='{topic}'")
        raw_quiz = generate_quiz(
            topic=topic,
            ai_response=ai_response,
            level=difficulty["level"],
            language=profile.preferred_language
        )
        if raw_quiz:
            # Save quiz to DB
            quiz_record = models.QuizRecord(
                user_id        = request.user_id,
                topic          = topic,
                question       = raw_quiz["question"],
                option_a       = raw_quiz["option_a"],
                option_b       = raw_quiz["option_b"],
                option_c       = raw_quiz["option_c"],
                option_d       = raw_quiz["option_d"],
                correct_option = raw_quiz["correct_option"].upper(),
                explanation    = raw_quiz["explanation"]
            )
            db.add(quiz_record)
            db.commit()
            db.refresh(quiz_record)

            quiz_data = {
                "quiz_id":  quiz_record.id,
                "topic":    topic,
                "question": quiz_record.question,
                "option_a": quiz_record.option_a,
                "option_b": quiz_record.option_b,
                "option_c": quiz_record.option_c,
                "option_d": quiz_record.option_d,
            }

    # Step 12 — Return
    return schemas.ChatResponse(
        ai_response=ai_response,
        memories_used=[schemas.MemoryItem(**{
            k: v for k, v in m.items()
            if k in ["user_message", "ai_response", "similarity", "created_at"]
        }) for m in memories],
        conversation_id=conversation.id,
        topic=topic,
        follow_ups=follow_ups,
        quiz=quiz_data
    )


@app.post("/api/quiz/answer", response_model=schemas.QuizAnswerResponse)
def submit_quiz_answer(
    request: schemas.QuizAnswerRequest,
    db:      Session = Depends(get_db)
):
    """
    Evaluates the user's answer to a quiz question.
    Updates the quiz record and adjusts confidence score.
    """
    quiz = db.query(models.QuizRecord).filter(
        models.QuizRecord.id == request.quiz_id
    ).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    is_correct = request.user_answer.upper() == quiz.correct_option.upper()

    # Record the answer
    quiz.user_answer  = request.user_answer.upper()
    quiz.is_correct   = is_correct
    quiz.answered_at  = datetime.now(timezone.utc)
    db.commit()

    # Adjust confidence score based on answer
    knowledge = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == quiz.user_id,
        models.TopicKnowledge.topic   == quiz.topic
    ).first()

    new_confidence = knowledge.confidence_score if knowledge else 0.1
    if knowledge:
        if is_correct:
            # Correct answer → boost confidence slightly
            knowledge.confidence_score = min(knowledge.confidence_score + 0.05, 1.0)
        else:
            # Wrong answer → reduce confidence slightly
            knowledge.confidence_score = max(knowledge.confidence_score - 0.05, 0.0)
        db.commit()
        new_confidence = knowledge.confidence_score

    return schemas.QuizAnswerResponse(
        is_correct=is_correct,
        correct_option=quiz.correct_option,
        explanation=quiz.explanation,
        new_confidence=round(new_confidence, 2)
    )


@app.get("/api/reviews/{user_id}", response_model=schemas.ReviewResponse)
def get_reviews(user_id: int, db: Session = Depends(get_db)):
    """
    Returns topics due for spaced repetition review.
    Called when the user opens the app.
    """
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    due = get_due_reviews(user_id, db)
    return schemas.ReviewResponse(
        user_id=user_id,
        due_reviews=[schemas.ReviewItem(**item) for item in due],
        total_due=len(due)
    )


# ── Phase 6 Routes ────────────────────────────────────────────────────────────

@app.get("/api/analytics/{user_id}", response_model=schemas.AnalyticsResponse)
def get_analytics(user_id: int, db: Session = Depends(get_db)):
    """
    Builds the full analytics payload for the dashboard.
    Aggregates data from UserProfile, Conversation, TopicKnowledge, QuizRecord.
    """
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # ── Basic counts ──────────────────────────────────────────────────────────
    total_sessions = db.query(models.Conversation).filter(
        models.Conversation.user_id == user_id
    ).count()

    topics = db.query(models.TopicKnowledge).filter(
        models.TopicKnowledge.user_id == user_id
    ).order_by(models.TopicKnowledge.encounter_count.desc()).all()

    # ── Quiz stats ────────────────────────────────────────────────────────────
    all_quizzes = db.query(models.QuizRecord).filter(
        models.QuizRecord.user_id    == user_id,
        models.QuizRecord.user_answer != None    # Only answered quizzes
    ).all()

    quiz_total   = len(all_quizzes)
    quiz_correct = sum(1 for q in all_quizzes if q.is_correct)
    quiz_accuracy = round(quiz_correct / quiz_total * 100, 1) if quiz_total > 0 else 0.0

    # ── Topic distribution ────────────────────────────────────────────────────
    topic_distribution = [
        schemas.TopicDistribution(
            topic=t.topic,
            sessions=t.encounter_count,
            confidence=round(t.confidence_score, 2)
        )
        for t in topics if t.topic != "general"
    ]

    # ── Quiz performance per topic ────────────────────────────────────────────
    quiz_by_topic = {}
    for q in all_quizzes:
        if q.topic not in quiz_by_topic:
            quiz_by_topic[q.topic] = {"total": 0, "correct": 0}
        quiz_by_topic[q.topic]["total"]   += 1
        quiz_by_topic[q.topic]["correct"] += 1 if q.is_correct else 0

    quiz_performance = [
        schemas.QuizPerformance(
            topic=topic,
            total=data["total"],
            correct=data["correct"],
            accuracy=round(data["correct"] / data["total"] * 100, 1)
        )
        for topic, data in quiz_by_topic.items()
    ]

    # ── Most active + weakest topic ───────────────────────────────────────────
    most_active = topics[0].topic if topics else None
    weakest     = None
    if quiz_performance:
        weakest = min(quiz_performance, key=lambda x: x.accuracy).topic

    # ── Days since start ──────────────────────────────────────────────────────
    days_since = (datetime.now() - profile.created_at).days if profile.created_at else 0

    return schemas.AnalyticsResponse(
        user_id=user_id,
        user_name=profile.name,
        total_sessions=total_sessions,
        total_topics=len([t for t in topics if t.topic != "general"]),
        current_streak=profile.current_streak or 0,
        longest_streak=profile.longest_streak or 0,
        quiz_total=quiz_total,
        quiz_correct=quiz_correct,
        quiz_accuracy=quiz_accuracy,
        topic_distribution=topic_distribution,
        quiz_performance=quiz_performance,
        most_active_topic=most_active,
        weakest_topic=weakest,
        days_since_start=days_since
    )


@app.post("/api/streak/{user_id}", response_model=schemas.StreakResponse)
def update_streak(user_id: int, db: Session = Depends(get_db)):
    """
    Updates the learning streak for a user.
    Called automatically after each chat message from the frontend.

    Logic:
    - If last_active_date is today → no change (already counted today)
    - If last_active_date is yesterday → increment streak
    - If last_active_date is older (or null) → reset streak to 1
    """
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    today          = date.today()
    last_active    = profile.last_active_date
    is_new_best    = False

    if last_active is None:
        # First ever session
        profile.current_streak = 1
    elif last_active == today:
        # Already active today — no change
        pass
    elif last_active == today - timedelta(days=1):
        # Active yesterday → extend streak
        profile.current_streak = (profile.current_streak or 0) + 1
    else:
        # Gap of 2+ days → reset
        profile.current_streak = 1

    # Update longest streak
    if (profile.current_streak or 0) > (profile.longest_streak or 0):
        profile.longest_streak = profile.current_streak
        is_new_best = True

    profile.last_active_date = today
    db.commit()

    return schemas.StreakResponse(
        current_streak=profile.current_streak,
        longest_streak=profile.longest_streak,
        is_new_best=is_new_best
    )






