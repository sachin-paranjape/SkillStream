import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

from config import DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            difficulty TEXT,
            question_text TEXT,
            selected_option TEXT,
            selected_option_text TEXT,
            correct_option TEXT,
            correct_option_text TEXT,
            explanation_text TEXT,
            is_correct INTEGER NOT NULL,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """
    )
    cursor.execute("PRAGMA table_info(submissions)")
    columns = [row[1] for row in cursor.fetchall()]
    if "difficulty" not in columns:
        cursor.execute("ALTER TABLE submissions ADD COLUMN difficulty TEXT")
    if "explanation_text" not in columns:
        cursor.execute("ALTER TABLE submissions ADD COLUMN explanation_text TEXT")
    conn.commit()
    conn.close()


def upsert_user(user_id: int, user_name: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (user_id, user_name, created_at) VALUES (?, ?, ?)",
            (user_id, user_name, datetime.utcnow().isoformat()),
        )
    else:
        cursor.execute(
            "UPDATE users SET user_name = ? WHERE user_id = ?",
            (user_name, user_id),
        )
    conn.commit()
    conn.close()


def record_submission(
    user_id: int,
    user_name: str,
    skill_name: str,
    difficulty: str,
    question_text: str,
    selected_option: str,
    selected_option_text: str,
    correct_option: str,
    correct_option_text: str,
    explanation_text: str,
    is_correct: bool,
) -> None:
    upsert_user(user_id, user_name)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO submissions (
            user_id,
            user_name,
            skill_name,
            difficulty,
            question_text,
            selected_option,
            selected_option_text,
            correct_option,
            correct_option_text,
            explanation_text,
            is_correct,
            submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            user_name,
            skill_name,
            difficulty,
            question_text,
            selected_option,
            selected_option_text,
            correct_option,
            correct_option_text,
            explanation_text,
            1 if is_correct else 0,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_leaderboard(limit: int = 20, skill_name: str | None = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if skill_name:
        cursor.execute(
            """
            SELECT
                user_id,
                user_name,
                SUM(is_correct) AS correct_count,
                COUNT(*) AS attempts,
                ROUND(100.0 * SUM(is_correct) / COUNT(*), 1) AS accuracy,
                SUM(is_correct) * 10 + COUNT(*) AS points,
                MAX(submitted_at) AS last_submission
            FROM submissions
            WHERE skill_name = ?
            GROUP BY user_id, user_name
            ORDER BY points DESC, correct_count DESC, attempts DESC
            LIMIT ?
            """,
            (skill_name, limit),
        )
    else:
        cursor.execute(
            """
            SELECT
                user_id,
                user_name,
                SUM(is_correct) AS correct_count,
                COUNT(*) AS attempts,
                ROUND(100.0 * SUM(is_correct) / COUNT(*), 1) AS accuracy,
                SUM(is_correct) * 10 + COUNT(*) AS points,
                MAX(submitted_at) AS last_submission
            FROM submissions
            GROUP BY user_id, user_name
            ORDER BY points DESC, correct_count DESC, attempts DESC
            LIMIT ?
            """,
            (limit,),
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_user_skill_summary(user_id: int, skill_name: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(*) AS attempts,
            SUM(is_correct) AS correct_count
        FROM submissions
        WHERE user_id = ? AND skill_name = ?
        """,
        (user_id, skill_name),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None or row[0] == 0:
        return {"attempts": 0, "correct_count": 0, "accuracy": 0.0}
    attempts = row[0]
    correct = row[1] or 0
    return {
        "attempts": attempts,
        "correct_count": correct,
        "accuracy": round((correct / attempts) * 100.0, 1) if attempts else 0.0,
    }


def get_user_points(user_id: int) -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(is_correct)*10 + COUNT(*) FROM submissions WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return float(row[0] or 0)


def get_user_rank(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT user_id, SUM(is_correct) AS correct_count, COUNT(*) AS attempts,
               SUM(is_correct) * 10 + COUNT(*) AS points
        FROM submissions
        GROUP BY user_id
        ORDER BY points DESC, correct_count DESC, attempts DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    rank = 0
    for index, row in enumerate(rows, start=1):
        if row[0] == user_id:
            rank = index
            break
    return rank
