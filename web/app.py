# web/app.py
from flask import Flask, send_from_directory, jsonify
import os
from db import get_db_connection

def create_app(scheduler=None): # scheduler is not used for serving static files
    app = Flask(__name__, static_folder='dist', static_url_path='')

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/api/conversations')
    def get_conversations():
        print("API endpoint: /api/conversations called")
        conn = get_db_connection()
        conversations_data = []
        try:
            query = "SELECT sender_email, content, timestamp FROM conversations ORDER BY timestamp DESC"
#            print(f"Executing query: {query}") # Print SQL query
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conversations_data = [{
                'sender': row[0],
                'subject': row[1][:50] + '...', # Truncate content for subject
                'date': row[2]
            } for row in rows]
 #           print(f"Conversations data: {conversations_data}") # Print data
        except Exception as e:
            print(f"Database error in /api/conversations: {e}") # Print exception
        finally:
            conn.close()
        return jsonify(conversations_data)

    @app.route('/api/scheduled_emails')
    def get_scheduled_emails():
        print("API endpoint: /api/scheduled_emails called")
        conn = get_db_connection()
        scheduled_emails_data = []
        try:
            query = "SELECT recipients, content, scheduled_time FROM scheduled_emails WHERE status = 'scheduled' ORDER BY scheduled_time ASC"
   #         print(f"Executing query: {query}") # Print SQL query
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            scheduled_emails_data = [{
                'recipient': row[0],
                'subject': row[1][:50] + '...', # Truncate content for subject
                'date': row[2]
            } for row in rows]
    #        print(f"Scheduled emails data: {scheduled_emails_data}") # Print data
        except Exception as e:
            print(f"Database error in /api/scheduled_emails: {e}") # Print exception
        finally:
            conn.close()
        return jsonify(scheduled_emails_data)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
