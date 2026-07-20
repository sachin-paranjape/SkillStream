import bcrypt
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from database import get_connection, upsert_user

class AuthHandler:
    """Manages user registration and authentication backed by SQLite & bcrypt hashing."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes plaintext password using bcrypt with salt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifies candidate plaintext password against stored bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False

    @classmethod
    def register_user(cls, username: str, email: str, password: str) -> Tuple[bool, str]:
        """Registers a new user into SQLite users table using parameterized queries."""
        username = username.strip()
        email = email.strip().lower()
        
        if not username or not email or not password:
            return False, "All fields are required."
            
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."

        hashed = cls.hash_password(password)
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.utcnow().isoformat()

        try:
            cursor.execute("PRAGMA table_info(users)")
            user_cols = [row[1] for row in cursor.fetchall()]

            # Check for existing username or email
            if "username" in user_cols:
                cursor.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email))
            else:
                cursor.execute("SELECT user_name, email FROM users WHERE user_name = ? OR email = ?", (username, email))

            existing = cursor.fetchone()
            if existing:
                u_val = existing['username'] if "username" in user_cols and existing['username'] else existing.get('user_name', '')
                if u_val and u_val.lower() == username.lower():
                    return False, "Username is already taken."
                if existing['email'] and existing['email'].lower() == email.lower():
                    return False, "Email address is already registered."

            # Insert new user with parameterized query
            if "user_name" in user_cols:
                cursor.execute(
                    "INSERT INTO users (username, user_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, username, email, hashed, now_str)
                )
            else:
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (username, email, hashed, now_str)
                )
            conn.commit()
            
            # Fetch created user to sync user_id
            cursor.execute("SELECT user_id, username FROM users WHERE username = ? OR user_name = ?", (username, username))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row['user_id']
                upsert_user(user_id, username)
                
            return True, "Account created successfully! Please sign in."
        except sqlite3.IntegrityError as e:
            return False, f"Registration failed: {e}"
        except Exception as e:
            return False, f"An unexpected error occurred: {e}"
        finally:
            conn.close()

    @classmethod
    def authenticate_user(cls, username_or_email: str, password: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Authenticates a user against SQLite database using parameterized queries."""
        identifier = username_or_email.strip()
        if not identifier or not password:
            return None, "Please enter your username/email and password."

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA table_info(users)")
            user_cols = [row[1] for row in cursor.fetchall()]

            if "username" in user_cols:
                cursor.execute(
                    "SELECT user_id, username, email, password_hash FROM users WHERE username = ? OR email = ?",
                    (identifier, identifier.lower())
                )
            else:
                cursor.execute(
                    "SELECT user_id, user_name AS username, email, password_hash FROM users WHERE user_name = ? OR email = ?",
                    (identifier, identifier.lower())
                )

            user_row = cursor.fetchone()
            if not user_row:
                return None, "Invalid username/email or password."

            stored_hash = user_row['password_hash']
            if stored_hash and cls.verify_password(password, stored_hash):
                user_dict = {
                    "user_id": user_row['user_id'],
                    "username": user_row['username'],
                    "email": user_row['email'],
                }
                upsert_user(user_row['user_id'], user_row['username'])
                return user_dict, "Login successful!"
            else:
                return None, "Invalid username/email or password."
        except Exception as e:
            return None, f"Authentication error: {e}"
        finally:
            conn.close()
