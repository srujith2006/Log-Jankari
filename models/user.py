from datetime import datetime
import bcrypt
from bson.objectid import ObjectId

class User:
    """User model for authentication"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db['users']
    
    def create_user(self, username, email, password):
        """Create a new user with hashed password"""
        # Check if user already exists
        if self.collection.find_one({'username': username}):
            raise ValueError("Username already exists")
        
        if self.collection.find_one({'email': email}):
            raise ValueError("Email already exists")
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'created_at': datetime.utcnow(),
            'contributions': 0,
            'is_admin': False
        }
        
        result = self.collection.insert_one(user_data)
        return str(result.inserted_id)
    
    def get_user_by_username(self, username):
        """Get user by username"""
        return self.collection.find_one({'username': username})

    def get_user_by_email(self, email):
        """Get user by email"""
        return self.collection.find_one({'email': email})
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            return self.collection.find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    def verify_password(self, password, password_hash):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash)
    
    def authenticate(self, email, password):
        """Authenticate user and return user data if successful"""
        user = self.get_user_by_email(email)
        if user and self.verify_password(password, user['password_hash']):
            return user
        return None
    
    def increment_contributions(self, user_id):
        """Increment user's contributions count"""
        self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$inc': {'contributions': 1}}
        )
