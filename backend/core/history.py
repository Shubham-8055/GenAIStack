import json
import redis
import os
import uuid

# --- CONFIGURATION ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

class RedisHistoryManager:
    def __init__(self):
        try:
            self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
            self.redis.ping() # Check connection
            print(f"[History] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            print(f"[History] Failed to connect to Redis: {e}")
            self.redis = None

    def get_history(self, session_id):
        """
        Retrieves the chat history for a given session ID.
        Returns a list of message dictionaries.
        """
        if not self.redis:
            return []
        
        # Redis List: "chat:{session_id}"
        key = f"chat:{session_id}"
        try:
            # Get all elements from the list
            history_json = self.redis.lrange(key, 0, -1)
            history = [json.loads(msg) for msg in history_json]
            return history
        except Exception as e:
            print(f"[History] Error reading history: {e}")
            return []

    def add_message(self, session_id, role, content):
        """
        Adds a message to the chat history.
        """
        if not self.redis:
            return

        key = f"chat:{session_id}"
        message = {"role": role, "content": content}
        try:
            # Push to the end of the list (RPUSH)
            self.redis.rpush(key, json.dumps(message))
            
            # Optional: Set TTL for sessions (e.g., 24 hours)
            self.redis.expire(key, 86400) 
            
            # Track active sessions in a Set
            self.redis.sadd("sessions", session_id)
        except Exception as e:
            print(f"[History] Error saving message: {e}")

    def get_sessions(self):
        """
        Returns a list of all active session IDs.
        """
        if not self.redis:
            return []
            
        try:
            sessions = self.redis.smembers("sessions")
            return [{"id": s, "name": f"Session {s[:8]}"} for s in sessions]
        except Exception as e:
            print(f"[History] Error fetching sessions: {e}")
            return []

    def create_session(self):
        """
        Generates a new session ID.
        """
        new_id = str(uuid.uuid4())
        return new_id

    def delete_history(self, session_id):
        """
        Deletes the chat history for a session.
        """
        if not self.redis:
            return False
            
        key = f"chat:{session_id}"
        try:
            self.redis.delete(key)
            # Optional: Remove from sessions set if you want to completely kill the session
            # self.redis.srem("sessions", session_id) 
            return True
        except Exception as e:
            print(f"[History] Error deleting history: {e}")
            return False
