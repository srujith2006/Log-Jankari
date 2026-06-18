"""
Integration Guide: Connect app.py detection to web_server.py website
This file shows how to update app.py to save survivors to MongoDB
"""

# ============================================================================
# IMPORTANT: Add this to the top of your app.py to enable MongoDB integration
# ============================================================================

# Add these imports to your app.py
"""
from reports.connection import get_database
import json
from datetime import datetime
"""

# ============================================================================
# Add this function to app.py to save survivors to MongoDB
# ============================================================================

def save_survivor_to_mongodb(survivor_data):
    """
    Save detected survivor to MongoDB so it appears on website
    
    Args:
        survivor_data: dict with keys:
            - survivor_id: unique identifier
            - image: path to image file
            - latitude: GPS latitude
            - longitude: GPS longitude
            - direction: direction in degrees
            - posture: standing/lying/etc
            - confidence: detection confidence (0.0-1.0)
    """
    try:
        db = get_database()
        survivors_collection = db['survivors']
        
        # Prepare survivor document
        survivor_doc = {
            'survivor_id': survivor_data.get('survivor_id'),
            'image': survivor_data.get('image'),
            'latitude': survivor_data.get('latitude'),
            'longitude': survivor_data.get('longitude'),
            'direction': survivor_data.get('direction'),
            'posture': survivor_data.get('posture'),
            'confidence': survivor_data.get('confidence'),
            'identified': False,
            'identification': None,
            'created_at': datetime.utcnow(),
            'last_updated': datetime.utcnow(),
            'verified': False
        }
        
        # Insert or update (upsert)
        result = survivors_collection.update_one(
            {'survivor_id': survivor_data.get('survivor_id')},
            {'$set': survivor_doc},
            upsert=True
        )
        
        print(f"✓ Saved survivor {survivor_data.get('survivor_id')} to MongoDB")
        return True
        
    except Exception as e:
        print(f"✗ Error saving to MongoDB: {e}")
        return False


# ============================================================================
# In app.py, replace the JSON save call with MongoDB
# ============================================================================

# BEFORE (Current way in app.py):
"""
survivor_records[survivor_id] = {
    "survivor_id": survivor_id,
    "image": image_file,
    "latitude": latitude,
    "longitude": longitude,
    "direction": direction,
    "posture": posture,
    "confidence": confidence,
    "voice_detected": False
}

# Save to JSON
with open(SURVIVOR_REPORT, 'w') as f:
    json.dump(list(survivor_records.values()), f, indent=2)
"""

# AFTER (New way with MongoDB):
"""
survivor_data = {
    "survivor_id": survivor_id,
    "image": image_file,
    "latitude": latitude,
    "longitude": longitude,
    "direction": direction,
    "posture": posture,
    "confidence": confidence
}

# Save to both JSON (for backup) and MongoDB (for website)
save_survivor_to_mongodb(survivor_data)

# Still keep JSON as backup
with open(SURVIVOR_REPORT, 'w') as f:
    json.dump(list(survivor_records.values()), f, indent=2)
"""


# ============================================================================
# IMPLEMENTATION STEPS
# ============================================================================

"""
Step 1: Add imports at top of app.py
   - from reports.connection import get_database
   - from datetime import datetime

Step 2: Add the save_survivor_to_mongodb() function

Step 3: When you detect a survivor, call:
   - save_survivor_to_mongodb(survivor_data)

Step 4: Test
   - Run app.py
   - Run web_server.py
   - Check http://localhost:5000
   - Detected survivors should appear immediately!

DONE! Your website will now show survivors in real-time as they're detected!
"""


# ============================================================================
# DATA FLOW AFTER INTEGRATION
# ============================================================================

"""
Mobile Device (Video)
        ↓
    app.py
    ├─ Detect survivor
    ├─ Capture image
    ├─ Get GPS location
    ├─ save_survivor_to_mongodb() ← NEW!
    └─ Save to JSON
        ↓
    MongoDB Database ← Receives data immediately!
        ↓
    web_server.py
    ├─ Queries MongoDB
    ├─ Gets fresh survivor data
    └─ Displays on website
        ↓
    http://localhost:5000 (Browser)
    └─ Users see unidentified survivors!
        ↓
    User submits identification
        ↓
    web_server.py saves to MongoDB
        ↓
    Both app.py and admin dashboard see it
"""


# ============================================================================
# IMPORTANT NOTES
# ============================================================================

"""
1. MongoDB Atlas Connection:
   - Your .env file already has the connection string
   - get_database() automatically connects
   - No additional setup needed!

2. Real-time Updates:
   - Survivors appear on website within seconds of detection
   - No need to refresh or wait
   - Website auto-refreshes every 30 seconds

3. Backward Compatibility:
   - Still saves to survivors.json for backup
   - app.py doesn't need to change much
   - Just add the save_survivor_to_mongodb() calls

4. Identification Data:
   - When users identify survivors on website
   - It's saved to MongoDB
   - app.py can query it for statistics

5. Testing:
   - Before: app.py creates survivors.json
   - After: app.py creates MongoDB + survivors.json
   - Website reads from MongoDB (not JSON)
"""


# ============================================================================
# OPTIONAL: Get identified survivors in app.py
# ============================================================================

def get_identified_survivors():
    """
    Query MongoDB to get survivors that have been identified
    Useful for statistics and reporting
    """
    try:
        db = get_database()
        survivors = db['survivors'].find({'identified': True})
        return list(survivors)
    except Exception as e:
        print(f"✗ Error getting identified survivors: {e}")
        return []


def get_survivor_stats():
    """Get statistics about survivors"""
    try:
        db = get_database()
        survivors = db['survivors']
        
        total = survivors.count_documents({})
        unidentified = survivors.count_documents({'identified': False})
        identified = survivors.count_documents({'identified': True})
        verified = survivors.count_documents({'identified': True, 'verified': True})
        
        stats = {
            'total': total,
            'unidentified': unidentified,
            'identified': identified,
            'verified': verified
        }
        
        print(f"✓ Survivor Stats: {stats}")
        return stats
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
        return {}


# ============================================================================
# QUICK INTEGRATION EXAMPLE
# ============================================================================

"""
# In your detection loop in app.py:

for detected_survivor in detection_results:
    survivor_id = generate_survivor_id()
    image_file = save_survivor_image(detected_survivor)
    
    survivor_data = {
        'survivor_id': survivor_id,
        'image': image_file,
        'latitude': gps['latitude'],
        'longitude': gps['longitude'],
        'direction': gps['direction'],
        'posture': detected_survivor['posture'],
        'confidence': detected_survivor['confidence']
    }
    
    # Add this line:
    save_survivor_to_mongodb(survivor_data)  # ← NEW!
    
    # Keep existing JSON save:
    survivor_records[survivor_id] = {... }
    save_json_backup()
"""


# ============================================================================
# SUMMARY
# ============================================================================

"""
BEFORE Integration:
  app.py → survivors.json → Website (Manual check)

AFTER Integration:
  app.py → MongoDB → website_server.py → Website (Real-time!)
         → survivors.json (backup)

BENEFIT:
  ✓ Instant updates
  ✓ Real-time website
  ✓ Admin dashboard shows live data
  ✓ Users can identify immediately
  ✓ No manual data transfer needed
"""
