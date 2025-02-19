import sqlite3
import config

def init_db():
    """Initialize SQLite database and tables"""
    db_file = config.TEST_HISTORY_FILE if config.TESTING else config.CONVERSATION_HISTORY_FILE
    with sqlite3.connect(db_file) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS conversations
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      sender_email TEXT NOT NULL,
                      role TEXT NOT NULL,
                      content TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()

def get_db_connection():
    """Get thread-safe database connection"""
    db_file = config.TEST_HISTORY_FILE if config.TESTING else config.CONVERSATION_HISTORY_FILE
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        # Test the connection
        conn.execute("SELECT 1")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {str(e)}")
        raise


def get_history_by_email(sender_email):
    """Gets conversation history for a given email"""
    with get_db_connection() as conn:
        try:
            cursor = conn.execute(
                "SELECT role, content FROM conversations WHERE sender_email = ? ORDER BY timestamp ASC",
                (sender_email,)
            )
            history = []
            for row in cursor.fetchall():
                # print(row)
                role, content = row
                turn = {'role': role, 'content': content}
                history.append(turn)
            return history
        except Exception as e:
            print(f"Error truncating history: {str(e)}")
            return []

def log_conversation(conn, sender_email, from_, subject, body, recipients, delay_seconds, content):
    """Logs the conversation to the database."""
    conn.execute(
        "INSERT INTO conversations (sender_email, role, content) VALUES (?, ?, ?)",
        (sender_email, 'user', f"From: {from_}\nSubject: {subject}\n{body}")
    )
    conn.execute(
        "INSERT INTO conversations (sender_email, role, content) VALUES (?, ?, ?)",
        (sender_email, 'assistant', f"To: {', '.join(recipients)}\nDelay: {delay_seconds}\n{content}")
    )
    conn.commit()