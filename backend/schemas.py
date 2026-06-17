# backend/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Phase 2 Schemas ───────────────────────────────────────────────────────────

class UserProfileCreate(BaseModel):
    name:               str           = Field(..., min_length=2, max_length=50)
    background:         str           = Field(..., min_length=2, max_length=100)
    experience_level:   str           = Field(...)
    learning_goals:     Optional[str] = Field(default=None, max_length=500)
    preferred_language: Optional[str] = Field(default="Python")

class UserProfileUpdate(BaseModel):
    name:               Optional[str] = Field(default=None, min_length=2, max_length=50)
    background:         Optional[str] = Field(default=None, max_length=100)
    experience_level:   Optional[str] = Field(default=None)
    learning_goals:     Optional[str] = Field(default=None, max_length=500)
    preferred_language: Optional[str] = Field(default=None)

class UserProfileResponse(BaseModel):
    id:                 int
    name:               str
    background:         str
    experience_level:   str
    learning_goals:     Optional[str]
    preferred_language: str
    created_at:         datetime
    updated_at:         datetime
    class Config:
        from_attributes = True


# ── Phase 3 Schemas ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: int = Field(...)
    message: str = Field(..., min_length=1, max_length=2000)

class MemoryItem(BaseModel):
    user_message: str
    ai_response:  str
    similarity:   float
    created_at:   str

class ChatResponse(BaseModel):
    ai_response:     str
    memories_used:   List[MemoryItem]
    conversation_id: int
    topic:           str
    # Phase 5 additions
    follow_ups:      List[str] = []        # Suggested next questions
    quiz:            Optional[dict] = None  # Quiz question if generated

class ConversationResponse(BaseModel):
    id:           int
    user_message: str
    ai_response:  str
    topic:        Optional[str]
    created_at:   datetime
    class Config:
        from_attributes = True


# ── Phase 4 Schemas ───────────────────────────────────────────────────────────

class TopicKnowledgeItem(BaseModel):
    topic:            str
    encounter_count:  int
    confidence_score: float
    last_seen:        datetime
    next_review_at:   Optional[datetime] = None   # ✅ New
    class Config:
        from_attributes = True

class KnowledgeGraphResponse(BaseModel):
    user_id:          int
    user_name:        str
    total_topics:     int
    total_sessions:   int
    topics:           List[TopicKnowledgeItem]
    strongest_topic:  Optional[str]
    suggested_next:   Optional[str]

class TopicStatsResponse(BaseModel):
    topic:            str
    encounter_count:  int
    confidence_score: float
    recent_questions: List[str]


# ── Phase 5 Schemas ───────────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    """A single multiple-choice quiz question."""
    quiz_id:        int
    topic:          str
    question:       str
    option_a:       str
    option_b:       str
    option_c:       str
    option_d:       str

class QuizAnswerRequest(BaseModel):
    """Sent by React when user selects an answer."""
    quiz_id:     int
    user_answer: str = Field(..., description="A, B, C, or D")

class QuizAnswerResponse(BaseModel):
    """Sent back after evaluating the answer."""
    is_correct:     bool
    correct_option: str
    explanation:    str
    new_confidence: float   # Updated confidence score after answering

class ReviewItem(BaseModel):
    """A topic that is due for spaced repetition review."""
    topic:           str
    last_seen:       datetime
    encounter_count: int
    days_overdue:    int

class ReviewResponse(BaseModel):
    """List of topics due for review."""
    user_id:      int
    due_reviews:  List[ReviewItem]
    total_due:    int

class DifficultyLevel(BaseModel):
    """Computed difficulty calibration for a topic."""
    topic:          str
    level:          str    # novice / learning / familiar / confident
    score:          float
    instruction:    str    # What to tell the AI about depth


# ── Phase 6 Schemas ───────────────────────────────────────────────────────────

class TopicDistribution(BaseModel):
    """One bar in the topic distribution chart."""
    topic:           str
    sessions:        int
    confidence:      float


class QuizPerformance(BaseModel):
    """One data point in the quiz accuracy chart."""
    topic:           str
    total:           int
    correct:         int
    accuracy:        float


class AnalyticsResponse(BaseModel):
    """
    Full analytics payload for the dashboard.
    Returned by GET /api/analytics/{user_id}
    """
    user_id:              int
    user_name:            str
    total_sessions:       int
    total_topics:         int
    current_streak:       int
    longest_streak:       int
    quiz_total:           int
    quiz_correct:         int
    quiz_accuracy:        float
    topic_distribution:   List[TopicDistribution]
    quiz_performance:     List[QuizPerformance]
    most_active_topic:    Optional[str]
    weakest_topic:        Optional[str]      # Lowest quiz accuracy
    days_since_start:     int


class StreakResponse(BaseModel):
    """Returned after updating the streak."""
    current_streak:  int
    longest_streak:  int
    is_new_best:     bool
