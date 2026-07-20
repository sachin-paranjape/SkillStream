import os
import sqlite3
import bcrypt
from datetime import datetime
from typing import List, Dict, Any

from config import DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with row_factory."""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes SQLite schema for users, submissions, and mastery with demo user seeding."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table for Auth
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Safely migrate existing users table if columns are missing from older schema
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    if "username" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "email" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "password_hash" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "user_name" in user_cols:
        cursor.execute("UPDATE users SET username = user_name WHERE username IS NULL OR username = ''")

    # Submissions table for tracking practice questions
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
    
    # Ensure columns in submissions
    cursor.execute("PRAGMA table_info(submissions)")
    sub_cols = [row[1] for row in cursor.fetchall()]
    if "difficulty" not in sub_cols:
        cursor.execute("ALTER TABLE submissions ADD COLUMN difficulty TEXT")
    if "explanation_text" not in sub_cols:
        cursor.execute("ALTER TABLE submissions ADD COLUMN explanation_text TEXT")
        
    # Seed demo user (admin / admin123) if not present
    cursor.execute("SELECT user_id FROM users WHERE username = ? OR email = ?", ("admin", "admin@skillstream.com"))
    if cursor.fetchone() is None:
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now_str = datetime.utcnow().isoformat()
        if "user_name" in user_cols:
            cursor.execute(
                "INSERT INTO users (username, user_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                ("admin", "admin", "admin@skillstream.com", hashed_password, now_str)
            )
        else:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("admin", "admin@skillstream.com", hashed_password, now_str)
            )

    conn.commit()
    conn.close()


def upsert_user(user_id: int, user_name: str) -> None:
    """Ensures user record exists in database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    now_str = datetime.utcnow().isoformat()
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ? OR username = ?", (user_id, user_name))
    if cursor.fetchone() is None:
        if "user_name" in user_cols:
            cursor.execute(
                "INSERT INTO users (user_id, username, user_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, user_name, user_name, f"{user_name}@skillstream.com", "EXTERNAL_AUTH", now_str),
            )
        else:
            cursor.execute(
                "INSERT INTO users (user_id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, user_name, f"{user_name}@skillstream.com", "EXTERNAL_AUTH", now_str),
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


def get_seen_question_texts(
    user_id: int,
    skill_name: str,
    difficulty: str | None = None,
) -> set[str]:
    conn = get_connection()
    cursor = conn.cursor()
    if difficulty:
        cursor.execute(
            """
            SELECT DISTINCT question_text
            FROM submissions
            WHERE user_id = ?
              AND skill_name = ?
              AND difficulty = ?
              AND question_text IS NOT NULL
            """,
            (user_id, skill_name, difficulty),
        )
    else:
        cursor.execute(
            """
            SELECT DISTINCT question_text
            FROM submissions
            WHERE user_id = ?
              AND skill_name = ?
              AND question_text IS NOT NULL
            """,
            (user_id, skill_name),
        )
    rows = cursor.fetchall()
    conn.close()
    return {str(row[0]).strip() for row in rows if str(row[0]).strip()}


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
