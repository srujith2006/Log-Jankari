from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from dotenv import load_dotenv
import os
import json
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# MongoDB Atlas Connection String
URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "DisasterSurvivorSystem")

def get_mongo_client():
    """Get MongoDB client with error handling."""
    if not URI:
        raise ValueError("MONGO_URI is not configured. Set it in .env or your environment.")

    try:
        client = MongoClient(URI, serverSelectionTimeoutMS=5000)
        # Verify connection
        client.admin.command('ping')
        print("Connected to MongoDB Atlas successfully.")
        return client
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"MongoDB connection failed: {e}")
        raise

def get_database():
    """Get the main database instance."""
    client = get_mongo_client()
    return client[DB_NAME]

# Initialize collections
def init_db():
    """Initialize database collections and indexes."""
    try:
        db = get_database()
        
        # Create survivors collection if not exists
        if 'survivors' not in db.list_collection_names():
            db.create_collection('survivors')
            db['survivors'].create_index('survivor_id', unique=True)
            db['survivors'].create_index('identified')
            print("Survivors collection created.")
            
            # Auto-migrate from survivors.json if exists
            migrate_from_json(db)
        
        # Create users collection if not exists
        if 'users' not in db.list_collection_names():
            db.create_collection('users')
            db['users'].create_index('username', unique=True)
            db['users'].create_index('email', unique=True)
            print("Users collection created.")
        
        print("Database initialized successfully.")
        return db
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

def migrate_from_json(db):
    """Auto-migrate survivors from JSON file to MongoDB"""
    try:
        json_path = Path(__file__).parent / 'survivors.json'
        
        if json_path.exists():
            with open(json_path, 'r') as f:
                survivors_data = json.load(f)
            
            if survivors_data and len(survivors_data) > 0:
                for survivor in survivors_data:
                    # Add default fields if missing
                    if 'identified' not in survivor:
                        survivor['identified'] = False
                    if 'identification' not in survivor:
                        survivor['identification'] = None
                    if 'verified' not in survivor:
                        survivor['verified'] = False
                
                # Insert all
                result = db['survivors'].insert_many(survivors_data, ordered=False)
                print(f"Migrated {len(result.inserted_ids)} survivors from survivors.json")
    except Exception as e:
        print(f"Could not migrate survivors.json: {e}")

# For backward compatibility. Keep this lazy so importing the web server does
# not block or fail before routes can fall back to local JSON data.
client = None
