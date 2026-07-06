"""Generates CFA sub-lessons via Groq, grounded in RAG context, cached in SQLite."""
import json
from rag_engine import get_groq_response, get_retriever
from progress_tracker import save_lesson, get_lessons

SUB_LESSON_COUNT = 3

LESSON_PROMPT = """You are a CFA Level 1 instructor. Topic: "{topic}".
Using the reference context below, produce exactly {n} sub-lessons that best cover this topic for a beginner.
Reference context:
{context}

Return ONLY valid JSON, a list of {n} objects, each with keys:
"title" (short sub-lesson name), "content" (3-5 paragraph explanation in markdown),
"formulas" (list of key formulas in LaTeX, or empty list).
No prose outside the JSON."""


def _get_context(topic: str) -> str:
    try:
        retriever = get_retriever()
        docs = retriever.invoke(topic)
        return "\n\n".join(d.page_content for d in docs[:4])[:4000]
    except Exception as e:
        return f"(no retrieved context: {e})"


def generate_lessons(topic: str):
    """Returns cached lessons for a topic, generating+caching via Groq if absent."""
    existing = get_lessons(topic)
    if existing:
        return existing

    context = _get_context(topic)
    prompt = LESSON_PROMPT.format(topic=topic, n=SUB_LESSON_COUNT, context=context)
    resp = get_groq_response(
        [{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile", temp=0.4,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        sub_lessons = json.loads(raw)
    except json.JSONDecodeError:
        sub_lessons = [{"title": topic, "content": raw, "formulas": []}]

    for sl in sub_lessons:
        formulas = "\n".join(sl.get("formulas", []))
        save_lesson(topic, sl.get("title", topic), sl.get("content", ""), formulas)

    return get_lessons(topic)
