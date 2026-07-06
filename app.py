"""CFA Level 1 AI Tutor - Duolingo-style Streamlit app. Run: streamlit run app.py"""
import streamlit as st

from scraper import TOPICS
from rag_engine import get_agent
from lesson_generator import generate_lessons
from quiz_generator import generate_quiz
from progress_tracker import (
    get_or_create_user, get_stats, mark_lesson_complete, record_quiz_answer,
    save_chat_message, get_chat_history, LEVELS,
)
from definition_popup import render_definition_popup

st.set_page_config(page_title="CFA Level 1 AI Tutor", page_icon="🎓", layout="wide")

CFA_BLUE = "#1a3c5e"
CFA_GOLD = "#c9a84c"

st.markdown(f"""
<style>
.stApp {{ background-color: #0e1a26; color: #f0f0f0; }}
section[data-testid="stSidebar"] {{ background-color: {CFA_BLUE}; }}
h1, h2, h3 {{ color: {CFA_GOLD}; }}
.stButton>button {{ background-color: {CFA_GOLD}; color: {CFA_BLUE}; border: none; font-weight: 600; }}
div[data-testid="stMetricValue"] {{ color: {CFA_GOLD}; }}
</style>
""", unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = get_or_create_user("default_user")
USER_ID = st.session_state.user_id


def render_sidebar():
    stats = get_stats(USER_ID)
    with st.sidebar:
        st.markdown("## 🎓 CFA Tutor")
        st.metric("🔥 Streak", f"{stats['streak']} days")
        st.metric("⭐ XP", stats["xp"])
        st.markdown(f"**Level:** {stats['level']}")
        next_thresh = next((t for t, n in LEVELS if t > stats["xp"]), None)
        if next_thresh:
            st.progress(min(stats["xp"] / next_thresh, 1.0))
            st.caption(f"{next_thresh - stats['xp']} XP to next level")
        st.divider()
        st.caption(f"✅ Lessons completed: {stats['lessons_completed']}")
        if stats["quiz_total"]:
            st.caption(f"🎯 Quiz accuracy: {round(100*stats['quiz_correct']/stats['quiz_total'])}%")
    render_definition_popup()


def learn_page():
    st.title("📘 Learn")
    topic = st.selectbox("Choose a CFA topic", TOPICS)
    with st.spinner(f"Loading lessons for {topic}..."):
        lessons = generate_lessons(topic)

    for lesson in lessons:
        lid, _, title, content, formulas, completed, _ = lesson
        with st.expander(f"{'✅' if completed else '📖'} {title}", expanded=not completed):
            st.markdown(content)
            if formulas:
                st.markdown("**Key Formulas:**")
                for f in formulas.split("\n"):
                    if f.strip():
                        st.latex(f.strip())
            if not completed:
                if st.button("Mark Complete (+10 XP)", key=f"complete_{lid}"):
                    mark_lesson_complete(lid, USER_ID)
                    st.success("Lesson complete! +10 XP")
                    st.rerun()


def quiz_page():
    st.title("🎯 Quiz")
    topic = st.selectbox("Topic", TOPICS, key="quiz_topic")
    lessons = generate_lessons(topic)
    titles = [l[2] for l in lessons]
    if not titles:
        st.info("No lessons yet for this topic — visit Learn first.")
        return
    choice = st.selectbox("Lesson", titles)
    lesson = next(l for l in lessons if l[2] == choice)
    lesson_id, _, title, content, *_ = lesson

    with st.spinner("Preparing quiz..."):
        questions = generate_quiz(lesson_id, title, content)

    import json
    for q in questions:
        qid, _, question, options_json, answer_idx, explanation, difficulty = q
        options = json.loads(options_json)
        st.markdown(f"**{question}**  \n*Difficulty: {difficulty}*")
        key = f"quiz_{qid}"
        selected = st.radio("Select an answer", options, key=key, index=None)
        if selected is not None:
            sel_idx = options.index(selected)
            answered_key = f"answered_{qid}"
            if not st.session_state.get(answered_key):
                correct = sel_idx == answer_idx
                st.session_state[answered_key] = True
                xp, level, streak = record_quiz_answer(qid, USER_ID, sel_idx, correct)
                if correct:
                    st.success(f"Correct! +10 XP  |  {explanation}")
                else:
                    st.error(f"Incorrect. Correct answer: {options[answer_idx]}  |  {explanation}")
        st.divider()


def chat_page():
    st.title("💬 Chat with your CFA Tutor")
    st.caption("Ask anything. Answers are grounded in CFA notes, with web search fallback.")

    history = get_chat_history(USER_ID)
    for role, content in history:
        with st.chat_message(role):
            st.markdown(content)

    if prompt := st.chat_input("Ask a CFA Level 1 question..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        save_chat_message(USER_ID, "user", prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                agent = get_agent()
                try:
                    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
                    answer = result["messages"][-1].content
                except Exception as e:
                    answer = f"Error: {e}"
            st.markdown(answer)
        save_chat_message(USER_ID, "assistant", answer)


def progress_page():
    st.title("📊 Progress")
    stats = get_stats(USER_ID)
    col1, col2, col3 = st.columns(3)
    col1.metric("⭐ Total XP", stats["xp"])
    col2.metric("🔥 Streak", f"{stats['streak']} days")
    col3.metric("🏅 Level", stats["level"])

    st.subheader("Badges")
    badges = []
    if stats["lessons_completed"] >= 1:
        badges.append("🥉 First Lesson")
    if stats["lessons_completed"] >= 10:
        badges.append("📚 Bookworm (10 lessons)")
    if stats["streak"] >= 5:
        badges.append("🔥 5-Day Streak")
    if stats["quiz_total"] >= 10 and stats["quiz_correct"] / max(stats["quiz_total"], 1) > 0.8:
        badges.append("🎯 Quiz Sharpshooter")
    if badges:
        st.write(" ".join(badges))
    else:
        st.caption("Complete lessons and quizzes to earn badges!")

    st.subheader("Quiz Accuracy")
    if stats["quiz_total"]:
        st.progress(stats["quiz_correct"] / stats["quiz_total"])
        st.caption(f"{stats['quiz_correct']} / {stats['quiz_total']} correct")
    else:
        st.caption("No quizzes attempted yet.")


render_sidebar()

pg = st.navigation([
    st.Page(learn_page, title="Learn", icon="📘", default=True),
    st.Page(quiz_page, title="Quiz", icon="🎯"),
    st.Page(chat_page, title="Chat", icon="💬"),
    st.Page(progress_page, title="Progress", icon="📊"),
])
pg.run()