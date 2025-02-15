import sqlite3

def init_db():
    """Initialize SQLite database and tables"""
    with sqlite3.connect('conversation_history.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS conversations
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      sender_email TEXT NOT NULL,
                      role TEXT NOT NULL,
                      content TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS scheduled_emails
                     (id TEXT PRIMARY KEY,
                      sender_email TEXT NOT NULL,
                      recipients TEXT NOT NULL,
                      content TEXT,
                      scheduled_time DATETIME NOT NULL,
                      status TEXT NOT NULL DEFAULT 'scheduled' 
                      CHECK(status IN ('scheduled', 'sent', 'cancelled')))''')
        conn.commit()

def get_db_connection():
    """Get thread-safe database connection"""
    try:
        conn = sqlite3.connect('conversation_history.db', check_same_thread=False)
        # Test the connection
        conn.execute("SELECT 1")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {str(e)}")
        raise

def log_scheduled_email(job_id, sender_email, recipients, content, scheduled_time):
    """Log a scheduled email to the database"""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scheduled_emails (id, sender_email, recipients, content, scheduled_time) VALUES (?, ?, ?, ?, ?)",
            (job_id, sender_email, ', '.join(recipients), content, scheduled_time)
        )
        conn.commit()

def get_scheduled_emails():
    """Retrieve all scheduled emails"""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, sender_email, recipients, content, scheduled_time FROM scheduled_emails WHERE status = 'scheduled' ORDER BY scheduled_time ASC"
        )
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def truncate_history(sender_email, max_length):
    """Truncates conversation history to maximum character length from database"""
    with get_db_connection() as conn:
        try:
            cursor = conn.execute(
                "SELECT role, content FROM conversations WHERE sender_email = ? ORDER BY timestamp ASC",
                (sender_email,)
            )
            truncated_history = []
            for row in cursor.fetchall():
                # print(row)
                role, content = row
                turn = {'role': role, 'content': content}
                truncated_history.append(turn)
            return truncated_history[-max_length:]
        except Exception as e:
            print(f"Error truncating history: {str(e)}")
            return []