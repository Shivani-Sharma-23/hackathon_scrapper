# hackathon_appwrite_client.py
import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.exception import AppwriteException
from dotenv import load_dotenv
import json

load_dotenv()

class HackathonAppwriteClient:
    def __init__(self):
        self.client = Client()
        self.client.set_endpoint(os.getenv('APPWRITE_ENDPOINT'))
        self.client.set_project(os.getenv('APPWRITE_PROJECT_ID'))
        self.client.set_key(os.getenv('APPWRITE_API_KEY'))
        
        self.databases = Databases(self.client)
        self.database_id = os.getenv('APPWRITE_DATABASE_ID', 'gigrithm')
        self.hackathons_collection_id = os.getenv('HACKATHONS_COLLECTION_ID', 'hackathons')
        self.users_collection_id = os.getenv('USERS_COLLECTION_ID', 'users')

    def get_user(self, user_id):
        """Get a specific user by user ID"""
        try:
            result = self.databases.get_document(
                database_id=self.database_id,
                collection_id=self.users_collection_id,
                document_id=user_id
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error fetching user {user_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching user {user_id}: {e}")
            return None

    def get_hackathon(self, hackathon_id):
        """Get a specific hackathon by hackathon ID"""
        try:
            result = self.databases.get_document(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                document_id=hackathon_id
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error fetching hackathon {hackathon_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching hackathon {hackathon_id}: {e}")
            return None

    def get_hackathons(self, limit=100):
        """Get all hackathons with optional limit"""
        try:
            result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=[Query.limit(limit)]
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error fetching hackathons: {e}")
            return None
        except Exception as e:
            print(f"Error fetching hackathons: {e}")
            return None

    def get_hackathons_by_filters(self, location=None, mode=None, limit=500):
        """Get hackathons filtered by location and/or mode"""
        queries = [Query.limit(limit)]  # Add default limit
        
        if location and location != 'all':
            queries.append(Query.equal('location', location))
        
        if mode and mode != 'all':
            queries.append(Query.equal('mode', mode))
        
        try:
            result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=queries
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error fetching filtered hackathons: {e}")
            return None
        except Exception as e:
            print(f"Error fetching filtered hackathons: {e}")
            return None

    def search_hackathons(self, search_query, limit=50):
        """Search hackathons by title or organization"""
        try:
            queries = [
                Query.limit(limit),
                Query.search('title', search_query)
            ]
            
            result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=queries
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error searching hackathons: {e}")
            # Fallback: get all and filter manually
            return self.get_hackathons_with_text_filter(search_query, limit)
        except Exception as e:
            print(f"Error searching hackathons: {e}")
            return None

    def get_hackathons_with_text_filter(self, search_text, limit=50):
        """Fallback method to filter hackathons by text manually"""
        try:
            # Get more hackathons to filter from
            all_hackathons = self.get_hackathons(limit * 3)
            if not all_hackathons or not all_hackathons.get('documents'):
                return None
            
            filtered_docs = []
            search_text_lower = search_text.lower()
            
            for hackathon in all_hackathons['documents']:
                title = hackathon.get('title', '').lower()
                organization = hackathon.get('organization', '').lower()
                
                if search_text_lower in title or search_text_lower in organization:
                    filtered_docs.append(hackathon)
                    
                if len(filtered_docs) >= limit:
                    break
            
            return {
                'documents': filtered_docs,
                'total': len(filtered_docs)
            }
        except Exception as e:
            print(f"Error in text filter fallback: {e}")
            return None

    def create_user(self, user_data):
        """Create a new user document"""
        try:
            result = self.databases.create_document(
                database_id=self.database_id,
                collection_id=self.users_collection_id,
                document_id='unique()',
                data=user_data
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error creating user: {e}")
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    def update_user(self, user_id, user_data):
        """Update an existing user document"""
        try:
            result = self.databases.update_document(
                database_id=self.database_id,
                collection_id=self.users_collection_id,
                document_id=user_id,
                data=user_data
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error updating user {user_id}: {e}")
            return None
        except Exception as e:
            print(f"Error updating user {user_id}: {e}")
            return None

    def create_hackathon(self, hackathon_data):
        """Create a new hackathon document"""
        try:
            result = self.databases.create_document(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                document_id='unique()',
                data=hackathon_data
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error creating hackathon: {e}")
            return None
        except Exception as e:
            print(f"Error creating hackathon: {e}")
            return None

    def update_hackathon(self, hackathon_id, hackathon_data):
        """Update an existing hackathon document"""
        try:
            result = self.databases.update_document(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                document_id=hackathon_id,
                data=hackathon_data
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error updating hackathon {hackathon_id}: {e}")
            return None
        except Exception as e:
            print(f"Error updating hackathon {hackathon_id}: {e}")
            return None

    def delete_hackathon(self, hackathon_id):
        """Delete a hackathon document"""
        try:
            result = self.databases.delete_document(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                document_id=hackathon_id
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error deleting hackathon {hackathon_id}: {e}")
            return None
        except Exception as e:
            print(f"Error deleting hackathon {hackathon_id}: {e}")
            return None

    def get_recent_hackathons(self, limit=20):
        """Get recently added hackathons sorted by creation date"""
        try:
            queries = [
                Query.limit(limit),
                Query.order_desc('$createdAt')
            ]
            
            result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=queries
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error fetching recent hackathons: {e}")
            return None
        except Exception as e:
            print(f"Error fetching recent hackathons: {e}")
            return None

    def get_hackathons_by_organization(self, organization, limit=50):
        """Get hackathons by specific organization"""
        try:
            queries = [
                Query.limit(limit),
                Query.equal('organization', organization)
            ]
            
            result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=queries
            )
            return result
        except AppwriteException as e:
            print(f"Appwrite error fetching hackathons by organization: {e}")
            return None
        except Exception as e:
            print(f"Error fetching hackathons by organization: {e}")
            return None

    def test_connection(self):
        """Test the Appwrite connection"""
        try:
            # Try to list documents with a small limit to test connection
            result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=[Query.limit(1)]
            )
            
            if result:
                return True, f"Connection successful. Found {result.get('total', 0)} hackathons in database."
            else:
                return False, "Connection failed: No result returned"
                
        except AppwriteException as e:
            return False, f"Appwrite connection error: {e}"
        except Exception as e:
            return False, f"Connection test failed: {e}"

    def get_database_stats(self):
        """Get statistics about the database"""
        try:
            hackathons_result = self.databases.list_documents(
                database_id=self.database_id,
                collection_id=self.hackathons_collection_id,
                queries=[Query.limit(1)]
            )
            
            users_result = None
            try:
                users_result = self.databases.list_documents(
                    database_id=self.database_id,
                    collection_id=self.users_collection_id,
                    queries=[Query.limit(1)]
                )
            except:
                pass  # Users collection might not exist
            
            stats = {
                'hackathons_count': hackathons_result.get('total', 0) if hackathons_result else 0,
                'users_count': users_result.get('total', 0) if users_result else 0,
                'database_id': self.database_id,
                'hackathons_collection_id': self.hackathons_collection_id,
                'users_collection_id': self.users_collection_id
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return None