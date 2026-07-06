"""Generates 5 MCQs per lesson via Groq, stored in SQLite."""
import json
from rag_engine import get_groq_response
from progress_tracker import save_quiz_questions, get_quiz_for_lesson

QUIZ_PROMPT = """You are a CFA Level 1 exam question writer. Based on this lesson, write exactly 5 multiple-choice
questions of mixed difficulty (easy/medium/hard).

Lesson title: {title}
Lesson content: {content}

Return ONLY valid JSON: a list of 5 objects, each with keys:
"question", "options" (list of 4 strings), "answer_index" (0-3, correct option index),
"explanation" (1-2 sentences why it's correct), "difficulty" ("easy"|"medium"|"hard").
No prose outside the JSON."""


def generate_quiz(lesson_id: int, title: str = "", content: str = ""):
    """Returns cached quiz questions for a lesson, generating+caching via Groq if absent."""
    existing = get_quiz_for_lesson(lesson_id)
    if existing:
        return existing

    prompt = QUIZ_PROMPT.format(title=title, content=content[:3000])
    resp = get_groq_response(
        [{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile", temp=0.5,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        questions = json.loads(raw)
        assert isinstance(questions, list) and len(questions) > 0
    except Exception:
        questions = [{
            "question": f"Quiz generation failed for '{title}'. Retry?",
            "options": ["Retry", "Skip", "N/A", "N/A"],
            "answer_index": 0, "explanation": "", "difficulty": "easy",
        }]

    save_quiz_questions(lesson_id, questions)
    return get_quiz_for_lesson(lesson_id)
