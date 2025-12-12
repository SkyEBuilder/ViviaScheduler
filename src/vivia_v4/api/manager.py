import json
import os
import uuid
from vivia_v4.task_pool import ViviaTaskPool
from vivia_v4.api.config import settings

class PoolManager:
    """
    Manages loading and saving ViviaTaskPool instances for users.
    Each user has a {user_id}.json file.
    """
    
    @staticmethod
    def get_pool_filename(user_id: str) -> str:
        return f"{user_id}.json"

    @staticmethod
    def load_pool(user_id: str) -> ViviaTaskPool:
        filename = PoolManager.get_pool_filename(user_id)
        if not os.path.exists(filename):
            # Create a new empty pool for the user
            # We use a hash of user_id or just a random int for the numeric id required by ViviaTaskPool
            # ViviaTaskPool.id is int, but our user_id is string (UUID)
            # Let's just generate a random int ID for the pool itself
            pool = ViviaTaskPool(id=uuid.uuid4().int & (1<<63)-1) # Positive 64-bit int
            PoolManager.save_pool(user_id, pool)
            return pool
            
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ViviaTaskPool.model_validate(data)

    @staticmethod
    def save_pool(user_id: str, pool: ViviaTaskPool) -> None:
        filename = PoolManager.get_pool_filename(user_id)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(pool.model_dump_json(indent=2))

class UserManager:
    """
    Manages user persistence.
    Stores users in a single JSON file defined in settings.
    Structure: { "api_key": { "user_id": "...", "email": "...", "is_active": bool } }
    We index by API Key for fast lookup during auth.
    """
    
    @staticmethod
    def _load_users() -> dict:
        if not os.path.exists(settings.users_file):
            return {}
        try:
            with open(settings.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _save_users(users: dict) -> None:
        with open(settings.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2)

    @staticmethod
    def create_user(email: str, is_active: bool = False) -> dict:
        users = UserManager._load_users()
        
        # Check if email exists (inefficient linear scan, but fine for now)
        for u in users.values():
            if u.get('email') == email:
                raise ValueError("Email already registered")
                
        user_id = str(uuid.uuid4())
        api_key = str(uuid.uuid4().hex)
        
        user_data = {
            "user_id": user_id,
            "email": email,
            "is_active": is_active,
            "api_key": api_key
        }
        
        # Index by API Key
        users[api_key] = user_data
        UserManager._save_users(users)
        return user_data

    @staticmethod
    def get_user_by_key(api_key: str) -> dict | None:
        users = UserManager._load_users()
        return users.get(api_key)
