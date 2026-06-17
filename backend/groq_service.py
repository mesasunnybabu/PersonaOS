# backend/groq_service.py

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"


def get_groq_client():
    return client


def build_system_prompt(
    profile:           dict,
    knowledge_context: str  = "",
    difficulty:        dict = None
) -> str:
    """
    System prompt now includes difficulty calibration instructions.
    The AI knows exactly how deep to go based on the student's history.
    """
    base = f"""You are PersonaOS, an adaptive AI coding tutor WITH MEMORY of past conversations.

CRITICAL INSTRUCTION: If you see a section called "## Relevant Past Conversations" \
in the user message, you MUST use it. Never say "this is our first session" \
if past conversations are provided.

## Student Profile
- Name: {profile['name']}
- Background: {profile['background']}
- Experience Level: {profile['experience_level']}
- Preferred Language: {profile['preferred_language']}
- Learning Goals: {profile.get('learning_goals') or 'Not specified'}

## Teaching Style by Level
- beginner: Simple analogies, no jargon, line-by-line comments, short examples
- intermediate: Explain the why, introduce patterns and best practices
- advanced: Concise, trade-offs, edge cases, proper terminology

## Rules
- Always use {profile['preferred_language']} for code examples unless asked otherwise
- Be encouraging and patient
- Use markdown for code blocks
- When past conversations are provided, ALWAYS reference them naturally"""

    if knowledge_context and knowledge_context != "No learning history yet.":
        base += f"""

## Student's Learning History
{knowledge_context}"""

    # Inject difficulty calibration — this is the key Phase 5 addition
    if difficulty:
        base += f"""

## Depth Instruction for This Response
Topic familiarity level: {difficulty['level'].upper()} (score: {difficulty['score']:.1f}/1.0)
{difficulty['instruction']}"""

    return base


def ask_groq(
    user_message:      str,
    profile:           dict,
    memories:          list,
    knowledge_context: str  = "",
    difficulty:        dict = None
) -> str:
    """Updated to accept and inject difficulty calibration."""

    memory_context = ""
    if memories:
        memory_context = "\n\n## Relevant Past Conversations\n"
        memory_context += "IMPORTANT: Use these to answer with continuity.\n\n"
        for i, mem in enumerate(memories, 1):
            memory_context += (
                f"### Past Exchange {i} "
                f"(relevance: {mem['similarity']}, topic: {mem.get('topic','?')})\n"
                f"Student asked: {mem['user_message']}\n"
                f"You explained: {mem['ai_response'][:500]}\n\n"
            )
        print(f"📨 Injecting {len(memories)} memories into prompt.")
    else:
        print("📨 No memories to inject.")

    full_message = (
        f"{memory_context}\n---\n## Current Question\n{user_message}"
        if memory_context else user_message
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role":    "system",
                "content": build_system_prompt(profile, knowledge_context, difficulty)
            },
            {
                "role":    "user",
                "content": full_message
            }
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    return response.choices[0].message.content


def generate_follow_ups(
    topic:        str,
    user_message: str,
    ai_response:  str,
    level:        str
) -> list[str]:
    """
    Generates 3 suggested follow-up questions after an explanation.
    These appear as clickable chips below the AI response.

    Returns a list of 3 question strings, or [] if generation fails.
    """
    prompt = f"""A coding student at {level} level just learned about {topic}.

Their question was: "{user_message}"

Suggest exactly 3 short follow-up questions they should ask next to deepen understanding.
Rules:
- Each question must be on ONE line
- Max 12 words per question
- Make them progressively deeper
- Return ONLY the 3 questions, numbered 1. 2. 3.
- No explanation, no preamble"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
        )
        raw   = response.choices[0].message.content.strip()
        lines = [l.strip() for l in raw.split('\n') if l.strip()]

        # Extract just the question text (remove "1." "2." "3." prefixes)
        questions = []
        for line in lines:
            # Remove numbering like "1." "1)" "1:"
            clean = line.lstrip('0123456789.-) ').strip()
            if clean and len(clean) > 5:
                questions.append(clean)

        return questions[:3]   # Return max 3

    except Exception as e:
        print(f"⚠️  Follow-up generation failed: {e}")
        return []


def generate_quiz(
    topic:       str,
    ai_response: str,
    level:       str,
    language:    str
) -> dict | None:
    """
    Generates a multiple-choice quiz question based on what was just explained.

    Returns a dict with question + 4 options + answer + explanation,
    or None if generation fails.
    """
    prompt = f"""Create ONE multiple-choice quiz question for a {level}-level student \
who just learned about {topic} in {language}.

The question should test understanding of this explanation:
{ai_response[:600]}

Return ONLY valid JSON in exactly this format, no markdown, no extra text:
{{
  "question": "the question text here",
  "option_a": "first option",
  "option_b": "second option",
  "option_c": "third option",
  "option_d": "fourth option",
  "correct_option": "A",
  "explanation": "why this answer is correct"
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,     # Lower temp for structured output
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        quiz_data = json.loads(raw)

        # Validate required fields
        required = ["question", "option_a", "option_b", "option_c",
                    "option_d", "correct_option", "explanation"]
        if all(k in quiz_data for k in required):
            return quiz_data
        return None

    except Exception as e:
        print(f"⚠️  Quiz generation failed: {e}")
        return None


def classify_topic_groq(user_message: str, ai_response: str) -> str:
    from topic_service import classify_topic
    return classify_topic(user_message, ai_response, client)