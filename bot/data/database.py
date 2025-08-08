import sqlite3
import os

DB_FILE = "tournament.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table for users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id BIGINT UNIQUE NOT NULL,
        username TEXT
    )
    """)

    # Table for admins
    # Table for tournament status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tournament_status (
        id INTEGER PRIMARY KEY,
        registration_open BOOLEAN DEFAULT 0,
        mode TEXT DEFAULT 'nickname'
    )
    """)
    # Ensure there's always one row in tournament_status
    cursor.execute("INSERT OR IGNORE INTO tournament_status (id) VALUES (1)")


    # Table for registrations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        nickname TEXT UNIQUE NOT NULL,
        character_name TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Table for matches
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round INTEGER NOT NULL,
        player1_id INTEGER,
        player2_id INTEGER,
        winner_id INTEGER,
        is_bye BOOLEAN DEFAULT 0,
        FOREIGN KEY (player1_id) REFERENCES registrations(id),
        FOREIGN KEY (player2_id) REFERENCES registrations(id),
        FOREIGN KEY (winner_id) REFERENCES registrations(id)
    )
    """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    initialize_database()
    print("Database initialized.")
