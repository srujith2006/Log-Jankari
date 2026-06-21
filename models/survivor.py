from datetime import datetime
from bson.objectid import ObjectId

class Survivor:
    """Survivor model for managing survivor data"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db['survivors']
    
    def add_survivor(self, survivor_data):
        """Add a new survivor from detection system"""
        survivor = {
            'survivor_id': survivor_data.get('survivor_id'),
            'image': survivor_data.get('image'),
            'latitude': survivor_data.get('latitude'),
            'longitude': survivor_data.get('longitude'),
            'direction': survivor_data.get('direction'),
            'posture': survivor_data.get('posture'),
            'confidence': survivor_data.get('confidence'),
            'face_detected': survivor_data.get('face_detected', False),
            'public_visible': survivor_data.get('public_visible', False),
            'blur_score': survivor_data.get('blur_score'),
            'quality_note': survivor_data.get('quality_note'),
            'identified': False,
            'identification': None,
            'created_at': datetime.utcnow(),
            'last_updated': datetime.utcnow(),
            'verified': False
        }
        
        # Update if exists, insert if new
        result = self.collection.update_one(
            {'survivor_id': survivor_data.get('survivor_id')},
            {'$set': survivor},
            upsert=True
        )
        return result
    
    def get_unidentified_survivors(self, limit=20):
        """Get all unidentified survivors (sorted by creation date, newest first)"""
        survivors = list(self.collection.find(
            {'identified': False}
        ).sort('created_at', -1).limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for survivor in survivors:
            survivor['_id'] = str(survivor['_id'])
        
        return survivors

    def get_public_unidentified_survivors(self, limit=20):
        """Get unidentified survivors safe for public recognition pages."""
        survivors = list(self.collection.find(
            {
                'identified': False,
                'face_detected': True
            }
        ).sort('created_at', -1).limit(limit))

        for survivor in survivors:
            survivor['_id'] = str(survivor['_id'])

        return survivors
    
    def get_survivor_by_id(self, survivor_id):
        """Get a specific survivor by survivor_id"""
        survivor = self.collection.find_one({'survivor_id': survivor_id})
        if survivor:
            survivor['_id'] = str(survivor['_id'])
        return survivor
    
    def identify_survivor(self, survivor_id, identification_data, user_id):
        """Store user-provided survivor information for admin verification."""
        identification = {
            'name': identification_data.get('name'),
            'age': identification_data.get('age'),
            'phone': identification_data.get('phone'),
            'address': identification_data.get('address'),
            'relationship': identification_data.get('relationship'),
            'relationship_detail': identification_data.get('relationship_detail'),
            'other_detail': identification_data.get('other_detail'),
            'notes': identification_data.get('notes'),
            'identified_by_user_id': ObjectId(user_id),
            'identified_at': datetime.utcnow(),
            'verified': False,
            'admin_seen': False,
            'details_seen_by_user': False
        }
        
        result = self.collection.update_one(
            {'survivor_id': survivor_id},
            {
                '$set': {
                    'identified': True,
                    'verified': False,
                    'identification': identification,
                    'last_updated': datetime.utcnow()
                }
            }
        )
        return result

    def verify_identification(self, survivor_id, recovery_status, hospital):
        """Approve an identification and add rescue-status information."""
        result = self.collection.update_one(
            {'survivor_id': survivor_id},
            {
                '$set': {
                    'verified': True,
                    'identification.verified': True,
                    'identification.verified_at': datetime.utcnow(),
                    'identification.details_seen_by_user': False,
                    'recovery_status': recovery_status,
                    'likely_hospital': hospital,
                    'last_updated': datetime.utcnow()
                }
            }
        )
        return result

    def get_user_submissions(self, user_id, limit=100):
        """Get survivors this user submitted information for."""
        survivors = list(self.collection.find(
            {'identification.identified_by_user_id': ObjectId(user_id)}
        ).sort('last_updated', -1).limit(limit))

        for survivor in survivors:
            survivor['_id'] = str(survivor['_id'])

        return survivors

    def count_unseen_verified_for_user(self, user_id):
        """Count verified survivor details not yet opened by this submitter."""
        return self.collection.count_documents({
            'verified': True,
            'identification.identified_by_user_id': ObjectId(user_id),
            'identification.details_seen_by_user': {'$ne': True}
        })

    def mark_verified_seen_for_user(self, user_id):
        """Mark released survivor details as seen for this submitter."""
        self.collection.update_many(
            {
                'verified': True,
                'identification.identified_by_user_id': ObjectId(user_id),
                'identification.details_seen_by_user': {'$ne': True}
            },
            {'$set': {'identification.details_seen_by_user': True}}
        )

    def count_unseen_admin_submissions(self):
        """Count user submissions the admin has not opened yet."""
        return self.collection.count_documents({
            'identified': True,
            'identification.admin_seen': {'$ne': True}
        })

    def mark_admin_submissions_seen(self):
        """Mark submitted identification forms as seen by admin."""
        self.collection.update_many(
            {
                'identified': True,
                'identification.admin_seen': {'$ne': True}
            },
            {'$set': {'identification.admin_seen': True}}
        )
    
    def get_identified_survivors(self, limit=100):
        """Get all identified survivors"""
        survivors = list(self.collection.find(
            {'identified': True}
        ).sort('last_updated', -1).limit(limit))
        
        for survivor in survivors:
            survivor['_id'] = str(survivor['_id'])
        
        return survivors
    
    def get_stats(self):
        """Get database statistics"""
        total = self.collection.count_documents({})
        unidentified = self.collection.count_documents({'identified': False})
        identified = self.collection.count_documents({'identified': True})
        verified = self.collection.count_documents({'identification.verified': True})
        
        return {
            'total': total,
            'unidentified': unidentified,
            'identified': identified,
            'verified': verified
        }
    
    def bulk_import_from_json(self, survivors_list):
        """Bulk import survivors from JSON (for initial data migration)"""
        for survivor_data in survivors_list:
            self.add_survivor(survivor_data)
        return len(survivors_list)
