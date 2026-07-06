"""SQLite-backed progress tracking: XP, streaks, levels, lessons, quizzes."""
import sqlite3
import json
from datetime import date, timedelta

DB_PATH = "./cfa_tutor.db"
LEVELS = [(0, "Bronze"), (200, "Silver"), (600, "Gold"), (1500, "Platinum")]


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, xp INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0, last_active TEXT, level TEXT DEFAULT 'Bronze')""")
    c.execute("""CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY, topic TEXT, title TEXT, content TEXT,
        formulas TEXT, completed INTEGER DEFAULT 0, completed_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY, lesson_id INTEGER, question TEXT, options TEXT,
        answer_index INTEGER, explanation TEXT, difficulty TEXT,
        FOREIGN KEY(lesson_id) REFERENCES lessons(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS quiz_answers (
        id INTEGER PRIMARY KEY, quiz_id INTEGER, user_id INTEGER,
        selected_index INTEGER, correct INTEGER, answered_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, content TEXT, ts TEXT)""")
    conn.commit()
    conn.close()


def get_or_create_user(username: str = "default_user") -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    c.execute("INSERT INTO users (username, last_active) VALUES (?, ?)", (username, str(date.today())))
    conn.commit()
    uid = c.lastrowid
    conn.close()
    return uid


def _level_for_xp(xp: int) -> str:
    level = LEVELS[0][1]
    for threshold, name in LEVELS:
        if xp >= threshold:
            level = name
    return level


def add_xp(user_id: int, amount: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT xp FROM users WHERE id=?", (user_id,))
    xp = (c.fetchone() or (0,))[0] + amount
    level = _level_for_xp(xp)
    c.execute("UPDATE users SET xp=?, level=? WHERE id=?", (xp, level, user_id))
    conn.commit()
    conn.close()
    return xp, level


def update_streak(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT streak, last_active FROM users WHERE id=?", (user_id,))
    streak, last_active = c.fetchone()
    today = date.today()
    last = date.fromisoformat(last_active) if last_active else today
    if last == today:
        new_streak = streak or 1
    elif last == today - timedelta(days=1):
        new_streak = (streak or 0) + 1
    else:
        new_streak = 1
    c.execute("UPDATE users SET streak=?, last_active=? WHERE id=?", (new_streak, str(today), user_id))
    conn.commit()
    conn.close()
    return new_streak


def save_lesson(topic: str, title: str, content: str, formulas: str = "") -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM lessons WHERE topic=? AND title=?", (topic, title))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    c.execute("INSERT INTO lessons (topic, title, content, formulas) VALUES (?, ?, ?, ?)",
               (topic, title, content, formulas))
    conn.commit()
    lid = c.lastrowid
    conn.close()
    return lid


def get_lessons(topic: str = None):
    conn = get_conn()
    c = conn.cursor()
    if topic:
        c.execute("SELECT * FROM lessons WHERE topic=?", (topic,))
    else:
        c.execute("SELECT * FROM lessons")
    rows = c.fetchall()
    conn.close()
    return rows


def mark_lesson_complete(lesson_id: int, user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE lessons SET completed=1, completed_at=? WHERE id=?", (str(date.today()), lesson_id))
    conn.commit()
    conn.close()
    xp, level = add_xp(user_id, 10)
    streak = update_streak(user_id)
    if streak % 5 == 0:
        add_xp(user_id, 5)  # streak bonus
    return xp, level, streak


def save_quiz_questions(lesson_id: int, questions: list):
    conn = get_conn()
    c = conn.cursor()
    ids = []
    for q in questions:
        c.execute(
            "INSERT INTO quizzes (lesson_id, question, options, answer_index, explanation, difficulty) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (lesson_id, q["question"], json.dumps(q["options"]), q["answer_index"],
             q.get("explanation", ""), q.get("difficulty", "medium")),
        )
        ids.append(c.lastrowid)
    conn.commit()
    conn.close()
    return ids


def get_quiz_for_lesson(lesson_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM quizzes WHERE lesson_id=?", (lesson_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def record_quiz_answer(quiz_id: int, user_id: int, selected_index: int, correct: bool):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO quiz_answers (quiz_id, user_id, selected_index, correct, answered_at) VALUES (?,?,?,?,?)",
              (quiz_id, user_id, selected_index, int(correct), str(date.today())))
    conn.commit()
    conn.close()
    if correct:
        xp, level = add_xp(user_id, 10)
        streak = update_streak(user_id)
        return xp, level, streak
    return None, None, None


def save_chat_message(user_id: int, role: str, content: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, role, content, ts) VALUES (?,?,?,?)",
              (user_id, role, content, str(date.today())))
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, limit: int = 50):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id ASC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def get_stats(user_id: int) -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT xp, streak, level FROM users WHERE id=?", (user_id,))
    xp, streak, level = c.fetchone()
    c.execute("SELECT COUNT(*) FROM lessons WHERE completed=1")
    completed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM quiz_answers WHERE user_id=? AND correct=1", (user_id,))
    correct = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM quiz_answers WHERE user_id=?", (user_id,))
    total = c.fetchone()[0]
    conn.close()
    return {
        "xp": xp, "streak": streak, "level": level,
        "lessons_completed": completed, "quiz_correct": correct, "quiz_total": total,
    }


init_db()
