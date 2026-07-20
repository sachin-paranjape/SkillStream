import sqlite3
import os
import bcrypt

def reset_and_init_db():
    print("Starting database initialization...")
    
    # Ensure the path is correct for local development and Render production
    db_path = os.getenv("DB_PATH", "data/skillstream.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove existing database to ensure a clean slate
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Existing database removed.")
        except PermissionError:
            print(f"Error: {db_path} is currently in use. Please close all apps/terminals using it.")
            return

    # Create fresh schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''CREATE TABLE users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                      )''')
    
    # Mastery table
    cursor.execute('''CREATE TABLE mastery (
                        username TEXT,
                        skill TEXT,
                        level TEXT,
                        percentage REAL,
                        FOREIGN KEY(username) REFERENCES users(username)
                      )''')

    # Seed demo user (admin / admin123)
    hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
    cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                   ("admin", "admin@skillstream.com", hashed_password.decode('utf-8')))
    
    conn.commit()
    conn.close()
    print(f"Database successfully initialized at {db_path} with demo user 'admin'.")

if __name__ == "__main__":
    reset_and_init_db()