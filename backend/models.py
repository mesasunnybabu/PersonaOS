# backend/models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id                 = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name               = Column(String, nullable=False)
    background         = Column(String, nullable=False)
    experience_level   = Column(String, nullable=False)
    learning_goals     = Column(Text, nullable=True)
    preferred_language = Column(String, default="Python")

    # ✅ Phase 6: Streak tracking
    current_streak     = Column(Integer, default=0)
    longest_streak     = Column(Integer, default=0)
    last_active_date   = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversations   = relationship("Conversation",   back_populates="user")
    topic_knowledge = relationship("TopicKnowledge", back_populates="user")
    quiz_records    = relationship("QuizRecord",     back_populates="user")

    def __repr__(self):
        return f"<UserProfile id={self.id} name={self.name}>"


class Conversation(Base):
    __tablename__ = "conversations"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    ai_response  = Column(Text, nullable=False)
    memory_id    = Column(String, nullable=True)
    topic        = Column(String, nullable=True, index=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserProfile", back_populates="conversations")


class TopicKnowledge(Base):
    __tablename__ = "topic_knowledge"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    topic            = Column(String, nullable=False, index=True)
    encounter_count  = Column(Integer, default=1)
    confidence_score = Column(Float, default=0.1)
    review_interval  = Column(Integer, default=1)
    next_review_at   = Column(DateTime(timezone=True), nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    first_seen       = Column(DateTime(timezone=True), server_default=func.now())
    last_seen        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserProfile", back_populates="topic_knowledge")


class QuizRecord(Base):
    __tablename__ = "quiz_records"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    user_id        = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    topic          = Column(String, nullable=False)
    question       = Column(Text, nullable=False)
    option_a       = Column(Text, nullable=False)
    option_b       = Column(Text, nullable=False)
    option_c       = Column(Text, nullable=False)
    option_d       = Column(Text, nullable=False)
    correct_option = Column(String, nullable=False)
    explanation    = Column(Text, nullable=False)
    user_answer    = Column(String, nullable=True)
    is_correct     = Column(Boolean, nullable=True)
    answered_at    = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserProfile", back_populates="quiz_records")